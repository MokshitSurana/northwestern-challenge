---
name: fair-guard
description: >
  Investigative journalism toolkit for federal lobbying disclosure analysis.
  Seven modes: doctor (validate setup and guided onboarding), index (ETL
  pipeline for raw LDA data), resolve (normalize messy org/person name
  strings), scan (find former officials lobbying their old agency by agency
  concentration ratio), trace (follow the money — federal awards from an
  agency to a lobbyist's clients on USAspending.gov), pressrel (cross-reference
  Congressional press releases for verified mentions of a client / firm /
  topic — pairs with scan and trace to name the members of Congress publicly
  aligning themselves with the same companies), and coi (compose the outputs of
  scan, trace, and pressrel into a conflict-of-interest graph that surfaces
  triangles, hubs, and bridges across all the other skills). Use when
  investigating federal lobbying, revolving-door cases, federal award/grant
  money trails, or analyzing congressional press releases against LDA records.
license: MIT
compatibility: Requires Python 3.11+, uv, Node.js, and npm. Run scripts via `uv run`. The trace mode needs network access to api.usaspending.gov; pressrel reads the local DuckDB; coi reads on-disk JSON only.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.4"
---

# FairGuard

Investigative journalism toolkit for federal LDA lobbying disclosure data + 141K Congressional press releases (2022–Q1 2026).

## Modes

Seven skills compose a full investigative pipeline:

| Mode | Full name | Purpose | Prerequisite |
|------|-----------|---------|-------------|
| `doctor` | setup-validator | Check all deps and data; optionally launch index | None |
| `index` | lda-corpus-indexer | Parse raw LDA dumps → `investigation.duckdb` | Raw data in `data/` |
| `resolve` | entity-resolver | Normalize org/person names; write `entity_map` (F1 = 0.963) | DuckDB built |
| `scan` | revolving-door-detector | Find former officials lobbying their old agency | DuckDB built |
| `trace` | federal-award-tracer | Follow the money: agency → lobbyist's clients on USAspending.gov | Network; a case file |
| `pressrel` | press-release-cross-ref | Cross-reference Congressional press releases for mentions of a client / firm / topic | DuckDB built |
| `coi` | coi-graph | Compose scan + trace + pressrel into a conflict-of-interest graph; surface triangles, hubs, bridges | findings.json (scan first) |

scan, trace, and pressrel each produce a list. coi turns those three lists
into a *graph* so the connections across them become visible — the headline
output is **triangles**: a member of Congress publicly mentioning a client
whose lobbyist used to staff that client's funding agency.

## Quickstart for new users

The fastest path to running an investigation:

```
1. /fair-guard doctor      — validates environment; offers to build index
2. /fair-guard scan        — produces findings after index is built
3. /fair-guard trace       — follow the money (USAspending) for a candidate
4. /fair-guard pressrel    — cross-ref press releases for the candidate's clients
5. /fair-guard coi         — compose everything into the conflict-of-interest graph
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
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json
uv run scripts/05_pressrel_search.py --enrich-findings  # one-shot pass over every scan finding

# Build the conflict-of-interest graph (composes the other skills' outputs)
uv run scripts/06_coi_graph.py
```

## Mode documentation

Each mode has detailed instructions in its own SKILL.md:

- [`modes/doctor/SKILL.md`](modes/doctor/SKILL.md) — setup validation
- [`modes/index/SKILL.md`](modes/index/SKILL.md) — ETL pipeline
- [`modes/resolve/SKILL.md`](modes/resolve/SKILL.md) — entity resolution
- [`modes/scan/SKILL.md`](modes/scan/SKILL.md) — revolving-door detection
- [`modes/trace/SKILL.md`](modes/trace/SKILL.md) — federal award money trail
- [`modes/pressrel/SKILL.md`](modes/pressrel/SKILL.md) — Congressional press-release cross-ref
- [`modes/coi/SKILL.md`](modes/coi/SKILL.md) — conflict-of-interest graph composition

## Anchor finding

The Artemis Group / Jim Bridenstine (NASA) revolving-door case is the verified
anchor finding. Details in `notes/05_finding_bridenstine.md`.
Numbers: 133 Senate filings, 52 targeting NASA (39.1% concentration), 115 House filings.
