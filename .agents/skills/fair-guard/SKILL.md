---
name: fair-guard
description: >
  Investigative journalism toolkit for federal lobbying disclosure analysis.
  Nine modes: doctor (validate setup and guided onboarding), index (ETL pipeline
  for raw LDA data), resolve (normalize messy org/person name strings), scan
  (find former officials lobbying their old agency by agency concentration
  ratio), trace (follow the money — federal awards from an agency to a
  lobbyist's clients on USAspending.gov), pressrel (cross-reference
  Congressional press releases for verified mentions of a client / firm /
  topic — pairs with scan and trace to name the members of Congress publicly
  aligning themselves with the same companies), coi (compose the outputs of
  scan, trace, and pressrel into a conflict-of-interest graph that surfaces
  triangles, hubs, and bridges across all the other skills), comment
  (materialize the request-for-comment workflow — log sends, acknowledgments,
  replies, follow-ups, and closures with derived status and deadline pressure
  rules), and archive (snapshot every cited URL to Wayback Machine +
  Archive.today with retry/backoff before publication). Use when investigating
  federal lobbying, revolving-door cases, federal award/grant money trails,
  analyzing congressional press releases against LDA records, tracking
  outreach to subjects of investigation, or preserving citations before
  publication.
license: MIT
compatibility: Requires Python 3.11+, uv, Node.js, and npm. Run scripts via `uv run`. The trace mode needs network access to api.usaspending.gov; pressrel reads the local DuckDB; coi and comment read on-disk JSON only; archive needs network access to web.archive.org and archive.ph.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.5"
---

# FairGuard

Investigative journalism toolkit for federal LDA lobbying disclosure data + 141K Congressional press releases (2022–Q1 2026).

## Modes

Nine skills compose a full investigative pipeline:

| Mode | Full name | Purpose | Prerequisite |
|------|-----------|---------|-------------|
| `doctor` | setup-validator | Check all deps and data; optionally launch index | None |
| `index` | lda-corpus-indexer | Parse raw LDA dumps → `investigation.duckdb` | Raw data in `data/` |
| `resolve` | entity-resolver | Normalize org/person names; write `entity_map` (F1 = 0.963) | DuckDB built |
| `scan` | revolving-door-detector | Find former officials lobbying their old agency | DuckDB built |
| `trace` | federal-award-tracer | Follow the money: agency → lobbyist's clients on USAspending.gov | Network; a case file |
| `pressrel` | press-release-cross-ref | Cross-reference Congressional press releases for mentions of a client / firm / topic | DuckDB built |
| `coi` | coi-graph | Compose scan + trace + pressrel into a conflict-of-interest graph; surface triangles, hubs, bridges | findings.json (scan first) |
| `comment` | comment-tracker | Materialize the request-for-comment workflow (sends, replies, status, deadlines) | `notes/comment_requests/comment_log.json` (always present) |
| `archive` | archive-on-cite | Snapshot every cited URL to Wayback + Archive.today before publication | Network; the on-disk web/public/*.json |

scan, trace, and pressrel each produce a list. coi turns those three lists
into a *graph* so the connections across them become visible — the headline
output is **triangles**: a member of Congress publicly mentioning a client
whose lobbyist used to staff that client's funding agency. comment and
archive close the two editorial gates that separate a good investigation
from a publishable one: documenting that you gave subjects a fair chance to
respond, and ensuring every cited URL will still resolve when the story
runs.

## Quickstart for new users

The fastest path to running an investigation:

```
1. /fair-guard doctor      — validates environment; offers to build index
2. /fair-guard scan        — produces findings after index is built
3. /fair-guard trace       — follow the money (USAspending) for a candidate
4. /fair-guard pressrel    — cross-ref press releases for the candidate's clients
5. /fair-guard coi         — compose everything into the conflict-of-interest graph
6. /fair-guard comment     — track outreach to subjects of investigation
7. /fair-guard archive     — snapshot every cited URL before publication
```

**No raw data? Download the pre-built database (~10 min):**
https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing
Unzip and place `output/` at the project root. Then run `/fair-guard scan` directly.

## Manual invocation

```bash
# Build index from raw corpus (~2.5 hr full / ~2 min sample)
uv run scripts/01_build_index.py
uv run scripts/01_build_index.py --sample

# Detect revolving-door patterns
uv run scripts/03_agency_concentration.py
uv run scripts/03_agency_concentration.py --agency nasa

# Follow the money (USAspending)
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json

# Cross-ref press releases (local DuckDB)
uv run scripts/05_pressrel_search.py --enrich-findings   # bulk pass first
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json

# Build the conflict-of-interest graph (composes the other skills' outputs)
uv run scripts/06_coi_graph.py

# Track request-for-comment outreach
uv run scripts/07_comment_tracker.py list
uv run scripts/07_comment_tracker.py log <firm> sent --addresses "press@x.com"

# Archive every cited URL to Wayback + Archive.today
uv run scripts/08_archive_cite.py
```

**Ordering matters for pressrel:** run `--enrich-findings` BEFORE any
case-file runs. `--enrich-findings` uses literal `top_clients_str` aliases
and bulk-populates every finding row; case-file runs then re-overwrite the
matched rows with richer per-alias data (e.g. `Cargill` finds many more
press releases than `CARGILL INC`). Reversing the order silently drops
coi-graph triangles from 11 to ~4.

## Mode documentation

Each mode has detailed instructions in its own SKILL.md:

- [`modes/doctor/SKILL.md`](modes/doctor/SKILL.md) — setup validation
- [`modes/index/SKILL.md`](modes/index/SKILL.md) — ETL pipeline
- [`modes/resolve/SKILL.md`](modes/resolve/SKILL.md) — entity resolution
- [`modes/scan/SKILL.md`](modes/scan/SKILL.md) — revolving-door detection
- [`modes/trace/SKILL.md`](modes/trace/SKILL.md) — federal award money trail
- [`modes/pressrel/SKILL.md`](modes/pressrel/SKILL.md) — Congressional press-release cross-ref
- [`modes/coi/SKILL.md`](modes/coi/SKILL.md) — conflict-of-interest graph composition
- [`modes/comment/SKILL.md`](modes/comment/SKILL.md) — request-for-comment workflow tracker
- [`modes/archive/SKILL.md`](modes/archive/SKILL.md) — Wayback + Archive.today snapshotter

## Anchor finding

The Artemis Group / Jim Bridenstine (NASA) revolving-door case is the verified
anchor finding. Details in `notes/05_finding_bridenstine.md`.
Numbers: 133 Senate filings, 52 targeting NASA (39.1% concentration), 115 House filings.
