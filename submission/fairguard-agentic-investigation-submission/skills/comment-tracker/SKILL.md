---
name: comment-tracker
description: >
  Materializes the request-for-comment workflow. The drafts in
  notes/comment_requests/ are ready to send — this skill turns the per-firm
  packets and the shared comment_log.json into a real, auditable system: a
  one-line CLI for logging events (sent, acknowledged, substantive_reply,
  followup_sent, closed, legal_threat), automatic derivation of the live
  status from each firm's event timeline, deadline-pressure rules that flag
  outreach overdue without a reply, and a web mirror that drives a /comments
  route in the Reporter UI. Use whenever you're about to send a request for
  comment, acknowledge a firm's response, follow up on overdue outreach, log
  a substantive reply or legal threat, or check the status of where the
  team's comment requests stand.
license: MIT
compatibility: Requires Python 3.11+ and uv. No network access needed.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# comment-tracker

## What this skill does

`notes/comment_requests/` carries the *drafts*. This skill turns those drafts
into a *workflow* — a real, auditable system for tracking which firms have
been contacted, when, by whom, with what addresses, and how (and when) each
firm responded.

The shape is intentionally minimal: append-only events on a per-firm
timeline, a derived "live status" computed from the event sequence plus the
deadline, and a one-line CLI that prevents the JSON file from drifting out
of its schema. The source of truth is
`notes/comment_requests/comment_log.json`, committed to the repo so a fact-
checker can audit the outreach record across the whole team. The Reporter
UI's `/comments` route reads a slimmer mirror at `web/public/comment_log.json`.

## Why this matters for journalism

