# Interaction traces — index

This directory contains the Claude Code interaction traces behind FairGuard. Two kinds:

- **Curated, rendered transcripts (`trace-01` … `trace-11`, Markdown).** Human-readable
  session logs, one per skill plus two narrative sessions, showing the prompts, tool
  calls, outputs, and — importantly — the points where human judgment intervened
  (parser-bug diagnosis, name-token corrections, discretionary-vs-routine framing calls).
  These are the primary artifact for connecting a trace to a skill and a finding.
- **Raw session logs (`*.jsonl`).** Complete, unedited Claude Code session records (JSONL,
  one event per line: prompts, assistant turns, tool calls and their results). Three are
  included — see below.

**Raw logs included:**

1. `trace-raw-repro-scan-finding02.jsonl` — a **live reproduction** of the `scan`
   (revolving-door-detector) run, regenerating **Finding 02** (139 candidates / 22
   agencies) and re-confirming the **Finding 01** Bridenstine/Artemis/NASA anchor. Full
   tool-call trace.
2. `trace-raw-repro-trace-moneytrail.jsonl` — a **live reproduction** of the `trace`
   (federal-award-tracer) run against the live USAspending.gov API, regenerating the
   **Finding 02 money trail** (Steinberg → DOE $1,080,820,046 exact; Limbaugh → Interior).
   Full tool-call trace.
3. `trace-raw-session-tracev1.1-evals-and-gates.jsonl` — one complete substantive working
   session (the `federal-award-tracer` v1.1 eval loop, the §207 + request-for-comment
   reportability-gate closure in `notes/09`, and this submission packaging).

**A note on completeness (disclosed honestly):** FairGuard was built across many sessions
over several weeks on two developers' machines. Claude Code retains raw `.jsonl`
transcripts only locally and only for a limited window, so most *original* build sessions
are no longer recoverable as raw logs. The curated Markdown transcripts (`trace-01`…
`trace-11`) were authored from those sessions as they happened and are the faithful record
of the work. Because **every finding is reproducible**, we also captured the two live
reproduction logs above: they show the actual skills regenerating the reported findings,
end to end, via real tool calls — the strongest available evidence that the findings come
from the skills as shipped.

## Trace → skill → finding map

| Trace file | Skill invocation | Supports finding |
|------------|------------------|------------------|
| `trace-01-setup-and-data-exploration.md` | Environment setup, corpus first-look | Foundation for all findings; establishes the corpus scope (2022–Q1 2026) |
| `trace-02-parser-debugging.md` | `index` (lda-corpus-indexer) — diagnosing the 7 silent-data-loss parser bugs | Data integrity behind **every** count; esp. the corrected House lobbyist rows in the Bridenstine anchor |
| `trace-03-skill-doctor.md` | `doctor` (setup-validator) | Reproducibility gate (setup validation) |
| `trace-04-skill-index.md` | `index` (lda-corpus-indexer) | Builds `investigation.duckdb` — substrate for Findings 01 & 02 |
| `trace-05-skill-resolve.md` | `resolve` (entity-resolver, F1 = 0.963) | Entity normalization behind candidate ranking |
| `trace-06-skill-scan.md` | `scan` (revolving-door-detector) | **Finding 02** (structural pattern, 139 candidates / 22 agencies) and the **Finding 01** Bridenstine/Artemis anchor |
| `trace-07-skill-trace.md` | `trace` (federal-award-tracer) | **Finding 02 money trail** — Steinberg→DOE ≈ $1.08B; Limbaugh→Interior $133.1M (grants only); USDA cases |
| `trace-08-skill-pressrel.md` | `pressrel` (press-release-cross-ref) | Congressional press-release corroboration of scan candidates |
| `trace-09-skill-coi.md` | `coi` (coi-graph) | Composed conflict-of-interest graph across scan + trace + pressrel |
| `trace-10-skill-comment.md` | `comment` (comment-tracker) | Reportability gate 4 — request-for-comment workflow |
| `trace-11-skill-archive.md` | `archive` (archive-on-cite) | Citation durability (Wayback + Archive.today snapshots) |
| `trace-raw-repro-scan-finding02.jsonl` | `scan` (revolving-door-detector) — live reproduction | **Finding 02** (139 candidates / 22 agencies) + **Finding 01** anchor, regenerated end-to-end |
| `trace-raw-repro-trace-moneytrail.jsonl` | `trace` (federal-award-tracer) — live reproduction vs. USAspending API | **Finding 02 money trail** — Steinberg → DOE $1,080,820,046 (exact) + Limbaugh → Interior |
| `trace-raw-session-tracev1.1-evals-and-gates.jsonl` | `trace` eval loop + §207/comment gate closure | **Finding 02** money-trail robustness (the wide-net entity-discovery fix) and the reportability-gate analysis in `notes/09` |

## Where human judgment intervened (highlights)

- **`trace-02`** — recognizing that House lobbyist names live under `<lobbyistFirstName>`/
  `<lobbyistLastName>` (not `<lobbyistName>`) and that ALI codes have two schemas; these
  human catches prevented a silent undercount in the Bridenstine anchor.
- **`trace-07` / raw session** — the name-token precision-vs-recall call in
  `federal-award-tracer`: searching the shortest distinctive core term to catch a client's
  project SPVs (e.g. `GROUP14 BAM-2, INC.`) while excluding coincidental name collisions.
- **raw session** — the §207 reading that separates the *expired timed cooling-off bans*
  (which make the lobbying legal) from the *permanent particular-matter bar* (a question to
  put to subjects, not a violation to assert).
