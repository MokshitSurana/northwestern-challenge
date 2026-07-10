#!/usr/bin/env python3
"""
07_comment_tracker.py — Materialize the request-for-comment workflow.

The drafts in notes/comment_requests/ are *ready to send* — but a Markdown
draft is not a workflow. This script turns the per-firm packets and the
shared comment_log.json into a real, auditable system:

  1. Validates the log against the schema (status vocabulary, event kinds).
  2. Computes derived status from the latest event in each firm's timeline.
  3. Flags deadlines that have passed without a substantive reply.
  4. Prints a status table (terminal-readable) AND mirrors the same data into
     web/public/comment_log.json so the Reporter UI's /comments route can
     render it.
  5. Provides a `log` subcommand for adding events in one line rather than
     hand-editing JSON.

The source of truth is notes/comment_requests/comment_log.json — committed to
the repo so a fact-checker can audit the outreach record across the whole
team.

Usage:
    uv run scripts/07_comment_tracker.py list                            # all firms with status
    uv run scripts/07_comment_tracker.py status <firm>                   # one firm, with timeline
    uv run scripts/07_comment_tracker.py log <firm> sent --addresses a,b --deadline 2026-06-15
    uv run scripts/07_comment_tracker.py log <firm> acknowledged --by "Press Office" --summary "..."
    uv run scripts/07_comment_tracker.py log <firm> substantive_reply --pointer mailto:... --summary "..."
    uv run scripts/07_comment_tracker.py log <firm> followup_sent --addresses press@firm
    uv run scripts/07_comment_tracker.py log <firm> closed --kind response --summary "..."
    uv run scripts/07_comment_tracker.py log <firm> closed --kind no_response
    uv run scripts/07_comment_tracker.py log <firm> legal_threat --summary "..."
    uv run scripts/07_comment_tracker.py export                          # only write the web JSON

Notes on time:
    All event timestamps are stored as ISO-8601 UTC. The script never invents
    a date — it always uses the system clock at log time. If you're back-
    dating an event (because the actual send happened earlier and you're
    catching up the log), pass `--at 2026-06-09T14:30:00`.

The four firms named in the structural finding's top-10 USDA bloc share a
single trace case (skill/federal-award-tracer/cases/usda_cases.json), so two
of them — Ashlee Johnson at The Russell Group and Kevin Bailey at FGS Global
— are top-10 candidates without an individual comment-request packet yet.
Their `comment_log.json` entries exist but are flagged with status
'not_drafted' rather than 'not_sent' so the UI shows them as a separate row.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / "notes" / "comment_requests" / "comment_log.json"
WEB_OUT = REPO_ROOT / "web" / "public" / "comment_log.json"

VALID_STATUSES = {
    "not_sent",
    "sent",
    "acknowledged",
    "awaiting_substantive",
    "responded",
    "no_response_by_deadline",
    "closed_response",
    "closed_no_response",
    "escalated_to_counsel",
    "not_drafted",
}

VALID_EVENT_KINDS = {
    "sent", "acknowledged", "substantive_reply",
    "followup_sent", "closed", "legal_threat",
}

# Maps a sequence of events to the derived status. The last event wins for
# most kinds; close-events end the timeline.
STATUS_RULES = {
    # event kind → resulting status (overridable by deadline logic below)
    "sent": "sent",
    "acknowledged": "acknowledged",
    "substantive_reply": "responded",
    "followup_sent": "awaiting_substantive",  # implies sent but no substantive
    "legal_threat": "escalated_to_counsel",
}


# ── Schema validation ─────────────────────────────────────────────────────────


def load_log() -> dict:
    if not LOG_PATH.exists():
        sys.exit(f"FATAL: {LOG_PATH} not found. Run /fair-guard scan first or "
                 "see notes/comment_requests/README.md.")
    return json.loads(LOG_PATH.read_text(encoding="utf-8"))


def save_log(data: dict) -> None:
    LOG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def validate_entry(firm_key: str, entry: dict) -> list[str]:
    """Return a list of validation errors (empty list = valid). We don't
    raise on bad data — the UI should still render whatever we have, and the
    `list` command will surface the errors as warnings."""
    errs: list[str] = []
    for required in ("firm", "case", "draft_path", "status", "events"):
        if required not in entry:
            errs.append(f"{firm_key}: missing required field {required!r}")
    status = entry.get("status")
    if status and status not in VALID_STATUSES:
        errs.append(f"{firm_key}: unknown status {status!r}; expected one of {sorted(VALID_STATUSES)}")
    for i, event in enumerate(entry.get("events", []) or []):
        if not isinstance(event, dict):
            errs.append(f"{firm_key}: events[{i}] is not an object")
            continue
        kind = event.get("kind")
        if kind not in VALID_EVENT_KINDS:
            errs.append(f"{firm_key}: events[{i}] unknown kind {kind!r}")
        if "at" not in event:
            errs.append(f"{firm_key}: events[{i}] missing 'at' timestamp")
    return errs


def validate_all(data: dict) -> list[str]:
    errs: list[str] = []
    for firm_key, entry in (data.get("entries") or {}).items():
        errs.extend(validate_entry(firm_key, entry))
    return errs


# ── Status derivation ─────────────────────────────────────────────────────────


def derive_status(entry: dict, now: datetime | None = None) -> str:
    """Compute the current status from the event timeline + deadline.

    Rules:
      - No events and status_vocabulary 'not_drafted' or 'not_sent' → keep
        whatever the entry says (the draft was prepared but never sent, or
        the draft was never drafted at all).
      - A `closed` event ends the timeline; surface response | no_response.
      - A `legal_threat` event escalates regardless of what came after.
      - Otherwise the latest non-followup event determines the live status:
        substantive_reply → responded, acknowledged → acknowledged, sent →
        sent. A followup_sent without a subsequent acknowledged/substantive
        downgrades to awaiting_substantive (no progress on their side).
      - Independent: if `deadline` has passed AND no substantive reply has
        come in, the status becomes `no_response_by_deadline` (a separate
        bucket from `closed_no_response`, which is the editorial decision)."""
    events = list(entry.get("events", []) or [])
    if not events:
        return entry.get("status") or "not_sent"

    # Walk events for terminal states first.
    for ev in events:
        if ev.get("kind") == "legal_threat":
            return "escalated_to_counsel"
    for ev in reversed(events):
        if ev.get("kind") == "closed":
            return "closed_response" if ev.get("response_kind") == "response" else "closed_no_response"

    # Non-terminal: latest meaningful event drives status.
    status = "not_sent"
    for ev in events:
        kind = ev.get("kind")
        if kind == "sent":
            status = "sent"
        elif kind == "acknowledged":
            status = "acknowledged"
        elif kind == "substantive_reply":
            return "responded"  # decisive — nothing later can downgrade
        elif kind == "followup_sent":
            status = "awaiting_substantive"

    # Deadline pressure layered on top.
    deadline = entry.get("deadline")
    if deadline and status in ("sent", "acknowledged", "awaiting_substantive"):
        try:
            dt = datetime.fromisoformat(deadline)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            now = now or datetime.now(UTC)
            if now > dt:
                return "no_response_by_deadline"
        except (TypeError, ValueError):
            pass
    return status


def derive_metrics(entry: dict, now: datetime | None = None) -> dict:
    """Compute days_since_send, days_until_deadline (negative if overdue),
    counts. Returns None values when not applicable so the UI can render
    placeholders."""
    now = now or datetime.now(UTC)
    out = {
        "days_since_send": None,
        "days_until_deadline": None,
        "n_events": len(entry.get("events") or []),
        "has_substantive": any(
            (e.get("kind") == "substantive_reply") for e in entry.get("events") or []
        ),
    }
    sent_events = [e for e in entry.get("events") or [] if e.get("kind") == "sent"]
    if sent_events:
        try:
            sent_at = datetime.fromisoformat(sent_events[0]["at"])
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=UTC)
            out["days_since_send"] = (now - sent_at).days
        except (TypeError, ValueError, KeyError):
            pass
    if entry.get("deadline"):
        try:
            dt = datetime.fromisoformat(entry["deadline"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            out["days_until_deadline"] = (dt - now).days
        except (TypeError, ValueError):
            pass
    return out


# ── CLI commands ──────────────────────────────────────────────────────────────


STATUS_LABELS = {
    "not_drafted": "⚪ Not drafted",
    "not_sent": "⬜ Not sent",
    "sent": "📤 Sent",
    "acknowledged": "👁 Acknowledged",
    "awaiting_substantive": "⏳ Awaiting substantive",
    "responded": "✓ Responded",
    "no_response_by_deadline": "⚠ No response by deadline",
    "closed_response": "✅ Closed (response)",
    "closed_no_response": "❌ Closed (no response)",
    "escalated_to_counsel": "🚨 Escalated to counsel",
}


def cmd_list(_args) -> int:
    data = load_log()
    errs = validate_all(data)
    if errs:
        sys.stderr.write("WARNINGS:\n")
        for e in errs:
            sys.stderr.write(f"  {e}\n")
        sys.stderr.write("\n")
    entries = data.get("entries") or {}
    if not entries:
        print("(no entries in comment_log.json)")
        return 0
    print(f"{'Status':<28} {'Days since send':>15} {'Deadline':>10} {'Firm'}")
    print("-" * 95)
    for key, entry in entries.items():
        status = derive_status(entry)
        metrics = derive_metrics(entry)
        days_send = metrics["days_since_send"]
        deadline = entry.get("deadline") or "—"
        days_dl = metrics["days_until_deadline"]
        deadline_str = (
            f"{deadline} ({days_dl:+d}d)" if days_dl is not None else deadline
        )
        days_send_str = f"{days_send}" if days_send is not None else "—"
        label = STATUS_LABELS.get(status, status)
        firm = entry.get("firm") or key
        print(f"{label:<28} {days_send_str:>15} {deadline_str:>10}  {firm}")
    return 0


def cmd_status(args) -> int:
    data = load_log()
    entry = (data.get("entries") or {}).get(args.firm)
    if not entry:
        sys.exit(f"no entry for firm {args.firm!r}; known: "
                 f"{sorted((data.get('entries') or {}).keys())}")
    status = derive_status(entry)
    metrics = derive_metrics(entry)
    print(f"# {entry.get('firm')}")
    print(f"  case:     {entry.get('case')}")
    print(f"  draft:    {entry.get('draft_path')}")
    print(f"  status:   {STATUS_LABELS.get(status, status)}")
    print(f"  events:   {metrics['n_events']}")
    if metrics["days_since_send"] is not None:
        print(f"  sent:     {metrics['days_since_send']} days ago")
    if metrics["days_until_deadline"] is not None:
        d = metrics["days_until_deadline"]
        print(f"  deadline: {entry.get('deadline')} ({d:+d} days)")
    print()
    for ev in entry.get("events") or []:
        kind = ev.get("kind") or "?"
        at = ev.get("at") or "?"
        by = ev.get("by") or ""
        summary = (ev.get("summary") or "").replace("\n", " ")
        addrs = ", ".join(ev.get("addresses") or [])
        bits = [f"[{at}] {kind}"]
        if by:
            bits.append(f"by={by}")
        if addrs:
            bits.append(f"to={addrs}")
        if summary:
            bits.append(f"— {summary}")
        print("  " + " ".join(bits))
    return 0


def cmd_log(args) -> int:
    data = load_log()
    entry = (data.get("entries") or {}).get(args.firm)
    if not entry:
        sys.exit(f"no entry for firm {args.firm!r}; known: "
                 f"{sorted((data.get('entries') or {}).keys())}")
    if args.kind not in VALID_EVENT_KINDS:
        sys.exit(f"invalid event kind {args.kind!r}; expected one of {sorted(VALID_EVENT_KINDS)}")

    at = args.at or datetime.now(UTC).isoformat()
    event: dict = {"at": at, "kind": args.kind}
    if args.by:
        event["by"] = args.by
    if args.addresses:
        event["addresses"] = [a.strip() for a in args.addresses.split(",") if a.strip()]
    if args.summary:
        event["summary"] = args.summary
    if args.pointer:
        event["pointer"] = args.pointer
    if args.kind == "closed":
        if args.closed_kind not in ("response", "no_response"):
            sys.exit("--kind response|no_response is required for `closed` events")
        event["response_kind"] = args.closed_kind

    entry.setdefault("events", []).append(event)
    if args.kind == "sent":
        entry["addresses_used"] = event.get("addresses", entry.get("addresses_used") or [])
        if args.deadline:
            entry["deadline"] = args.deadline
        elif not entry.get("deadline"):
            # Default deadline: 5 business days from send (≈ 7 calendar days).
            dt = datetime.fromisoformat(at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            entry["deadline"] = (dt + timedelta(days=7)).date().isoformat()

    entry["status"] = derive_status(entry)
    save_log(data)
    sys.stderr.write(f"logged {args.kind} for {args.firm}; status now {entry['status']}\n")
    return cmd_export(args)


def cmd_export(_args) -> int:
    """Write the slimmed web-facing JSON: per-firm derived status + metrics +
    full event timeline. The Reporter UI reads this directly."""
    data = load_log()
    errs = validate_all(data)
    web_entries = []
    for key, entry in (data.get("entries") or {}).items():
        status = derive_status(entry)
        metrics = derive_metrics(entry)
        web_entries.append({
            "key": key,
            "firm": entry.get("firm"),
            "case": entry.get("case"),
            "scan_rank": entry.get("scan_rank"),
            "trail_case_id": entry.get("trail_case_id"),
            "draft_path": entry.get("draft_path"),
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "deadline": entry.get("deadline"),
            "addresses_used": entry.get("addresses_used") or [],
            "metrics": metrics,
            "events": entry.get("events") or [],
        })
    # Sort by urgency: escalations first, then overdue, then awaiting, then closed.
    status_order = {
        "escalated_to_counsel": 0,
        "no_response_by_deadline": 1,
        "awaiting_substantive": 2,
        "acknowledged": 3,
        "sent": 4,
        "not_sent": 5,
        "not_drafted": 6,
        "responded": 7,
        "closed_response": 8,
        "closed_no_response": 9,
    }
    web_entries.sort(key=lambda e: (status_order.get(e["status"], 99), e["firm"] or ""))

    WEB_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_entries": len(web_entries),
        "n_warnings": len(errs),
        "warnings": errs,
        "status_legend": [
            {"status": s, "label": STATUS_LABELS[s]} for s in STATUS_LABELS
        ],
        "entries": web_entries,
    }
    WEB_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    sys.stderr.write(f"wrote {WEB_OUT} ({len(web_entries)} entries, {len(errs)} warnings)\n")
    return 0


# ── argparse wiring ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Print the status table for all firms.")

    p_status = sub.add_parser("status", help="Detailed status for one firm.")
    p_status.add_argument("firm", help="Firm key (e.g. venn_strategies)")

    p_log = sub.add_parser("log", help="Append an event to a firm's timeline.")
    p_log.add_argument("firm", help="Firm key (e.g. venn_strategies)")
    p_log.add_argument("kind", choices=sorted(VALID_EVENT_KINDS), help="Event kind.")
    p_log.add_argument("--at", help="ISO-8601 datetime (defaults to now).")
    p_log.add_argument("--by", help="Person/office on the firm side (for ack/reply).")
    p_log.add_argument("--addresses", help="Comma-separated addresses used.")
    p_log.add_argument("--summary", help="One-line description; for substantive content, store a pointer.")
    p_log.add_argument("--pointer", help="Pointer to substantive content (URL, mail thread ref).")
    p_log.add_argument("--deadline", help="Set deadline (only meaningful for 'sent'; default = sent + 7 days).")
    p_log.add_argument("--kind", dest="closed_kind", choices=["response", "no_response"],
                       help="For 'closed' events: was the outcome a response or no_response?")

    sub.add_parser("export", help="Write web/public/comment_log.json from the source log.")
    return ap


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args()
    return {
        "list": cmd_list,
        "status": cmd_status,
        "log": cmd_log,
        "export": cmd_export,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