Investigative pieces about real firms and real people get killed late by two
things: (a) a subject was never actually given the chance to respond, and
(b) the response that did come in didn't make it back to the editor before
print. A scattered set of email threads and notes/comment_requests/*.md
files solves neither. A structured log that the UI surfaces ("3 days until
Venn Strategies deadline; ⚠ Ferguson is overdue") solves both.

## Event vocabulary

Six event kinds; the derived status is computed from the latest meaningful
event in the timeline, with deadline pressure layered on top.

| Event kind | When to log it |
|---|---|
| `sent` | First outreach to the firm. Logs addresses, optionally a deadline (defaults to send + 7 calendar days). |
| `acknowledged` | A press office, comms person, or counsel acknowledged receipt — but hasn't responded substantively. |
| `substantive_reply` | A real on-record statement, declination, denial, or any other substantive response. Decisive — nothing later (except `closed`, `legal_threat`) downgrades it. |
| `followup_sent` | A second outreach because the original wasn't acknowledged or wasn't substantive. |
| `closed` | The reporter has formally closed this outreach. Requires `--kind response` or `--kind no_response`. |
| `legal_threat` | The firm or its counsel threatened legal action. Escalates to `escalated_to_counsel` and overrides everything else. |

## Status vocabulary (derived from events)

| Status | Meaning |
|---|---|
| `not_drafted` | No draft exists yet. Used for top-10 candidates without an individual packet (e.g. The Russell Group, FGS Global — they fold into the USDA aggregate). |
| `not_sent` | A draft exists; no `sent` event yet. |
| `sent` | Outreach sent, deadline not yet passed, no acknowledgment. |
| `acknowledged` | Acknowledged but no substantive reply. |
| `awaiting_substantive` | Followed up, still no substantive reply (within deadline). |
| `responded` | Substantive reply received. Decisive. |
| `no_response_by_deadline` | Deadline passed, no acknowledged or substantive reply. Distinct from `closed_no_response` (which is the editorial decision to formally close). |
| `closed_response` | Reporter closed the outreach as `--kind response`. |
| `closed_no_response` | Reporter closed the outreach as `--kind no_response`. |
| `escalated_to_counsel` | A `legal_threat` event was logged. The team's counsel is now handling it. |

## CLI surface

```bash
# Read
uv run skills/comment-tracker/scripts/07_comment_tracker.py list                  # all firms with status + days
uv run skills/comment-tracker/scripts/07_comment_tracker.py status venn_strategies # one firm, with timeline

# Write (one line per event)
uv run skills/comment-tracker/scripts/07_comment_tracker.py log venn_strategies sent \
    --addresses "press@vennstrategies.com,bsteinberg@vennstrategies.com" \
    --deadline 2026-06-15 \
    --summary "Sent per draft"

uv run skills/comment-tracker/scripts/07_comment_tracker.py log venn_strategies acknowledged \
    --by "Press Office" --summary "Acknowledged receipt, working on response"

uv run skills/comment-tracker/scripts/07_comment_tracker.py log venn_strategies substantive_reply \
    --pointer "https://internal-drive/venn-statement-2026-06-15.eml" \
    --summary "Brief statement: no comment on individual matters; firm has §207 screening process"

uv run skills/comment-tracker/scripts/07_comment_tracker.py log venn_strategies followup_sent \
    --addresses press@vennstrategies.com

uv run skills/comment-tracker/scripts/07_comment_tracker.py log venn_strategies closed \
    --kind response --summary "Used the brief statement in print"

uv run skills/comment-tracker/scripts/07_comment_tracker.py log acme_corp legal_threat \
    --by "Smith & Co Attorneys" \
    --summary "C&D threat received; escalated to outlet counsel"

# Web mirror (auto-run after every `log`; also runnable manually)
uv run skills/comment-tracker/scripts/07_comment_tracker.py export                # writes web/public/comment_log.json
```

## What gets written where

| Destination | Content |
|---|---|
| `notes/comment_requests/comment_log.json` | Source of truth. Committed. Full event timelines, untouched by the script except via the `log` command. |
| `web/public/comment_log.json` | Slimmed mirror with derived status, label, metrics (days since send, days until deadline), urgency-sorted entry list. Read by the Reporter UI's `/comments` route. |
| stdout | `list` prints a status table; `status` prints one firm in detail with the full event timeline. |

## Reading the live status table

```
Status                       Days since send   Deadline Firm
-----------------------------------------------------------------------------------------------
🚨 Escalated to counsel                    7  2026-06-15 (-2d)  Acme Corp
⚠ No response by deadline                  9  2026-06-14 (-3d)  Ferguson Group
⏳ Awaiting substantive                     5  2026-06-19 (+1d)  Venn Strategies
👁 Acknowledged                             4  2026-06-20 (+2d)  Delta Strategy Group
📤 Sent                                     1  2026-06-23 (+5d)  Spirit Rock Consulting
✅ Closed (response)                       10  2026-06-15 (-2d)  Torrey Advisory Group
⬜ Not sent                                 —          —          Waneta Strategies
```

Urgency-sorted: escalations first, then overdue, then awaiting, then closed.

## Editorial discipline

- **Log immediately after sending** — every minute of drift between actual
  send and log entry is a minute the audit trail is weaker.
- **Pointers, not bodies.** Never paste a private email body into the log.
  Use `--pointer` to reference where the full text lives (a shared drive
  path, an email thread ID), and `--summary` to capture the gist.
- **One firm per `log` call.** The script intentionally does not support
  batch updates — each event should be a deliberate, considered append.
- **Legal threats stop everything.** A `legal_threat` event escalates the
  status to `escalated_to_counsel` and overrides every subsequent event;
  hand off to the outlet's counsel and do not log further events without
  their guidance.

## Reproducibility

The status derivation is pure: same input timeline + same deadline + same
`now` → same output. The integration tests
(`tests/test_comment_tracker.py`) cover every status-rule edge case
(decisive substantive, followup-without-substantive downgrade, deadline
pressure, legal-threat override, close terminations).

To regenerate the web mirror after hand-editing the source log:

```bash
uv run skills/comment-tracker/scripts/07_comment_tracker.py export
```

## When NOT to use this skill

- If you want to draft a *new* request for comment — use the templates in
  `notes/comment_requests/_template.md` first, save the per-firm packet,
  then add the entry to `comment_log.json` manually before the first `log
  sent` call.
- If the question is "what did the subject say?" — the log stores pointers
  and one-line summaries, not full bodies. Open the pointer.
- If you need a quote for print — re-read the substantive_reply's full text
  at the pointer; the log is a status system, not a quote library.
