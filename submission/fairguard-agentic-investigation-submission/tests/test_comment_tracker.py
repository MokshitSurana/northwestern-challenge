"""Tests for the comment-tracker skill (scripts/07_comment_tracker.py).

Tests focus on the deterministic logic — schema validation, status derivation
from event timelines, deadline-pressure rules, and metric computation. The
CLI subcommands are exercised by writing to a tmp_path log file and asserting
on the resulting JSON state."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "comment-tracker" / "scripts" / "07_comment_tracker.py"


def _load():
    spec = importlib.util.spec_from_file_location("comment_tracker", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["comment_tracker"] = mod
    spec.loader.exec_module(mod)
    return mod


CT = _load()


# ── Schema validation ─────────────────────────────────────────────────────────


class TestSchemaValidation:
    def test_well_formed_entry_has_no_errors(self):
        entry = {
            "firm": "X", "case": "Y → Z",
            "draft_path": "p.md", "status": "not_sent",
            "events": [],
        }
        assert CT.validate_entry("x", entry) == []

    def test_missing_required_field_flagged(self):
        entry = {"firm": "X", "case": "Y", "draft_path": "p.md"}
        errs = CT.validate_entry("x", entry)
        assert any("status" in e for e in errs)
        assert any("events" in e for e in errs)

    def test_unknown_status_flagged(self):
        entry = {
            "firm": "X", "case": "Y", "draft_path": "p.md",
            "status": "bogus_status", "events": [],
        }
        errs = CT.validate_entry("x", entry)
        assert any("unknown status" in e for e in errs)

    def test_unknown_event_kind_flagged(self):
        entry = {
            "firm": "X", "case": "Y", "draft_path": "p.md",
            "status": "sent",
            "events": [{"at": "2026-01-01", "kind": "bogus_kind"}],
        }
        errs = CT.validate_entry("x", entry)
        assert any("unknown kind" in e for e in errs)

    def test_event_missing_at_flagged(self):
        entry = {
            "firm": "X", "case": "Y", "draft_path": "p.md",
            "status": "sent",
            "events": [{"kind": "sent"}],
        }
        errs = CT.validate_entry("x", entry)
        assert any("missing 'at'" in e for e in errs)


# ── Status derivation (event timeline → live status) ──────────────────────────


class TestDeriveStatus:
    def _entry(self, events: list[dict], deadline: str | None = None) -> dict:
        return {
            "firm": "X", "case": "Y",
            "status": "not_sent", "draft_path": "p.md",
            "events": events,
            "deadline": deadline,
        }

    def test_no_events_returns_entry_status(self):
        assert CT.derive_status(self._entry([])) == "not_sent"
        e = self._entry([])
        e["status"] = "not_drafted"
        assert CT.derive_status(e) == "not_drafted"

    def test_sent_event_sets_sent(self):
        e = self._entry([{"at": "2026-01-01T00:00:00+00:00", "kind": "sent"}])
        assert CT.derive_status(e) == "sent"

    def test_acknowledged_overrides_sent(self):
        e = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-02T00:00:00+00:00", "kind": "acknowledged"},
        ])
        assert CT.derive_status(e) == "acknowledged"

    def test_substantive_reply_is_decisive(self):
        """Once a substantive reply comes in, nothing else (except `closed`
        or `legal_threat`) can downgrade the status."""
        e = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-02T00:00:00+00:00", "kind": "substantive_reply"},
            {"at": "2026-01-03T00:00:00+00:00", "kind": "followup_sent"},
        ])
        assert CT.derive_status(e) == "responded"

    def test_followup_without_substantive_marks_awaiting(self):
        e = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-08T00:00:00+00:00", "kind": "followup_sent"},
        ])
        assert CT.derive_status(e) == "awaiting_substantive"

    def test_legal_threat_overrides_everything(self):
        e = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-02T00:00:00+00:00", "kind": "substantive_reply"},
            {"at": "2026-01-03T00:00:00+00:00", "kind": "legal_threat"},
        ])
        assert CT.derive_status(e) == "escalated_to_counsel"

    def test_closed_terminates_with_outcome(self):
        e_resp = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-10T00:00:00+00:00", "kind": "closed", "response_kind": "response"},
        ])
        e_noresp = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-10T00:00:00+00:00", "kind": "closed", "response_kind": "no_response"},
        ])
        assert CT.derive_status(e_resp) == "closed_response"
        assert CT.derive_status(e_noresp) == "closed_no_response"

    def test_deadline_pressure_marks_overdue(self):
        """When the deadline has passed and there's no substantive reply, the
        status flips to no_response_by_deadline — separate from the editorial
        decision to formally close."""
        past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        e = self._entry(
            [{"at": "2026-01-01T00:00:00+00:00", "kind": "sent"}],
            deadline=past,
        )
        assert CT.derive_status(e) == "no_response_by_deadline"

    def test_deadline_in_future_does_not_flip(self):
        future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        e = self._entry(
            [{"at": "2026-01-01T00:00:00+00:00", "kind": "sent"}],
            deadline=future,
        )
        assert CT.derive_status(e) == "sent"

    def test_deadline_does_not_override_substantive(self):
        past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        e = self._entry([
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-02T00:00:00+00:00", "kind": "substantive_reply"},
        ], deadline=past)
        assert CT.derive_status(e) == "responded"


# ── Metric computation ──────────────────────────────────────────────────────


class TestDeriveMetrics:
    def test_no_send_no_days_since(self):
        m = CT.derive_metrics({"events": []})
        assert m["days_since_send"] is None

    def test_days_since_send(self):
        sent = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        m = CT.derive_metrics({"events": [{"at": sent, "kind": "sent"}]})
        assert m["days_since_send"] in (4, 5, 6)  # allow boundary jitter

    def test_days_until_deadline_negative_when_overdue(self):
        past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        m = CT.derive_metrics({"events": [], "deadline": past})
        assert m["days_until_deadline"] is not None
        assert m["days_until_deadline"] < 0

    def test_has_substantive_flag(self):
        m = CT.derive_metrics({"events": [
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
        ]})
        assert m["has_substantive"] is False
        m = CT.derive_metrics({"events": [
            {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
            {"at": "2026-01-02T00:00:00+00:00", "kind": "substantive_reply"},
        ]})
        assert m["has_substantive"] is True


# ── CLI end-to-end (writes to a tmp log, reloads, asserts) ────────────────────


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    """Point the script at a fresh temporary log file in tmp_path."""
    log_path = tmp_path / "comment_log.json"
    web_path = tmp_path / "web_log.json"
    seed = {
        "schema_version": 1,
        "entries": {
            "venn_strategies": {
                "firm": "Venn Strategies", "case": "Steinberg → DOE",
                "scan_rank": 1, "trail_case_id": "steinberg_doe",
                "draft_path": "notes/comment_requests/venn_strategies.md",
                "status": "not_sent", "addresses_used": [],
                "deadline": None, "events": [],
            },
        },
    }
    log_path.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setattr(CT, "LOG_PATH", log_path)
    monkeypatch.setattr(CT, "WEB_OUT", web_path)
    return log_path, web_path


def _ns(**kwargs):
    import argparse
    n = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(n, k, v)
    # Defaults the log command checks for:
    for default in ("at", "by", "addresses", "summary", "pointer", "deadline", "closed_kind"):
        if not hasattr(n, default):
            setattr(n, default, None)
    return n


class TestCLI:
    def test_log_sent_sets_deadline_default(self, tmp_log, capsys):
        _, web_path = tmp_log
        args = _ns(firm="venn_strategies", kind="sent",
                   addresses="a@x.com,b@x.com",
                   summary="Sent per draft", deadline=None)
        rc = CT.cmd_log(args)
        assert rc == 0
        data = json.loads(CT.LOG_PATH.read_text(encoding="utf-8"))
        entry = data["entries"]["venn_strategies"]
        assert entry["status"] == "sent"
        assert entry["deadline"] is not None
        # Default deadline = sent + 7 days
        assert len(entry["events"]) == 1
        assert entry["events"][0]["addresses"] == ["a@x.com", "b@x.com"]
        # Web mirror was written:
        assert web_path.exists()
        web = json.loads(web_path.read_text(encoding="utf-8"))
        assert web["n_entries"] == 1
        assert web["entries"][0]["status"] == "sent"

    def test_log_explicit_deadline_preserved(self, tmp_log):
        args = _ns(firm="venn_strategies", kind="sent",
                   addresses="a@x.com", deadline="2027-01-01")
        CT.cmd_log(args)
        data = json.loads(CT.LOG_PATH.read_text(encoding="utf-8"))
        assert data["entries"]["venn_strategies"]["deadline"] == "2027-01-01"

    def test_log_closed_requires_kind(self, tmp_log):
        args = _ns(firm="venn_strategies", kind="closed", closed_kind=None)
        with pytest.raises(SystemExit):
            CT.cmd_log(args)

    def test_log_closed_with_response(self, tmp_log):
        args = _ns(firm="venn_strategies", kind="sent", addresses="a@x.com")
        CT.cmd_log(args)
        args2 = _ns(firm="venn_strategies", kind="closed",
                    closed_kind="response", summary="Brief on-record statement")
        CT.cmd_log(args2)
        data = json.loads(CT.LOG_PATH.read_text(encoding="utf-8"))
        assert data["entries"]["venn_strategies"]["status"] == "closed_response"

    def test_unknown_firm_exits(self, tmp_log):
        args = _ns(firm="does_not_exist", kind="sent")
        with pytest.raises(SystemExit):
            CT.cmd_log(args)

    def test_export_sorts_by_urgency(self, tmp_log):
        """Escalations and overdue items should sort to the top of the web feed
        so a reporter sees the highest-priority outreach first."""
        # Two firms, one escalated, one closed.
        data = json.loads(CT.LOG_PATH.read_text(encoding="utf-8"))
        data["entries"]["acme_corp"] = {
            "firm": "Acme Corp", "case": "Test", "draft_path": "p.md",
            "status": "escalated_to_counsel", "addresses_used": [],
            "deadline": None,
            "events": [
                {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
                {"at": "2026-01-02T00:00:00+00:00", "kind": "legal_threat",
                 "summary": "Cease and desist threat"},
            ],
        }
        data["entries"]["zebra_inc"] = {
            "firm": "Zebra Inc", "case": "Test", "draft_path": "p.md",
            "status": "closed_response", "addresses_used": [],
            "deadline": None,
            "events": [
                {"at": "2026-01-01T00:00:00+00:00", "kind": "sent"},
                {"at": "2026-01-05T00:00:00+00:00", "kind": "closed",
                 "response_kind": "response"},
            ],
        }
        CT.LOG_PATH.write_text(json.dumps(data), encoding="utf-8")
        rc = CT.cmd_export(_ns())
        assert rc == 0
        web = json.loads(CT.WEB_OUT.read_text(encoding="utf-8"))
        # Acme (escalated) should come before Zebra (closed_response).
        firms_in_order = [e["firm"] for e in web["entries"]]
        assert firms_in_order.index("Acme Corp") < firms_in_order.index("Zebra Inc")
