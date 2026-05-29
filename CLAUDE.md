# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FairGuard** — entry to the Northwestern GAIN Agentic AI Investigative Journalism Challenge (deadline: July 15, 2026). The deliverable is a set of reusable Agent Skills plus a findings report demonstrating that those skills produce real journalism on a corpus of federal lobbying records and congressional press releases (2022–Q1 2026).

**Reproducibility is a hard gate.** If a judge can't re-run the skill from a clean clone, the submission caps at 1/3 on every scoring dimension.

---

## Commands

All scripts run with `uv`. Install dependencies first: `uv sync`

### Agent skill dispatcher (Claude Code)

```
/fair-guard                         # show available modes, ask which to run
/fair-guard doctor                  # validate setup + guided onboarding (start here)
/fair-guard index                   # run ETL pipeline (lda-corpus-indexer)
/fair-guard scan                    # run Bridenstine-pattern scan (revolving-door-detector)
/fair-guard scan --agency nasa      # filter to one agency
/fair-guard resolve                 # entity resolution (planned, not yet implemented)
```

`argument-hint` shows `[mode: doctor | index | scan | resolve]` in CLI autocomplete. The dispatcher reads `skill/<full-name>/SKILL.md` at runtime and executes its instructions. `allowed-tools: Read Bash` is pre-approved — no permission prompts during execution.

**Prerequisite guard (enforced by dispatcher):** `scan` and `resolve` require `output/investigation.duckdb`. If it doesn't exist, the dispatcher stops and shows two recovery options before attempting anything.

**Two ways to get `output/investigation.duckdb`:**
- **Fast (~10 min):** Download pre-built `output/` from Google Drive → unzip → place at project root:
  https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing
- **Full build (~2.5 hr):** Run `/fair-guard index` after placing raw corpus in `data/`

### ETL pipeline (Skill: index)

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
cd web && npm ci && npm run dev   # http://localhost:3000
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

### Four Agent Skills

| Short name | Full name | Status | Implementation |
|-----------|-----------|--------|---------------|
| `doctor` | setup-validator | Working | Agent instructions in `skill/doctor/SKILL.md` |
| `index` | lda-corpus-indexer | Working | `scripts/01_build_index.py` + `skill/lda-corpus-indexer/` |
| `resolve` | entity-resolver | Planned | Design doc in `skill/entity-resolver/SKILL.md` |
| `scan` | revolving-door-detector | Working | `scripts/03_agency_concentration.py` + `skill/revolving-door-detector/` |

### Agent Skills architecture (three layers)

Skills exist at three levels simultaneously — each serves a different audience:

| Layer | Path | Standard | Who uses it |
|-------|------|----------|-------------|
| Standalone submission artifacts | `skill/<full-name>/` | agentskills.io (original) | Challenge judges, direct skill users |
| Canonical agent store with modes | `.agents/skills/fair-guard/` | agentskills.io (modes architecture) | Other agents (Codex, Gemini, Qwen) |
| Claude Code dispatcher | `.claude/skills/fair-guard/` | Claude Code extensions | Claude Code CLI (`/fair-guard`) |

**Do not put Claude Code-specific fields** (`$ARGUMENTS`, `argument-hint`, `context: fork`, `disable-model-invocation`) into `skill/` files — those are the portable, submission-facing artifacts. Keep those extensions in `.claude/skills/` only.

The `.agents/skills/fair-guard/modes/` copies have cleaned-up frontmatter (non-standard fields like `version`, `author`, `tools` moved under `metadata:` and `compatibility:` per the agentskills.io spec). The originals in `skill/` are untouched.

The dispatcher routes `$ARGUMENTS` short names to `skill/<full-name>/SKILL.md` at runtime. It enforces prerequisites deterministically (DuckDB check for `scan`/`resolve`, data dir check for `index`) before reading any mode file.

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

## Priority Order (remaining work as of May 29, 2026)

1. **Run `scripts/03_agency_concentration.py`** → generates Track 2 structural finding
2. **Verify top candidates from Track 2** against external sources (LinkedIn, news archives, USAspending.gov)
3. **Populate reporter UI** with findings JSON (`web/public/findings.json`)
4. **Collect remaining traces from Mokshit** → save to `traces/`
5. **Complete `findings/findings_report.md`** → export to PDF
6. **Test `/fair-guard doctor`** across Linux, macOS, Windows — see `notes/HANDOFF_TO_MOKSHIT_SKILL_DOCTOR.md`
7. **Build entity-resolver** (Skill: `resolve`) — target F1 ≥ 0.92 on 500-pair eval set

---

## Submission checklist

- [ ] `uv run scripts/01_build_index.py --sample` runs clean from scratch on a new machine
- [ ] `uv run scripts/03_agency_concentration.py` runs and produces output
- [ ] All SKILL.md files have valid YAML frontmatter + instructions
- [ ] `/fair-guard doctor` runs without errors and prints a correct checklist
- [ ] `/fair-guard scan` routes correctly and executes without permission prompts
- [ ] `findings/findings_report.md` exported to PDF
- [ ] `traces/` contains logs keyed to skill invocations
- [ ] `README.md` maps all submission artifacts
- [ ] `cd web && npm ci && npm run build` succeeds
- [ ] No hardcoded absolute paths in any script
- [ ] `pyproject.toml` has pinned dependency versions

---

## Codebase structure (key files)

```
skill/doctor/SKILL.md                      # Skill: doctor — setup validator
skill/lda-corpus-indexer/SKILL.md          # Skill: index — submission artifact
skill/lda-corpus-indexer/references/
    known_quirks.md                         # ← most important ref file
    senate_schema.md
    house_schema.md
    joins.md
skill/revolving-door-detector/SKILL.md     # Skill: scan — submission artifact
skill/entity-resolver/SKILL.md             # Skill: resolve — design doc (planned)

.agents/skills/fair-guard/SKILL.md         # agentskills.io master skill
.agents/skills/fair-guard/modes/
    doctor/SKILL.md                        # agentskills.io compliant copies
    index/SKILL.md                         # (short names; originals in skill/ unchanged)
    resolve/SKILL.md
    scan/SKILL.md

.claude/skills/fair-guard/SKILL.md         # Claude Code dispatcher (/fair-guard)

scripts/01_build_index.py                  # ETL (Skill: index implementation)
scripts/02_revolving_door_scan.py          # broad revolving door scan
scripts/03_agency_concentration.py         # Skill: scan implementation (Track 2)

findings/findings_report.md               # final findings (→ PDF)
notes/05_finding_bridenstine.md           # anchor finding (verified)
notes/06_structural_pattern_findings.md   # Track 2 output (auto-generated)
notes/HANDOFF_TO_MOKSHIT_SKILL_DOCTOR.md  # doctor skill spec + testing tasks for Mokshit

web/src/app/page.tsx                      # reporter UI — server component
web/src/app/FindingsClient.tsx            # reporter UI — interactive client
web/src/app/types.ts                      # shared TypeScript interfaces
docker-compose.yml                        # full system orchestration
```
