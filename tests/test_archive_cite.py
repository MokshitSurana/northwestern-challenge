"""Tests for the archive-on-cite skill (scripts/08_archive_cite.py).

Network-touching paths are NOT tested here — those need real HTTP and would
make CI flaky. The tests cover the deterministic plumbing: URL collection
from the on-disk payloads, registry persistence, and the `is_recent` filter
that drives incremental re-runs."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "08_archive_cite.py"


def _load():
    spec = importlib.util.spec_from_file_location("archive_cite", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["archive_cite"] = mod
    spec.loader.exec_module(mod)
    return mod


AC = _load()


# ── URL collection from findings.json ─────────────────────────────────────────


class TestCollectFromFindings:
    def test_picks_up_senate_lda_url(self, tmp_path):
        path = tmp_path / "findings.json"
        path.write_text(json.dumps({
            "findings": [
                {"senate_lda_url": "https://lda.senate.gov/filings/public/filing/abc/print/"},
            ]
        }), encoding="utf-8")
        urls = AC.collect_urls_from_findings(path)
        assert "https://lda.senate.gov/filings/public/filing/abc/print/" in urls

    def test_picks_up_embedded_pressrel_match_urls(self, tmp_path):
        path = tmp_path / "findings.json"
        path.write_text(json.dumps({
            "findings": [
                {
                    "senate_lda_url": "https://lda.senate.gov/x",
                    "press_releases": {
                        "by_client": [
                            {"client": "X", "matches": [
                                {"url": "https://senator.house.gov/news/a"},
                                {"url": "https://senator.house.gov/news/b"},
                            ]},
                            {"client": "Y", "matches": [
                                {"url": "https://other.senate.gov/news/c"},
                            ]},
                        ],
                    },
                }
            ]
        }), encoding="utf-8")
        urls = AC.collect_urls_from_findings(path)
        assert "https://senator.house.gov/news/a" in urls
        assert "https://senator.house.gov/news/b" in urls
        assert "https://other.senate.gov/news/c" in urls

    def test_missing_file_returns_empty(self, tmp_path):
        assert AC.collect_urls_from_findings(tmp_path / "missing.json") == set()

    def test_findings_with_no_url_field_excluded(self, tmp_path):
        path = tmp_path / "findings.json"
        path.write_text(json.dumps({
            "findings": [
                {"senate_lda_url": None},
                {"senate_lda_url": ""},
            ]
        }), encoding="utf-8")
        urls = AC.collect_urls_from_findings(path)
        assert urls == set()


# ── URL collection from press_releases.json ───────────────────────────────────


class TestCollectFromPressrel:
    def test_picks_up_match_urls(self, tmp_path):
        path = tmp_path / "press_releases.json"
        path.write_text(json.dumps({
            "reports": [
                {
                    "matches": [
                        {"url": "https://a.example/1"},
                        {"url": "https://a.example/2"},
                    ]
                },
                {
                    "matches": [
                        {"url": "https://b.example/1"},
                    ]
                },
            ]
        }), encoding="utf-8")
        urls = AC.collect_urls_from_pressrel(path)
        assert urls == {
            "https://a.example/1",
            "https://a.example/2",
            "https://b.example/1",
        }


# ── is_recent: incremental re-run filter ──────────────────────────────────────


class TestIsRecent:
    def test_empty_entry_not_recent(self):
        assert AC.is_recent({}, days=30) is False
        assert AC.is_recent(None, days=30) is False

    def test_recent_with_both_services_succeeded(self):
        entry = {
            "snapshotted_at": datetime.now(UTC).isoformat(),
            "wayback_url": "https://web.archive.org/web/2026/x",
            "archive_today_url": "https://archive.ph/abc123",
        }
        assert AC.is_recent(entry, days=30) is True

    def test_recent_with_only_one_service_not_recent(self):
        """Partial successes must re-attempt to fill the missing service."""
        entry = {
            "snapshotted_at": datetime.now(UTC).isoformat(),
            "wayback_url": "https://web.archive.org/web/2026/x",
            "archive_today_url": None,
        }
        assert AC.is_recent(entry, days=30) is False

    def test_old_entry_not_recent(self):
        old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        entry = {
            "snapshotted_at": old,
            "wayback_url": "https://web.archive.org/web/2026/x",
            "archive_today_url": "https://archive.ph/abc123",
        }
        assert AC.is_recent(entry, days=30) is False

    def test_within_window_recent(self):
        recent = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        entry = {
            "snapshotted_at": recent,
            "wayback_url": "x",
            "archive_today_url": "y",
        }
        assert AC.is_recent(entry, days=30) is True

    def test_malformed_timestamp_not_recent(self):
        entry = {
            "snapshotted_at": "not-a-timestamp",
            "wayback_url": "x",
            "archive_today_url": "y",
        }
        assert AC.is_recent(entry, days=30) is False


# ── Registry persistence ─────────────────────────────────────────────────────


class TestRegistry:
    def test_load_empty_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(AC, "REGISTRY", tmp_path / "missing.json")
        reg = AC.load_registry()
        assert reg["n_urls"] == 0
        assert reg["entries"] == {}

    def test_save_and_reload_round_trips(self, tmp_path, monkeypatch):
        registry_path = tmp_path / "registry.json"
        web_path = tmp_path / "web_registry.json"
        monkeypatch.setattr(AC, "REGISTRY", registry_path)
        monkeypatch.setattr(AC, "WEB_PUBLIC", tmp_path)
        monkeypatch.setattr(AC, "WEB_REGISTRY", web_path)
        reg = {
            "entries": {
                "https://example.com/a": {
                    "url": "https://example.com/a",
                    "snapshotted_at": "2026-06-07T00:00:00+00:00",
                    "wayback_url": "https://web.archive.org/x",
                    "archive_today_url": "https://archive.ph/y",
                }
            }
        }
        AC.save_registry(reg)
        assert registry_path.exists()
        assert web_path.exists()
        reloaded = AC.load_registry()
        assert reloaded["n_urls"] == 1
        assert "https://example.com/a" in reloaded["entries"]


# ── Default URL collection composes all sources ───────────────────────────────


class TestDefaultURLCollection:
    def test_filters_out_non_http(self, tmp_path, monkeypatch):
        # Build a fake web/public with mixed URL types.
        findings_path = tmp_path / "findings.json"
        findings_path.write_text(json.dumps({
            "findings": [{
                "senate_lda_url": "https://lda.senate.gov/x",
                "press_releases": {"by_client": [
                    {"client": "X", "matches": [
                        {"url": "https://valid.example/1"},
                        {"url": "mailto:reporter@example.com"},
                        {"url": "javascript:void(0)"},
                        {"url": ""},
                    ]}
                ]},
            }]
        }), encoding="utf-8")
        # Simulate empty trails + pressrel.
        (tmp_path / "trails.json").write_text(json.dumps({"trails": []}), encoding="utf-8")
        (tmp_path / "press_releases.json").write_text(json.dumps({"reports": []}), encoding="utf-8")
        monkeypatch.setattr(AC, "WEB_PUBLIC", tmp_path)
        urls = AC.collect_default_urls()
        # All non-HTTP URLs filtered out.
        assert "mailto:reporter@example.com" not in urls
        assert "javascript:void(0)" not in urls
        assert "" not in urls
        assert "https://valid.example/1" in urls
        assert "https://lda.senate.gov/x" in urls
