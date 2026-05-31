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
/fair-guard resolve                 # build entity_map (F1 = 0.963)
/fair-guard scan                    # run Bridenstine-pattern scan (revolving-door-detector)
/fair-guard scan --agency nasa      # filter to one agency
```

`argument-hint` shows `[mode: doctor | index | scan | resolve]` in CLI autocomplete. The dispatcher reads `skill/<full-name>/SKILL.md` at runtime and executes its instructions. `allowed-tools: Read Bash` is pre-approved — no permission prompts during execution.

**Prerequisite guard (enforced by dispatcher):** `scan` and `resolve` require `output/investigation.duckdb`. If it doesn't exist, the dispatcher stops and shows two recovery options before attempting anything.

**Two ways to get `output/investigation.duckdb`:**
- **Fast (~10 min):** Download pre-built `output/` from Google Drive → unzip → place at project root:
  https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing
- **Full build (~2.5 hr):** Run `/fair-guard index` after placing raw corpus in `data/`

### Skill scripts (called by the dispatcher; also runnable directly)

```bash
# doctor — cross-platform setup validator
uv run scripts/doctor.py
uv run scripts/doctor.py --json              # machine-readable
uv run scripts/doctor.py --quiet             # hide passes

# index — ETL pipeline (raw LDA dumps → DuckDB)
uv run scripts/01_build_index.py             # full build (~2.5 hr)
uv run scripts/01_build_index.py --sample    # fast validation (~2 min)
uv run scripts/01_build_index.py --duckdb-only   # rebuild DB from existing Parquet
uv run scripts/01_build_index.py --clean         # remove stale Parquet then rebuild
uv run scripts/01c_rebuild_house_all.py          # targeted House rebuild only

# verify — post-build invariants (34 checks; run after every index build)
uv run scripts/verify_build.py
uv run scripts/verify_build.py --sample      # smaller thresholds for sample builds
uv run scripts/verify_build.py --strict      # warnings become errors

# resolve — entity resolution; writes entity_map table to investigation.duckdb
uv run scripts/02_entity_resolver.py
uv run scripts/02_entity_resolver.py --orgs-only
uv run scripts/02_entity_resolver.py --limit 5000 --dry-run

# scan — Bridenstine-pattern agency concentration analysis
uv run scripts/03_agency_concentration.py
uv run scripts/03_agency_concentration.py --agency nasa
uv run scripts/03_agency_concentration.py --min-filings 5 --min-conc 0.15
```

### Tests

```bash
uv run pytest                                            # full suite (144 tests)
uv run pytest tests/test_agency_registry.py -v           # scan regex coverage (111 tests)
uv run pytest tests/test_entity_resolver.py -v           # resolver unit + F1 (33 tests)
uv run pytest tests/test_entity_resolver.py::test_f1_on_db -s   # show F1 eval output
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
    └── output/investigation.duckdb  (≈3 GB, 11 tables + 2 views once resolve has run)
    │
    ▼
scripts/verify_build.py          (post-build invariants: 34 checks)
    │
    ▼
scripts/02_entity_resolver.py    → writes entity_map table into investigation.duckdb
scripts/03_agency_concentration.py → output/agency_concentration.{md,csv}
                                   → notes/06_structural_pattern_findings.md
                                   → web/public/findings.json
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

| Short name | Full name | Status | Implementation | Tests |
|-----------|-----------|--------|---------------|-------|
| `doctor` | setup-validator | Shipped | `scripts/doctor.py` + `skill/doctor/` | manual cross-platform; clean run on Windows |
| `index` | lda-corpus-indexer | Shipped | `scripts/01_build_index.py` + `skill/lda-corpus-indexer/` | `scripts/verify_build.py` — 34 invariants |
| `resolve` | entity-resolver | Shipped | `scripts/02_entity_resolver.py` + `skill/entity-resolver/` | `tests/test_entity_resolver.py` — 33 tests, F1 = 0.963 |
| `scan` | revolving-door-detector | Shipped | `scripts/03_agency_concentration.py` + `skill/revolving-door-detector/` | `tests/test_agency_registry.py` — 111 tests |

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

## Priority Order (remaining work as of May 30, 2026)

All four skills now ship with tests. Remaining work for submission:

1. **Verify top candidates from `scan`** against external sources (LinkedIn, news archives, USAspending.gov)
2. **Cross-platform run of `doctor`** — confirmed on Windows; need macOS + Linux smoke test
3. **Complete `findings/findings_report.md`** → export to PDF
4. **Generate per-skill traces** (one each for doctor, index, resolve, scan) → already done as `traces/trace_skill_*.md`
5. **Update `README.md` submission map** to reflect shipped resolve and the test suite

---

## Submission checklist

- [x] `uv run scripts/01_build_index.py --sample` runs clean from scratch on a new machine (note: validated against `scripts/verify_build.py --sample`)
- [x] `uv run scripts/03_agency_concentration.py` runs and produces output (139 candidates, 22 agencies)
- [x] `uv run scripts/02_entity_resolver.py` runs and writes entity_map (F1 = 0.963)
- [x] `uv run scripts/verify_build.py` runs and all 34 invariants pass
- [x] `uv run pytest` — 144 tests passing (111 registry + 33 resolver)
- [x] All SKILL.md files have valid YAML frontmatter + instructions
- [x] `/fair-guard doctor` runs without errors and prints a correct checklist (Windows-verified)
- [x] `/fair-guard scan` routes correctly and executes without permission prompts
- [ ] `findings/findings_report.md` exported to PDF
- [x] `traces/` contains logs keyed to skill invocations
- [ ] `README.md` maps all submission artifacts (needs refresh)
- [x] `cd web && npm ci && npm run build` succeeds
- [x] No hardcoded absolute paths in any script
- [x] `pyproject.toml` has pinned dependency versions

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
skill/entity-resolver/SKILL.md             # Skill: resolve — shipped, F1 = 0.963

.agents/skills/fair-guard/SKILL.md         # agentskills.io master skill
.agents/skills/fair-guard/modes/
    doctor/SKILL.md                        # agentskills.io compliant copies
    index/SKILL.md                         # (short names; originals in skill/ unchanged)
    resolve/SKILL.md
    scan/SKILL.md

.claude/skills/fair-guard/SKILL.md         # Claude Code dispatcher (/fair-guard)

scripts/doctor.py                          # Skill: doctor implementation (cross-platform)
scripts/01_build_index.py                  # Skill: index implementation (ETL)
scripts/02_entity_resolver.py              # Skill: resolve implementation
scripts/03_agency_concentration.py         # Skill: scan implementation
scripts/verify_build.py                    # post-index invariants (34 checks)
scripts/_archive/                          # superseded scripts kept for history
scripts/_diagnose_*.py                     # one-shot data-quality probes

tests/test_agency_registry.py              # 111 tests for scan registry
tests/test_entity_resolver.py              # 33 tests for resolver (incl. F1 eval)

findings/findings_report.md               # final findings (→ PDF)
notes/05_finding_bridenstine.md           # anchor finding (verified)
notes/06_structural_pattern_findings.md   # Track 2 output (auto-generated)
notes/HANDOFF_TO_MOKSHIT_SKILL_DOCTOR.md  # doctor skill spec + testing tasks for Mokshit

web/src/app/page.tsx                      # reporter UI — server component
web/src/app/FindingsClient.tsx            # reporter UI — interactive client
web/src/app/types.ts                      # shared TypeScript interfaces
docker-compose.yml                        # full system orchestration
```
