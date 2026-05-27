# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**FairGuard** — entry to the Northwestern GAIN Agentic AI Investigative Journalism Challenge (deadline: July 15, 2026). The deliverable is a set of reusable Agent Skills plus a findings report demonstrating that those skills produce real journalism on a corpus of federal lobbying records and congressional press releases (2022–Q1 2026).

**Reproducibility is a hard gate.** If a judge can't re-run the skill from a clean clone, the submission caps at 1/3 on every scoring dimension.

---

## Commands

All scripts run with `uv`. Install dependencies first: `uv sync`

### ETL pipeline (Skill 1)

```bash
uv run scripts/01_build_index.py              # full build (~2.5 hr)
uv run scripts/01_build_index.py --sample     # fast validation (~2 min)
uv run scripts/01_build_index.py --duckdb-only  # rebuild DB from existing Parquet
uv run scripts/01_build_index.py --clean      # remove stale Parquet then rebuild
uv run scripts/01c_rebuild_house_all.py       # targeted House rebuild only
```

### Analysis scripts

```bash
uv run scripts/02_revolving_door_scan.py                  # broad candidate scan
uv run scripts/03_agency_concentration.py                 # Bridenstine-pattern scan
uv run scripts/03_agency_concentration.py --agency nasa   # filter to one agency
uv run scripts/03_agency_concentration.py --min-filings 5 --min-conc 0.15
```

### Database verification

```python
import duckdb
con = duckdb.connect("output/investigation.duckdb", read_only=True)
for t in ("press_releases", "senate_filings", "house_filings", "house_lobbyists"):
    print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
```

### Reporter UI (web/)

```bash
cd web && npm install && npm run dev   # http://localhost:3000
```

### Linting

```bash
uv run ruff check scripts/
uv run ruff check scripts/ --fix
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_ROOT` | `data` | Path to raw corpus root (`senate/`, `house/`, `congress_press/` are subdirs) |
| `OUTPUT_ROOT` | `output` | Path for Parquet files and DuckDB |

The raw data extracts as `data/data/` on some systems. If that happened, set `DATA_ROOT=data/data`.

---

## Architecture

### Data flow

```
Raw data (8.6 GB, gitignored in data/)
    │
    ▼
scripts/01_build_index.py        (ETL: parse → Parquet → DuckDB)
    │
    ├── output/parquet/*.parquet  (~1 GB, one file per source×quarter)
    └── output/investigation.duckdb  (2.92 GB, 10 tables + 2 views)
    │
    ▼
scripts/02_revolving_door_scan.py    → output/revolving_door_candidates.{md,csv}
scripts/03_agency_concentration.py  → output/agency_concentration.{md,csv}
                                    → notes/06_structural_pattern_findings.md
    │
    ▼
web/src/app/page.tsx             (reporter verification UI, reads findings JSON)
```

### DuckDB tables

| Table | Source | Key columns |
|-------|--------|-------------|
| `press_releases` | JSONL | `bioguide_id`, `filing_quarter`, `text` |
| `senate_filings` | JSON | `filing_uuid`, `registrant_name`, `client_name`, `income` |
| `senate_activities` | JSON | `filing_uuid`, `activity_idx`, `general_issue_code` |
| `senate_lobbyists` | JSON | `filing_uuid`, `activity_idx`, `lobbyist_name`, `covered_position` |
| `senate_gov_entities` | JSON | `filing_uuid`, `activity_idx`, `entity_name` |
| `senate_contributions` | JSON | `filing_uuid`, `amount`, `payee` |
| `house_filings` | XML | `house_id`, `senate_id`, `org_name`, `client_name` |
| `house_activities` | XML | `house_id`, `activity_idx`, `ali_code` |
| `house_lobbyists` | XML | `house_id`, `activity_idx`, `lobbyist_name`, `covered_position` |

Convenience views: `revolving_door` (senate lobbyists with non-empty `covered_position`), `senate_spend_by_issue`.

### Three Agent Skills

