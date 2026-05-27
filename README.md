# FairGuard — Northwestern Agentic AI Investigative Journalism Challenge

**Team:** FairGuard
**Members:** Mokshit Surana (agent orchestration & investigation logic) · Archit Rathod (data pipelines, reporter-facing tooling)
**Competition:** [Northwestern GAIN Agentic AI Investigative Journalism Challenge](https://www.gain-agent-challenge.northwestern.edu/details/)
**Deadline:** July 15, 2026
**License:** MIT (Agent Skills; code is open-source as required by competition rules)

---

## What this is

A set of reusable Agent Skills for investigative journalism, plus the findings they produced on a corpus of 1M+ federal lobbying records and congressional press releases (2022–Q1 2026). Built for the Northwestern GAIN challenge using Claude Code.

The anchor finding: **The Artemis Group** — a lobbying firm founded by former NASA Administrator Jim Bridenstine that directs 39% of its filings at NASA, staffed by four former Bridenstine officials. The structural finding: a ranked list of comparable revolving-door patterns across 23 federal agencies.

---

## Submission map

| Artifact | Location | Status |
|----------|----------|--------|
| Agent Skill 1 — `lda-corpus-indexer` | `skill/lda-corpus-indexer/` | ✅ Complete |
| Agent Skill 2 — `entity-resolver` | `skill/entity-resolver/` | 🚧 Planned |
| Agent Skill 3 — `revolving-door-detector` | `skill/revolving-door-detector/` | ✅ Complete |
| Findings report (PDF) | `findings/findings_report.md` → PDF | 🚧 In progress |
| Interaction traces | `traces/` | 🚧 Collecting |
| Anchor finding | `notes/05_finding_bridenstine.md` | ✅ Draft complete |
| Structural finding | `notes/06_structural_pattern_findings.md` | ✅ Draft complete |

---

## Repository structure

```
.
├── README.md                              # this file — submission map
├── CLAUDE.md                              # Claude Code project instructions
├── pyproject.toml                         # Python dependencies (uv)
├── uv.lock
├── Dockerfile                             # ETL pipeline image
├── docker-compose.yml                     # Full system orchestration
├── docker-entrypoint.sh
│
├── skill/                                 # ── Agent Skills (primary submission artifacts)
│   ├── lda-corpus-indexer/               #   Skill 1: ETL pipeline
│   │   ├── SKILL.md                      #     instructions + invocation guide
│   │   ├── references/
│   │   │   ├── known_quirks.md           #     ← most valuable: 7 hard-won parser bugs
│   │   │   ├── senate_schema.md          #     Senate LDA column reference
│   │   │   ├── house_schema.md           #     House XML structure reference
│   │   │   └── joins.md                  #     cross-dataset join patterns
│   │   └── assets/
│   │       └── example_query.sql         #     ready-to-run DuckDB queries
│   ├── entity-resolver/                   #   Skill 2: name normalization (planned)
│   │   └── SKILL.md
│   └── revolving-door-detector/           #   Skill 3: agency concentration scan
│       └── SKILL.md
│
├── scripts/                               # ── Pipeline scripts
│   ├── 01_build_index.py                 #   ETL: raw → Parquet → DuckDB
│   ├── 01b_rebuild_house_lobbyists.py    #   targeted House lobbyist rebuild
│   ├── 01c_rebuild_house_all.py          #   targeted full House rebuild
│   ├── 02_revolving_door_scan.py         #   broad revolving-door candidate scan
│   └── 03_agency_concentration.py        #   Bridenstine-pattern concentration analysis
│
├── notebooks/                             # ── Exploratory notebooks (verification runs)
│   ├── 04_revolving_door_leads.ipynb
│   ├── 05_bridenstine_verification.ipynb
│   └── 05d_house_crossval.ipynb
│
├── notes/                                 # ── Working findings (markdown)
│   ├── 03_skill_packaging_plan.md
│   ├── 04_finding_draft_chamberlin.md
│   ├── 05_finding_bridenstine.md         #   ← THE ANCHOR FINDING (verified)
│   ├── 06_structural_pattern_findings.md #   Track 2 output (auto-generated)
│   └── HANDOFF_TO_ARCHIT.md
│
├── findings/                              # ── Final findings report
│   └── findings_report.md               #   → will become PDF for submission
│
├── traces/                                # ── Interaction traces (required by competition)
│   ├── trace_01_setup_and_data_exploration.md
│   └── trace_02_parser_debugging.md
│
└── web/                                   # ── Reporter verification UI (Next.js)
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    └── src/app/
        ├── layout.tsx
        └── page.tsx                       #   provenance display for findings
```

**Gitignored:** `data/` (8.6 GB corpus), `output/` (2.92 GB DuckDB), `web/node_modules/`, `web/.next/`, `.venv/`.

---

## Quick start

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- Python 3.11+ (installed automatically by `uv sync`)
- The corpus data (download link in registration email; extract to `data/`)

### 1. Install dependencies

```bash
uv sync
```

### 2. Build the DuckDB analytical store

```bash
# Fast validation (~2 min, one quarter per dataset)
uv run scripts/01_build_index.py --sample

# Full build (~2.5 hours on a typical laptop)
uv run scripts/01_build_index.py
```

### 3. Verify the build

```python
import duckdb
con = duckdb.connect("output/investigation.duckdb", read_only=True)
for t in ("press_releases", "senate_filings", "house_filings", "house_lobbyists"):
    print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
```

Expected: `press_releases 141332`, `senate_filings 418170`, `house_filings 409640`.

### 4. Run the revolving-door scan (broad)

```bash
uv run scripts/02_revolving_door_scan.py
# Output: output/revolving_door_candidates.md
```

### 5. Run the agency concentration scan (Track 2 — the main finding)

```bash
uv run scripts/03_agency_concentration.py
# Outputs: output/agency_concentration.{csv,md}
#          notes/06_structural_pattern_findings.md

# Filter to a single agency:
uv run scripts/03_agency_concentration.py --agency nasa
```

### 6. Start the reporter verification UI (optional)

```bash
cd web
npm install
npm run dev
# Open http://localhost:3000
```

### With Docker

```bash
# ETL pipeline only
docker compose run --rm etl

# Sample mode (fast)
SAMPLE=1 docker compose run --rm etl

# Full stack (ETL + web UI)
docker compose up
```

---

## The corpus

| Source | Format | Size | Records |
|--------|--------|------|---------|
| Senate LDA filings | JSON | ~2.2 GB | 418,170 |
| House LDA filings | XML (one file/filing) | ~5.9 GB | 409,640 |
| Congressional press releases | JSONL | ~504 MB | 141,332 |

**Data layout:** `data/data/congress_press/`, `data/data/senate/`, `data/data/house/`
(nested due to zip extraction; set `DATA_ROOT=data/data` if needed).

---

## Agent Skills

### Skill 1 — `lda-corpus-indexer`

Converts raw federal LDA dumps into a queryable DuckDB analytical store with
per-row provenance. Any journalist receiving a fresh bulk LDA export can run
this and have a queryable database in ~2.5 hours instead of days.

See `skill/lda-corpus-indexer/SKILL.md`.

### Skill 2 — `entity-resolver` *(planned)*

Normalizes messy organization/person names across LDA records (e.g., "MICROSOFT
CORP" vs "Microsoft Corporation"). Corpus-agnostic — works on any government
dataset with this problem.

See `skill/entity-resolver/SKILL.md`.

### Skill 3 — `revolving-door-detector`

Identifies former senior agency officials lobbying their former agency, ranked
by concentration × volume × seniority. The Bridenstine-pattern detector.

See `skill/revolving-door-detector/SKILL.md`.

---

## Findings

### Finding 1 — The Artemis Group (anchor case study)

**Status:** Draft complete, verified against Senate and House LDA.

In Q4 2024, former NASA Administrator Jim Bridenstine launched The Artemis Group,
a lobbying firm that directs 39.1% of its filings at NASA — the highest
concentration of any third-party firm with significant volume in the corpus.
Five of the twelve most active NASA-targeting lobbyists in the 2024-2026
Senate corpus work at this firm. Four worked directly under Bridenstine.

Full writeup: `notes/05_finding_bridenstine.md`

### Finding 2 — Structural Pattern (Track 2)

**Status:** Draft complete. 106 candidates identified across 18 agencies.

Ranks all Bridenstine-pattern cases across 23 federal agencies. Extends the
Artemis Group case study from one instance to a systemic analysis. Top cases:
Benjamin Steinberg (DOE, 90.2%), Jim Newsome (CFTC, 96.0%), Kate Marks (DOE, 91.3%).

Output: `notes/06_structural_pattern_findings.md` (auto-generated)
Reporter UI: `web/` — run `cd web && npm install && npm run dev` → http://localhost:3000

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_ROOT` | `data` | Path containing `senate/`, `house/`, `congress_press/` |
| `OUTPUT_ROOT` | `output` | Path for Parquet files and DuckDB |

---

## Known issues and design decisions

See `skill/lda-corpus-indexer/references/known_quirks.md` for the full list
of parser bugs discovered during development. Key ones:

- Senate JSON: lobbyist names nested under `lob["lobbyist"]["first_name"]`
- House XML: two ALI schemas (modern nested vs. legacy flat)
- Polars schema inference: explicit `pl.Utf8` overrides required on House writes
- `senate_lobbyists` has 2.1M rows — deduplicate on `(filing_uuid, lobbyist_name)`

---

## Contact

- Mokshit Surana — mokshitsurana3110@gmail.com
- Archit Rathod — architrathod77@gmail.com
