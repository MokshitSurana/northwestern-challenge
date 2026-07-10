---
name: lda-corpus-indexer
description: >
  Converts raw federal LDA lobbying disclosure dumps (Senate JSON + House XML +
  congressional press release JSONL) into a flat, queryable DuckDB analytical
  store with full per-row provenance. Use this skill when a journalist or
  researcher has received a bulk LDA data export and needs to get it into a
  queryable form fast, without spending days wrangling 400K XML files and
  inconsistent JSON schemas.
license: MIT
compatibility: Requires Python 3.11+ and uv (uses polars, duckdb, lxml, orjson, tqdm).
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# lda-corpus-indexer

## What this skill does

Parses Senate LDA JSON filings, House LDA XML filings (409K+ files), and
congressional press release JSONL into a normalized DuckDB analytical store.
The output is a single `investigation.duckdb` file with 10 tables and 2 views,
covering every registrant, client, lobbyist, government entity targeted, and
press release in the corpus.

**Why it matters for journalism:** LDA data is public, quarterly, and enormous.
This skill compresses a multi-day data-wrangling job into a single command.
Every row in the output includes a `source_path` pointing back to the original
file, so any finding is auditable to its source record.

## Inputs

| Path | Format | Size |
|------|--------|------|
| `data/senate/{year}/filings/filings_{year}.json` | JSON arrays | ~2.2 GB |
| `data/house/{quarter}_XML/*.xml` | XML, one file per filing | ~5.9 GB, 409K files |
| `data/congress_press/*.jsonl` | JSONL, one record per line | ~504 MB |

Set `DATA_ROOT` env var if your data lives elsewhere (default: `data`).
If the zip extracted nested (`data/data/...`), set `DATA_ROOT=data/data`.

## Outputs

| Path | Description |
|------|-------------|
| `output/parquet/*.parquet` | Intermediate Parquet files, one per source chunk |
| `output/investigation.duckdb` | Single-file DuckDB analytical store (~2.9 GB) |

## Invocation

```bash
# Install dependencies
uv sync

# Fast validation (~2 min, one quarter per dataset)
uv run skills/lda-corpus-indexer/scripts/01_build_index.py --sample

# Full build (~2.5 hours on a typical laptop)
uv run skills/lda-corpus-indexer/scripts/01_build_index.py

# Rebuild only DuckDB from existing Parquet (skip re-parsing raw files)
uv run skills/lda-corpus-indexer/scripts/01_build_index.py --duckdb-only

# Targeted House rebuild only (after patching House parser)
uv run skills/lda-corpus-indexer/scripts/01c_rebuild_house_all.py
uv run skills/lda-corpus-indexer/scripts/01_build_index.py --duckdb-only

# Remove stale Parquet then rebuild everything
uv run skills/lda-corpus-indexer/scripts/01_build_index.py --clean
```

## Verify the build

Run the dedicated verifier — it asserts 34 invariants covering table presence,
row counts, null fractions on required columns, FK-style join integrity, and
sentinel anchor queries (the Bridenstine / Artemis Group case must be
findable).

```bash
uv run skills/lda-corpus-indexer/scripts/verify_build.py               # full build
uv run skills/lda-corpus-indexer/scripts/verify_build.py --sample      # sample build (smaller thresholds)
uv run skills/lda-corpus-indexer/scripts/verify_build.py --strict      # treat warnings as errors
```

If you want a quick manual sanity check instead:

```python
import duckdb
con = duckdb.connect("output/investigation.duckdb", read_only=True)
for t in ("press_releases", "senate_filings", "house_filings", "house_lobbyists"):
    print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:,}")
```

Expected row counts for the 2022-Q1 2026 corpus:

| Table | Expected rows |
|-------|--------------|
| press_releases | 141,332 |
| senate_filings | 418,170 |
| senate_activities | 799,192 |
| senate_lobbyists | 2,121,863 |
| senate_gov_entities | 2,016,363 |
| senate_contributions | 636,833 |
| house_filings | 409,640 |
| house_activities | ~781K |
| house_lobbyists | ~2M |

## Database schema

See `references/senate_schema.md` and `references/house_schema.md` for full
column-level documentation.

Convenience views already in the database:
- `revolving_door` — Senate lobbyists with non-empty `covered_position`, joined to filing context
- `senate_spend_by_issue` — quarterly aggregate spend by ALI issue code

## Common failure modes

1. **"Miss" on senate JSON files, Total rows: 0** — Expected if Parquet files
   already exist. The script loads from Parquet and skips re-parsing. The DuckDB
   row counts will still be correct. Only a problem if you intentionally want to
   re-parse from raw JSON.

2. **Schema inference errors on House Parquet** — House XML has all-null columns
   in some quarters. Always use `schema_overrides={col: pl.Utf8}` on House writes.
   See `references/known_quirks.md` §4.

3. **data/data/ nesting** — Some zip extractors produce `data/data/` instead of
   `data/`. Set `DATA_ROOT=data/data` if that's your layout.

4. **DuckDB type mismatch on union_by_name** — Means the first Parquet file in a
   glob has a different inferred type than later ones. Solution: explicit
   `schema_overrides` at Parquet write time (see known_quirks.md §4).

5. **Windows PowerShell f-string quoting** — PowerShell chokes on Python one-liners
   with nested f-strings. Use a `.py` file instead of `-c "..."`.

## Critical parser quirks

**Read `references/known_quirks.md` before modifying any parsing code.**

The six parser bugs discovered during development are documented there. Each one
cost at least an hour to debug. Ignoring them will break the entire Senate or House
corpus silently (e.g., all lobbyist names become None).

## Cross-dataset joins

See `references/joins.md` for how to link Senate ↔ House ↔ press releases.
The most common gotcha: House `senate_id` is a *registrant-engagement* ID
(`{registrant_id}-{engagement_id}`), not the Senate `filing_uuid`.
