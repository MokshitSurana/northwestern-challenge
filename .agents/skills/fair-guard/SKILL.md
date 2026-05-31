---
name: fair-guard
description: >
  Investigative journalism toolkit for federal lobbying disclosure analysis.
  Four modes: doctor (validate setup and guided onboarding), index (ETL pipeline
  for raw LDA data), resolve (normalize messy org/person name strings), and scan
  (find former officials lobbying their old agency by agency concentration ratio).
  Use when investigating federal lobbying, revolving-door cases, or analyzing
  congressional press releases against LDA records.
license: MIT
compatibility: Requires Python 3.11+, uv, Node.js, and npm. Run scripts via `uv run`.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.1"
---

# FairGuard

Investigative journalism toolkit for federal LDA lobbying disclosure data (2022–Q1 2026).

## Modes

Four skills compose a full investigative pipeline:

| Mode | Full name | Purpose | Prerequisite |
|------|-----------|---------|-------------|
| `doctor` | setup-validator | Check all deps and data; optionally launch index | None |
| `index` | lda-corpus-indexer | Parse raw LDA dumps → `investigation.duckdb` | Raw data in `data/` |
| `resolve` | entity-resolver | Normalize org/person names; write `entity_map` (F1 = 0.963) | DuckDB built |
| `scan` | revolving-door-detector | Find former officials lobbying their old agency | DuckDB built |

## Quickstart for new users

The fastest path to running an investigation:

```
1. /fair-guard doctor      — validates environment; offers to build index
2. /fair-guard scan        — produces findings after index is built
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
```

## Mode documentation

Each mode has detailed instructions in its own SKILL.md:

- [`modes/doctor/SKILL.md`](modes/doctor/SKILL.md) — setup validation
- [`modes/index/SKILL.md`](modes/index/SKILL.md) — ETL pipeline
- [`modes/resolve/SKILL.md`](modes/resolve/SKILL.md) — entity resolution
- [`modes/scan/SKILL.md`](modes/scan/SKILL.md) — revolving-door detection

## Anchor finding

The Artemis Group / Jim Bridenstine (NASA) revolving-door case is the verified
anchor finding. Details in `notes/05_finding_bridenstine.md`.
Numbers: 133 Senate filings, 52 targeting NASA (39.1% concentration), 115 House filings.
