---
name: pressrel
description: >
  Cross-references Congressional press releases against lobbying-clients findings.
  Given a client name, firm, or topical phrase, searches 141K+ House and Senate
  press releases (2022–2026) for verified mentions and returns a journalism-ready
  table of date · member (party-state-chamber) · title · URL · matched snippet,
  plus per-client tallies and a framing note. The press-release half of the
  FairGuard corpus — pairs with scan (revolving-door-detector) and trace
  (federal-award-tracer) to turn a structural pattern into a story with named
  legislators in it. Use whenever someone wants to know which members of Congress
  have publicly mentioned a company, advocated for a project, or named an industry
  term tied to a lobbying client, and especially when investigating whether a
  member who praised an entity sits on the committee whose former staff lobby
  for that entity.
license: MIT
compatibility: Requires Python 3.11+ and uv. Reads output/investigation.duckdb (press_releases table) — no network access needed.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  part-of: fair-guard
  companion-to: revolving-door-detector, federal-award-tracer
  tools: bash, python, file-read, file-write
---

# press-release-cross-ref

Short-name `pressrel`. The submission-facing full skill file lives at
`skill/press-release-cross-ref/SKILL.md`; this modes copy mirrors the same
guidance with frontmatter cleaned up for the agentskills.io spec.

## What this skill does

`scan` finds *who* the former agency officials lobbying their old agency are.
`trace` follows the *money* from that agency to their clients. This skill
closes the loop on the third side of the triangle: which **members of
Congress** have been publicly speaking about, advocating for, or otherwise
aligning themselves with those same clients.

Given one or more client / firm / topical names, it queries the
`press_releases` table in `output/investigation.duckdb` (141,332 House and
Senate press releases, 2022–Q1 2026) for verified mentions and emits:

1. A **per-client tally** — mentions, distinct members, first and last date.
2. A **matches table** — date, member (party · state · chamber), title, URL,
   and a snippet showing the matched phrase in context.
3. A **framing note** explaining what the matches mean and what they don't.
4. *(Default-on)* Web writes that attach the result to the scan finding card
   in the Reporter UI and append the report to a global feed.

## The matching discipline

Two things this skill gets right that a bare grep gets wrong:

- **Word boundaries** around every alias (regex `\b`), so "Cargill" doesn't
  false-match "Cargilltechnologies."
- **De-duplication** on `(bioguide_id, date, title)`, so re-issued releases
  and cross-posts don't inflate the per-client tally.

Plus smart-quote tolerance ("O'Lakes" matches "O'Lakes"), snippet extraction
with the matched phrase wrapped in `**bold**`, and member-side filters
(party / state / chamber / domain).

## CLI surface

```bash
# Ad-hoc
uv run scripts/05_pressrel_search.py --mention "critical minerals"
uv run scripts/05_pressrel_search.py --mention "Cargill" --party Democrat --chamber Senate

# Case file (recommended for multi-client queries)
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json

# Auto-enrich every scan finding card in one pass (~10s)
uv run scripts/05_pressrel_search.py --enrich-findings

# Persist outputs
uv run scripts/05_pressrel_search.py --case <case.json> --out notes/pr.md --json output/pr.json

# CI mode (skip web writes)
uv run scripts/05_pressrel_search.py --case <case.json> --no-web

# Schema
uv run scripts/05_pressrel_search.py --print-template
```

## Case-file schema

| Key | Meaning |
|-----|---------|
| `case_id` | Stable id; upsert key in `web/public/press_releases.json`. |
| `label` | Header for the report. |
| `clients[].name` | Display name in the per-client tally. |
| `clients[].aliases` | Word-bounded, case-insensitive phrases. Defaults to `[name]`. |
| `filters.since` / `.until` | Date window (defaults 2022-01-01 / 2026-04-01). |
| `filters.party` / `.state` / `.chamber` / `.domain_contains` | Member-side filters. |
| `match` (optional) | List of `{lobbyist_name, agency_short}` keys. When present, the report is embedded into matching `findings.json` rows. |

## Outputs

| Destination | Content |
|-------------|---------|
| stdout / `--out FILE` | Markdown report. |
| `--json FILE` | Raw JSON payload. |
| `web/public/press_releases.json` | Upserted per `case_id`. Drives `/pressrel` route. |
| `web/public/findings.json` | If `match` is present, matching rows gain a `press_releases` field. |

Use `--no-web` to skip the last two.

## Reproducibility

Bundled cases in `skill/press-release-cross-ref/cases/` (Steinberg DOE,
Limbaugh Interior) reproduce against the committed corpus.