1. **`lda-corpus-indexer`** — ETL pipeline. Working code in `scripts/01_build_index.py`. Packaged under `skill/lda-corpus-indexer/`.
2. **`entity-resolver`** — normalizes org/person names. Designed but not yet built. Placeholder in `skill/entity-resolver/`.
3. **`revolving-door-detector`** — cross-references covered_position with gov entity targets. Working code in `scripts/03_agency_concentration.py`. Packaged under `skill/revolving-door-detector/`.

---

## Critical Parser Quirks

**Read `skill/lda-corpus-indexer/references/known_quirks.md` before touching any parsing code.**

Summary of the 7 bugs that produce silent data loss:

1. **Senate lobbyist names** nested under `lob["lobbyist"]["first_name"]` NOT at top level
2. **House lobbyist names** use `<lobbyistFirstName>` + `<lobbyistLastName>`, not `<lobbyistName>`
3. **House ALI codes** have TWO schemas: modern (`ali_info/issueAreaCode`) vs legacy (`ali_Code`) — parse both
4. **Polars schema inference** infers numeric types on all-null columns — always explicit `pl.Utf8` overrides
5. **`house_id` links to `senate_id`** at firm-engagement level, NOT filing level
6. **`senate_lobbyists` has 2.1M rows** — deduplicate on `(filing_uuid, lobbyist_name)` for counts
7. **`data/data/` nesting** — set `DATA_ROOT=data/data` if corpus extracted nested

---

## Findings

### Anchor finding (verified)

`notes/05_finding_bridenstine.md` — The Artemis Group / Jim Bridenstine revolving-door case study.

Numbers verified against corrected House data:
- 133 Senate filings, 52 targeting NASA (39.1% concentration)
- 115 House filings
- 125 House lobbyist rows naming Bridenstine

### Structural finding (Track 2, in progress)

`notes/06_structural_pattern_findings.md` — auto-generated by `scripts/03_agency_concentration.py`.
Run `uv run scripts/03_agency_concentration.py` to populate.

---

## Priority Order (remaining work as of May 27, 2026)

1. **Run `scripts/03_agency_concentration.py`** → generates Track 2 structural finding
2. **Verify top candidates from Track 2** against external sources (LinkedIn, news archives, USAspending.gov)
3. **Populate reporter UI** with findings JSON (`web/public/findings.json`)
4. **Collect remaining traces from Mokshit** → save to `traces/`
5. **Complete `findings/findings_report.md`** → export to PDF
6. **Build entity-resolver** (Skill 2) — target F1 ≥ 0.92 on 500-pair eval set

---

## Submission checklist

- [ ] `uv run scripts/01_build_index.py --sample` runs clean from scratch on a new machine
- [ ] `uv run scripts/03_agency_concentration.py` runs and produces output
- [ ] All SKILL.md files have valid YAML frontmatter + instructions
- [ ] `findings/findings_report.md` exported to PDF
- [ ] `traces/` contains logs keyed to skill invocations
- [ ] `README.md` maps all submission artifacts
- [ ] `cd web && npm run build` succeeds
- [ ] No hardcoded absolute paths in any script
- [ ] `pyproject.toml` has pinned dependency versions

---

## Codebase structure (key files)

```
skill/lda-corpus-indexer/SKILL.md          # Skill 1 — main instructions
skill/lda-corpus-indexer/references/
    known_quirks.md                         # ← most important ref file
    senate_schema.md
    house_schema.md
    joins.md
skill/revolving-door-detector/SKILL.md     # Skill 3 — methodology doc
skill/entity-resolver/SKILL.md             # Skill 2 — design doc (planned)

scripts/01_build_index.py                  # ETL (Skill 1 implementation)
scripts/02_revolving_door_scan.py          # broad revolving door scan
scripts/03_agency_concentration.py         # Skill 3 implementation (Track 2)

findings/findings_report.md               # final findings (→ PDF)
notes/05_finding_bridenstine.md           # anchor finding (verified)
notes/06_structural_pattern_findings.md   # Track 2 output (auto-generated)

web/src/app/page.tsx                      # reporter UI (Next.js)
docker-compose.yml                        # full system orchestration
```
