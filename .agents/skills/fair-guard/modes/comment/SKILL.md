---
name: comment
description: >
  Materializes the request-for-comment workflow. Turns the per-firm packets
  in notes/comment_requests/ and the shared comment_log.json into a real,
  auditable system: one-line CLI for logging events (sent, acknowledged,
  substantive_reply, followup_sent, closed, legal_threat), automatic
  derivation of the live status from each firm's event timeline,
  deadline-pressure rules that flag outreach overdue without a reply, and a
  web mirror that drives the /comments route in the Reporter UI. Use
  whenever you're about to send a request for comment, acknowledge a firm's
  response, follow up on overdue outreach, log a substantive reply or legal
  threat, or check the status of where the team's comment requests stand.
license: MIT
compatibility: Requires Python 3.11+ and uv. Source of truth at notes/comment_requests/comment_log.json; writes web/public/comment_log.json. No DB, no network.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  part-of: fair-guard
  companion-to: scan, trace, pressrel
  tools: bash, python, file-read, file-write
---

# comment-tracker

Short-name `comment`. Submission-facing full skill file at
`skill/comment-tracker/SKILL.md`; this modes copy mirrors the same guidance
with frontmatter cleaned up for agentskills.io.

## What this skill does

`notes/comment_requests/` carries the *drafts*. This skill turns those
drafts into a *workflow* — a real, auditable system for tracking which firms
have been contacted, when, by whom, with what addresses, and how (and when)
each firm responded.

The source of truth is `notes/comment_requests/comment_log.json`. The
Reporter UI's `/comments` route reads a slimmer mirror at
`web/public/comment_log.json`.

## Event vocabulary (six kinds)

`sent`, `acknowledged`, `substantive_reply`, `followup_sent`, `closed`,
`legal_threat`. Derived status is computed from the latest meaningful event
in each firm's timeline, with deadline pressure layered on top.

## Status vocabulary (10)

`not_drafted`, `not_sent`, `sent`, `acknowledged`, `awaiting_substantive`,
`responded`, `no_response_by_deadline`, `closed_response`,
`closed_no_response`, `escalated_to_counsel`.

## CLI surface

```bash
uv run scripts/07_comment_tracker.py list                   # all firms + status
uv run scripts/07_comment_tracker.py status venn_strategies # one firm + timeline
uv run scripts/07_comment_tracker.py log <firm> sent --addresses a@x,b@x [--deadline DATE]
uv run scripts/07_comment_tracker.py log <firm> acknowledged --by "Press Office" --summary "..."
uv run scripts/07_comment_tracker.py log <firm> substantive_reply --pointer URL --summary "..."
uv run scripts/07_comment_tracker.py log <firm> followup_sent --addresses press@firm
uv run scripts/07_comment_tracker.py log <firm> closed --kind response|no_response [--summary "..."]
uv run scripts/07_comment_tracker.py log <firm> legal_threat --by "Counsel" --summary "..."
uv run scripts/07_comment_tracker.py export                 # only write web mirror
```

## Outputs

| Destination | Content |
|---|---|
| `notes/comment_requests/comment_log.json` | Source of truth, committed |
| `web/public/comment_log.json` | Slimmed mirror, urgency-sorted, for /comments |
| stdout | Status table or per-firm detail |

## Editorial discipline

- Log immediately after sending — every minute of drift weakens the audit trail.
- Use `--pointer`, not bodies — never paste private email contents into the log.
- One firm per `log` call — deliberate, considered appends only.
- Legal threats stop everything — hand off to counsel.
