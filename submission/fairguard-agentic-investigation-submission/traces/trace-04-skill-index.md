# Trace — `/fair-guard index` (verification phase)

**Date:** 2026-05-30
**Skill invoked:** `index` (lda-corpus-indexer)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** Full build already on disk (DB ≈ 3 GB, 11 tables). Verifier passes all 34 invariants.

---

## Invocation

`/fair-guard index` was originally run during the initial corpus build
(weeks 1–2 of development). The DB persists at `output/investigation.duckdb`.
This trace captures the **verification phase** of the skill — the part a
judge will re-run on a clean clone after either rebuilding or downloading
the pre-built `output/`.

```bash
uv run scripts/verify_build.py
```

## Why a verifier exists

The `index` ETL script previously had no automated check that the parsers
produced sane output. During development we hit silent data loss bugs (e.g.
House lobbyist names parsed as all-NULL because of an XML schema mismatch).
The verifier asserts post-build invariants that would catch any regression
of those bugs immediately, instead of waiting for `scan` to return zero
results.

## Output (verbatim)

```
Verifying output\investigation.duckdb  (mode: full)
  PASS  press_releases: 141,332 rows in expected range
  PASS  senate_filings: 418,170 rows in expected range
  PASS  senate_activities: 799,192 rows in expected range
  PASS  senate_lobbyists: 2,121,863 rows in expected range
  PASS  senate_gov_entities: 2,016,363 rows in expected range
  PASS  senate_contributions: 636,833 rows in expected range
  PASS  senate_foreign_entities: 3,627 rows in expected range
  PASS  house_filings: 409,640 rows in expected range
  PASS  house_activities: 781,004 rows in expected range
  PASS  house_lobbyists: 2,017,296 rows in expected range
  PASS  view senate_spend_by_issue: 1,343 rows
  PASS  view revolving_door: 582,114 rows
  PASS  senate_filings.filing_uuid: 0.0% null (≤ 0.1%)
  PASS  senate_filings.registrant_name: 0.0% null (≤ 0.1%)
  PASS  senate_filings.filing_year: 0.0% null (≤ 0.1%)
  PASS  senate_lobbyists.filing_uuid: 0.0% null (≤ 0.1%)
  PASS  senate_lobbyists.lobbyist_name: 0.0% null (≤ 30.0%)
  PASS  senate_gov_entities.filing_uuid: 0.0% null (≤ 0.1%)
  PASS  senate_gov_entities.entity_name: 0.0% null (≤ 0.1%)
  PASS  house_filings.house_id: 0.0% null (≤ 0.1%)
  PASS  house_filings.org_name: 0.8% null (≤ 5.0%)
  PASS  house_filings.filing_year: 0.0% null (≤ 0.1%)
  PASS  house_lobbyists.house_id: 0.0% null (≤ 0.1%)
  PASS  house_lobbyists.lobbyist_name: 0.0% null (≤ 30.0%)
  PASS  press_releases.bioguide_id: 0.1% null (≤ 30.0%)
  PASS  press_releases.text: 0.1% null (≤ 5.0%)
  PASS  senate_filings.filing_year: all integer-castable
  PASS  senate_filings.income: all numeric-castable
  PASS  senate_lobbyists: every filing_uuid joins to senate_filings
  PASS  house_lobbyists: every house_id joins to house_filings
  PASS  anchor: Bridenstine — Artemis Group exists in Senate filings → 133 rows
  PASS  anchor: Bridenstine — appears as a Senate lobbyist → 182 rows
  PASS  anchor: House lobbyist names are populated (not all-null) → 2017296 rows
  PASS  anchor: NASA appears as a Senate gov entity → 2605 rows

  Summary: 34 passed, 0 warning(s), 0 failure(s)
  Build verified.
```

## What was verified

| Layer | Checks |
|---|---|
| Table presence + row count ranges | 10 tables |
| Convenience views present | 2 (`revolving_door`, `senate_spend_by_issue`) |
| Required columns non-null at thresholds | 14 |
| Type sanity (cast invariants) | 2 |
| Foreign-key joinability | 2 |
| Sentinel anchor queries | 4 (incl. Bridenstine + Artemis Group) |

The sentinel anchors are the most important. If the parser breaks the
Senate JSON path (as happened at one point during development), the
`Bridenstine — Artemis Group exists in Senate filings → 0 rows` check
would fail loudly. Same for the all-null lobbyist name regression on House
XML.

## On the original ETL

The actual `01_build_index.py` run takes ~2.5 hours for the full corpus
and ~2 min for `--sample` (one quarter per source). The full build's tqdm
progress logs are preserved at `notes/01c_rebuild_log.txt`. Per-quarter
trace lines look like:

```
[senate/2024] read 47 files → 102_853 filings, 482_711 lobbyists, …
[house/2024Q4] glob 38_104 XML → wrote 1 parquet (38_104 rows, 95.2 MB)
```

## Reproducibility

A clean-clone re-run of `/fair-guard index` followed by
`/fair-guard verify_build` (or `scripts/verify_build.py` directly)
produces this same 34-pass output on the same input data. Sample-mode runs
use the same script with `--sample` and pass under the smaller thresholds.
