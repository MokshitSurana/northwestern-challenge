# Trace — `/fair-guard comment`

**Date:** 2026-06-07
**Skill invoked:** `comment` (comment-tracker v1.0.0)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** Status table rendered for all 7 firms (all currently `not_sent` because the actual outreach hasn't happened yet); web/public/comment_log.json mirror written for the Reporter UI's `/comments` route.

---

## Invocation

```bash
uv run scripts/07_comment_tracker.py list
```

The dispatcher noted that `comment` requires no DB or network — the source log lives in `notes/comment_requests/comment_log.json` (committed). Routed to `skill/comment-tracker/SKILL.md`.

## Output (verbatim)

```
Status                       Days since send   Deadline Firm
-----------------------------------------------------------------------------------------------
⬜ Not sent                                 —          —  Venn Strategies
⬜ Not sent                                 —          —  The Ferguson Group, LLC
⬜ Not sent                                 —          —  Delta Strategy Group
⬜ Not sent                                 —          —  Torrey Advisory Group
⬜ Not sent                                 —          —  Invariant LLC
⬜ Not sent                                 —          —  Waneta Strategies, LLC
⬜ Not sent                                 —          —  Spirit Rock Consulting
```

All 7 firms are at the starting state (`not_sent`). The drafts are ready in `notes/comment_requests/*.md` — each firm has a per-packet markdown with the addressee guidance, the send-ready subject + body, a response-log section, and internal notes (money figures, §207 status, framing reminders).

## Invocation 2 — append an event

```bash
uv run scripts/07_comment_tracker.py log venn_strategies sent \
    --addresses "press@vennstrategies.com,bsteinberg@vennstrategies.com" \
    --deadline 2026-06-15 \
    --summary "Sent per the draft in notes/comment_requests/venn_strategies.md"
```

(This was run in development as a smoke test, then reverted in the committed log.)

**Script behavior:**

1. Validated the firm key exists in `comment_log.json` (`venn_strategies` is one of the 7 seeded entries).
2. Validated the event kind is one of the six supported (`sent`, `acknowledged`, `substantive_reply`, `followup_sent`, `closed`, `legal_threat`).
3. Appended an event to the firm's timeline with an ISO-8601 UTC timestamp.
4. For `sent` events specifically: persisted the `addresses_used` list and computed a default deadline (`sent + 7 calendar days`) if `--deadline` wasn't passed.
5. Re-derived the live status from the event timeline (`derive_status()` walks the events, applies deadline pressure if applicable, returns one of 10 vocab statuses).
6. Wrote the updated `notes/comment_requests/comment_log.json` (the source of truth, committed).
7. Auto-ran `export` to write `web/public/comment_log.json` — the slimmed mirror the UI reads, with derived statuses, metrics (`days_since_send`, `days_until_deadline`, `has_substantive`), and an urgency-sorted entry list.

**Output:**

```
logged sent for venn_strategies; status now sent
wrote web/public/comment_log.json (7 entries, 0 warnings)
```

## Invocation 3 — per-firm detail

```bash
uv run scripts/07_comment_tracker.py status venn_strategies
```

```
# Venn Strategies
  case:     Benjamin Steinberg → Department of Energy
  draft:    notes/comment_requests/venn_strategies.md
  status:   📤 Sent
  events:   1
  sent:     0 days ago
  deadline: 2026-06-15 (+7 days)

  [2026-06-07T04:01:23.882550+00:00] sent
    to=press@vennstrategies.com, bsteinberg@vennstrategies.com
    — Sent per the draft in notes/comment_requests/venn_strategies.md
```

## The judgment that mattered

The script intentionally does NOT support batch updates. Each `log` call is a deliberate, considered append. The reasoning: an investigative outreach record's value is in its precision (which addresses, what time, what outcome) — a script that lets a reporter mass-update timelines makes the record less trustworthy, not more.

The status-derivation rules are also load-bearing:

- A `substantive_reply` event is decisive — nothing later (except `closed` or `legal_threat`) can downgrade the status.
- A `followup_sent` event without a subsequent `acknowledged` or `substantive_reply` downgrades to `awaiting_substantive` (reflects "we tried again, they still haven't moved").
- A `legal_threat` event overrides everything else — escalates to `escalated_to_counsel` regardless of what came after. The team's counsel is now handling it.

All three rules + the deadline-pressure logic (overdue + no substantive → `no_response_by_deadline`) are pinned in `tests/test_comment_tracker.py::TestDeriveStatus`.

## Reproducibility

The status derivation is pure: `same input timeline + same deadline + same now → same output`. The 25 tests cover every status-rule edge case and the CLI round-trip.

```bash
# Read-only inspection:
uv run scripts/07_comment_tracker.py list
uv run scripts/07_comment_tracker.py status venn_strategies

# Append (each event is a deliberate one-line command):
uv run scripts/07_comment_tracker.py log venn_strategies sent --addresses a,b
uv run scripts/07_comment_tracker.py log venn_strategies substantive_reply --pointer URL --summary "..."

# Re-export web mirror without logging anything:
uv run scripts/07_comment_tracker.py export
```

## Why the log is committed

`notes/comment_requests/comment_log.json` is in the repo so a fact-checker — internal or external — can audit the outreach record across the whole team. The drafts in `notes/comment_requests/*.md` plus the log = a complete record of "we asked, they responded (or didn't), here's when, here's how to verify."

The `web/public/comment_log.json` mirror is a derived view (status + metrics + urgency-sort) so the Reporter UI's `/comments` route can render without re-implementing the derivation rules client-side.
