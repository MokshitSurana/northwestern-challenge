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

### Demo

A walkthrough of the reporter UI — landing, findings, money trails, the
conflict-of-interest graph, and the request-for-comment tracker.

https://github.com/MokshitSurana/northwestern-challenge/raw/master/demo/FairGuard-demo.mp4

If your client doesn't auto-play the embed, the file is at
[`demo/FairGuard-demo.mp4`](demo/FairGuard-demo.mp4).

---

## For journalists — three ways in

Three paths, ordered fastest → most powerful. You only need the first one to read every finding the project has produced.

### Path A — Just browse the findings (≈ 3 minutes, only needs Node.js)

Everything a reporter needs to *read* — the 139 ranked candidates, the $1.24B money trail, the press-release cross-references, the conflict-of-interest graph, the request-for-comment status — is already baked into JSON files committed to this repo. You don't need Python, DuckDB, or the 8.6 GB corpus to look at any of it.

1. Install [Node.js 20+](https://nodejs.org/) (Mac / Windows installers; on Linux: `sudo apt install nodejs npm` or use `nvm`).
2. Open a terminal and run:
   ```bash
   git clone https://github.com/MokshitSurana/northwestern-challenge.git
   cd northwestern-challenge/web
   npm install
   npm run dev
   ```
3. Open **<http://localhost:3000>** in your browser.

Then start at the **landing page** (`/`), or skip straight to:
- `/findings` — the 139 ranked candidates, filterable by agency
- `/findings/[id]` — click any candidate to open a single-screen "four gates" view
- `/search` — type a name (lobbyist, firm, client, agency, legislator)
- `/methods` — pipeline diagram + what each step claims
- `/glossary` — plain-English definitions (§207, LDA, ALI code, discretionary)

### Path B — Pre-built DuckDB (≈ 30 minutes, lets you run new queries / new scans)

If you want to run your own queries or kick off a fresh scan against a different agency, download the pre-built database instead of rebuilding from raw filings:

1. Do Path A first (the web UI is the front door for most workflows).
2. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — one-line installer on every OS.
3. Download `output.zip` (≈ 3 GB DuckDB) from the team Drive:
   <https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf>
4. Unzip so the file lives at `output/investigation.duckdb`.
5. From the repo root: `uv sync` (one-time Python install).
6. Run any of the skills below.

### Path C — Full rebuild from raw LDA dumps (≈ 2.5 hours, fully reproducible)

For judges and engineers verifying that nothing is hand-curated:

1. Do Path B steps 1–5, *but* skip the Drive download — instead place the raw LDA dump at `data/` (download link in the GAIN registration email).
2. `uv run scripts/01_build_index.py`  → builds `output/investigation.duckdb` from scratch.
3. `uv run scripts/verify_build.py` → 34 post-build invariants must all pass.

This is the path CI runs on every push (cross-platform: Linux, macOS, Windows — see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

---

## How to run a skill — `/fair-guard <mode>` vs. `scripts/`

The nine FairGuard skills (`doctor`, `index`, `resolve`, `scan`, `trace`, `pressrel`, `coi`, `comment`, `archive`) can be invoked **two ways**, depending on whether you have an agent CLI available:

### With an agent CLI (recommended — Claude Code, Codex, Gemini CLI, etc.)

The `/fair-guard` dispatcher reads `skill/<full-name>/SKILL.md` at runtime and runs the right script with prerequisite checks. Inside the Claude Code CLI:

```
/fair-guard                  # dispatcher menu
/fair-guard doctor           # validate setup
/fair-guard scan             # rank candidates
/fair-guard scan --agency nasa
/fair-guard trace            # follow the money
/fair-guard pressrel         # cross-ref press releases
/fair-guard coi              # build the conflict-of-interest graph
/fair-guard comment          # request-for-comment workflow
/fair-guard archive          # snapshot cited URLs
```

The dispatcher guards prerequisites — e.g. `scan` and `resolve` refuse to run without `output/investigation.duckdb` and tell you exactly how to get it.

### Without an agent CLI — call the scripts directly

If you don't have Claude Code (or any other agent CLI), every skill ships an underlying script you can run by hand. The CLI flags match the skill's options:

| Skill | Direct script |
|-------|---------------|
| `doctor` | `uv run scripts/doctor.py` |
| `index` | `uv run scripts/01_build_index.py` (`--sample` for fast validation) |
| `resolve` | `uv run scripts/02_entity_resolver.py` |
| `scan` | `uv run scripts/03_agency_concentration.py [--agency nasa]` |
| `trace` | `uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json` |
| `pressrel` | `uv run scripts/05_pressrel_search.py --enrich-findings` |
| `coi` | `uv run scripts/06_coi_graph.py` |
| `comment` | `uv run scripts/07_comment_tracker.py list` |
| `archive` | `uv run scripts/08_archive_cite.py` |

The agent-mediated and direct-script paths produce **identical artifacts** — the dispatcher is a routing layer, not a code path of its own. Pick whichever you have at hand.

---

## Submission map

| Artifact | Location | Status |
|----------|----------|--------|
| Agent Skill 1 — `doctor` (setup-validator) | `skill/doctor/` | ✅ Shipped (cross-platform Python) |
| Agent Skill 2 — `lda-corpus-indexer` (`index`) | `skill/lda-corpus-indexer/` | ✅ Shipped (`scripts/verify_build.py` — 34 invariants pass) |
| Agent Skill 3 — `entity-resolver` (`resolve`) | `skill/entity-resolver/` | ✅ Shipped (F1 = 0.963 on held-out eval) |
| Agent Skill 4 — `revolving-door-detector` (`scan`) | `skill/revolving-door-detector/` | ✅ Shipped (139 candidates, 22 agencies) |
| Agent Skill 5 — `federal-award-tracer` (`trace`) | `skill/federal-award-tracer/` | ✅ Shipped (USAspending money trail; 3 reproducible case files) |
| Agent Skill 6 — `press-release-cross-ref` (`pressrel`) | `skill/press-release-cross-ref/` | ✅ Shipped (Congressional press-release cross-ref over 141K rows; 3 reproducible case files) |
| Agent Skill 7 — `coi-graph` (`coi`) | `skill/coi-graph/` | ✅ Shipped (composes scan + trace + pressrel into a force-directed conflict-of-interest graph; surfaces triangles, hubs, bridges; renders to JSON + SVG + DOT + interactive `/graph` route) |
| Agent Skill 8 — `comment-tracker` (`comment`) | `skill/comment-tracker/` | ✅ Shipped (turns the per-firm comment-request drafts into an auditable status system; six event kinds, ten derived statuses with deadline pressure rules; CLI + `/comments` UI route) |
| Agent Skill 9 — `archive-on-cite` (`archive`) | `skill/archive-on-cite/` | ✅ Shipped (snapshots every cited URL to Wayback + Archive.today with retry/backoff; output/archive_registry.json + UI mirror) |
| Test suite (pytest) | `tests/` | ✅ 261 tests passing |
| Findings report (PDF) | `findings/findings_report.md` → PDF | ✅ Builds via pandoc + typst (see report header) |
| Interaction traces | `traces/` | ✅ 4 per-skill traces + 2 narrative traces |
| Anchor finding | `notes/05_finding_bridenstine.md` | ✅ Draft complete |
| Structural finding | `notes/06_structural_pattern_findings.md` | ✅ Auto-generated by `scan` |
| External verification + money trail | `notes/08_external_verification_top_candidates.md` | ✅ 8/10 roles confirmed; USAspending awards traced |

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
│   ├── doctor/                            #   Skill: doctor — setup validator
│   │   └── SKILL.md
│   ├── lda-corpus-indexer/               #   Skill: index — ETL pipeline
│   │   ├── SKILL.md                      #     instructions + invocation guide
│   │   ├── references/
│   │   │   ├── known_quirks.md           #     ← most valuable: 7 hard-won parser bugs
│   │   │   ├── senate_schema.md          #     Senate LDA column reference
│   │   │   ├── house_schema.md           #     House XML structure reference
│   │   │   └── joins.md                  #     cross-dataset join patterns
│   │   └── assets/
│   │       └── example_query.sql         #     ready-to-run DuckDB queries
│   ├── entity-resolver/                   #   Skill: resolve — name normalization (F1 0.963)
│   │   └── SKILL.md
│   ├── revolving-door-detector/           #   Skill: scan — agency concentration scan
│   │   └── SKILL.md
│   └── federal-award-tracer/              #   Skill: trace — USAspending money trail
│       ├── SKILL.md
│       └── cases/                         #     3 reproducible case files
│
├── scripts/                               # ── Pipeline scripts
│   ├── doctor.py                         #   Skill: doctor implementation (cross-platform)
│   ├── 01_build_index.py                 #   Skill: index implementation (ETL)
│   ├── 01b_rebuild_house_lobbyists.py    #   targeted House lobbyist rebuild
│   ├── 01c_rebuild_house_all.py          #   targeted full House rebuild
│   ├── 02_entity_resolver.py             #   Skill: resolve implementation
│   ├── 03_agency_concentration.py        #   Skill: scan implementation
│   ├── 04_award_tracer.py                #   Skill: trace implementation (USAspending)
│   ├── verify_build.py                   #   post-index invariants (34 checks)
│   ├── _probe_usaspending.py             #   original money-trail probe (trace's ancestor)
│   ├── _archive/                         #   superseded scripts (see _archive/README.md)
│   └── _diagnose_*.py                    #   one-shot data-quality probes
│
├── tests/                                 # ── pytest suite (261 tests)
│   ├── test_agency_registry.py           #   scan registry + regex coverage (111 tests)
│   ├── test_entity_resolver.py           #   resolver unit + F1 eval (33 tests)
│   ├── test_pressrel.py                  #   pressrel regex + snippet + DB integration (30 tests)
│   ├── test_coi_graph.py                 #   coi canonicalization + patterns + renderers (26 tests)
│   ├── test_comment_tracker.py           #   comment-tracker schema + status + CLI (25 tests)
│   ├── test_archive_cite.py              #   archive URL collection + registry (14 tests)
│   └── test_ap_style_lint.py             #   AP-style rules + false-positive controls (22 tests)
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
│   ├── 06_structural_pattern_findings.md #   Track 2 output (auto-generated by scan)
│   ├── 07_skills_brainstorm.md           #   forward-looking ideas / v2 roadmap
│   ├── 08_external_verification_top_candidates.md #   external verification + USAspending money trail
│   └── HANDOFF_TO_ARCHIT.md
│
├── findings/                              # ── Final findings report
│   └── findings_report.md               #   → will become PDF for submission
│
├── traces/                                # ── Interaction traces (required by competition)
│   ├── trace_01_setup_and_data_exploration.md
│   ├── trace_02_parser_debugging.md
│   ├── trace_skill_doctor.md             #   per-skill keyed traces
│   ├── trace_skill_index.md
│   ├── trace_skill_resolve.md
│   └── trace_skill_scan.md
│
└── web/                                   # ── Reporter verification UI (Next.js — 11 routes)
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    └── src/app/
        ├── layout.tsx
        ├── NavTabs.tsx                    #   nav (10 entries: Home, Findings, Search, …)
        ├── types.ts                       #   shared TypeScript interfaces
        ├── lib/exports.ts                 #   CSV/Markdown export helpers + findingSlug()
        ├── page.tsx                       #   /          — landing (hero, stats, tiles, top-3)
        ├── findings/page.tsx              #   /findings  — ranked candidate list (was / pre-2026-06-08)
        ├── findings/[id]/page.tsx         #   /findings/[id] — four-gate permalink (SSG one per candidate)
        ├── findings/[id]/DetailButtons.tsx
        ├── FindingsClient.tsx             #   interactive findings list (used by /findings)
        ├── search/page.tsx                #   /search    — name-first inverse lookup (server)
        ├── search/SearchClient.tsx        #   search filter + URL sync + type chips
        ├── trails/page.tsx                #   /trails    — money-trail index
        ├── pressrel/page.tsx              #   /pressrel  — press-release report index
        ├── graph/page.tsx                 #   /graph     — interactive D3 force-directed CoI graph
        ├── comments/page.tsx              #   /comments  — request-for-comment status table
        ├── methods/page.tsx               #   /methods   — pipeline diagram, four gates, skill walkthrough
        └── glossary/page.tsx              #   /glossary  — plain-English term reference (LDA, §207, ALI, …)
```

**Gitignored:** `data/` (8.6 GB corpus), `output/` (2.92 GB DuckDB), `web/node_modules/`, `web/.next/`, `.venv/`.

---

## Full engineering quickstart (verification / reproducibility)

This section is the **detailed step-by-step** behind Path C above (and the dependencies needed if you arrived from Path B). For the journalist-friendly entry points, see [For journalists — three ways in](#for-journalists--three-ways-in) at the top of this file.

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

### 4. Verify the build (34 post-build invariants)

```bash
uv run scripts/verify_build.py
uv run scripts/verify_build.py --sample   # smaller thresholds for sample builds
```

### 5. Resolve entity names (F1 = 0.963)

```bash
uv run scripts/02_entity_resolver.py
# Writes the `entity_map` table into output/investigation.duckdb
```

### 6. Run the agency concentration scan (Track 2 — the main finding)

```bash
uv run scripts/03_agency_concentration.py
# Outputs: output/agency_concentration.{csv,md}
#          notes/06_structural_pattern_findings.md
#          web/public/findings.json (auto-refreshes the reporter UI)

# Filter to a single agency:
uv run scripts/03_agency_concentration.py --agency nasa
```

### 7. Run the test suite (261 tests)

```bash
uv run pytest
uv run pytest tests/test_agency_registry.py -v    # scan regex coverage
uv run pytest tests/test_entity_resolver.py -v    # resolver F1 eval
uv run pytest tests/test_pressrel.py -v           # pressrel regex + DB integration
uv run pytest tests/test_coi_graph.py -v          # coi canonicalization + patterns
uv run pytest tests/test_comment_tracker.py -v    # comment-tracker schema + status
uv run pytest tests/test_archive_cite.py -v       # archive URL collection + registry
uv run pytest tests/test_ap_style_lint.py -v      # AP-style rules
```

### 8. Start the reporter verification UI (optional)

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

All nine skills are shipped. The `/fair-guard` dispatcher routes between them
and enforces prerequisites deterministically before reading any mode file.
A tenth tool (`scripts/09_ap_style_lint.py`) provides AP-style markdown
linting for the findings report and notes; it runs directly without going
through the dispatcher and has 22 unit tests covering each rule plus
false-positive controls.

### Skill 1 — `doctor` (setup-validator)

Cross-platform setup validator. Checks Python, uv, Node, npm, the Python and
web environments, raw-data presence, and the existence of the pre-built DuckDB.
Prints a pass/fail checklist and offers to launch the index build on a clean pass.

Implementation: `scripts/doctor.py` (Python; Linux, macOS, Windows).
See `skill/doctor/SKILL.md`.

### Skill 2 — `lda-corpus-indexer` (`index`)

Converts raw federal LDA dumps into a queryable DuckDB analytical store with
per-row provenance. Any journalist receiving a fresh bulk LDA export can run
this and have a queryable database in ~2.5 hours instead of days.

Implementation: `scripts/01_build_index.py` (ETL) + `scripts/verify_build.py`
(34 post-build invariants).
See `skill/lda-corpus-indexer/SKILL.md`.

### Skill 3 — `entity-resolver` (`resolve`)

Normalizes and clusters messy organization/person names across LDA records
(e.g., "MICROSOFT CORP" vs "Microsoft Corporation") so cross-record joins and
counts can be done reliably. Held-out F1 = 0.963 on labeled positives harvested
from `registrant_id` collisions.

Implementation: `scripts/02_entity_resolver.py` + `tests/test_entity_resolver.py`.
See `skill/entity-resolver/SKILL.md`.

### Skill 4 — `revolving-door-detector` (`scan`)

Identifies former senior agency officials lobbying their former agency, ranked
by concentration × volume × seniority. The Bridenstine-pattern detector.
Registry covers 23 federal agencies and is exhaustively unit-tested
(`tests/test_agency_registry.py` — 111 tests).

Implementation: `scripts/03_agency_concentration.py`.
See `skill/revolving-door-detector/SKILL.md`.

### Skill 5 — `federal-award-tracer` (`trace`)

Follows the money behind a revolving-door case. Given a lobbyist, their client
list, and a target agency, it traces the federal awards each client received from
that agency on USAspending.gov, verifies every row against the recipient's real
name (the API's recipient search is fuzzy), and emits a sourced per-client table
plus a framing note that separates discretionary grants (newsworthy) from routine
program participation (commodity purchases, food aid, formula financing). The
"follow the money" companion to `scan`. Three reproducible case files ship in
`skill/federal-award-tracer/cases/` — Steinberg → DOE ($1,080,820,046) and the
USDA cases ($1,398,877,777) reproduce to the dollar.

Implementation: `scripts/04_award_tracer.py` (live USAspending.gov API).
See `skill/federal-award-tracer/SKILL.md`.

### Skill 6 — `press-release-cross-ref` (`pressrel`)

Closes the third side of the triangle: which **members of Congress** have
publicly mentioned the companies surfaced by `scan` and the awards followed by
`trace`. Searches 141,332 House + Senate press releases (2022–Q1 2026) for
verified word-bounded mentions of a client / firm / topical name and returns a
journalism-ready table of date · member (party-state-chamber) · title · URL ·
snippet, plus per-client tallies, plus a framing note. Member-side filters
(party, state, chamber, official-domain substring) let a reporter scope the
question to "did Energy Committee Democrats talk about this in 2024?"

Integrates with the Reporter UI: every press-release report upserts into
`web/public/press_releases.json` (drives a planned `/pressrel` route), and
case files with a `match` block enrich the corresponding scan-finding rows in
`web/public/findings.json` so a Press-releases panel appears inline on the
candidate's card. `--enrich-findings` runs a one-shot batched pass that
attaches press-release evidence to every top-40 scan finding in ~10 seconds.

Bundled cases reproduce against the committed corpus: Steinberg DOE clients
(9 clients) and Limbaugh Interior/Reclamation clients (8 clients), both keyed
to their matching scan-finding rows.

Implementation: `scripts/05_pressrel_search.py` (DuckDB `press_releases` table;
no network access required). See `skill/press-release-cross-ref/SKILL.md`.

### Skill 7 — `coi-graph` (`coi`)

The **composition skill**. The other eight skills each produce a list (or a
log); this one joins their outputs into one investigable network so the
**connections across them** become visible. Inputs are entirely on-disk JSON
(no DB or network); the graph is built from `web/public/findings.json` after
scan + trace + pressrel have run.

Five typed node types (lobbyist, firm, agency, client, legislator) and five
typed edges (works_at, former_official_of, lobbies_for, funded_by, mentions)
encode the relationships. Three structural patterns are detected and surfaced
in the report header:

- **Triangles** — `(legislator, client, agency)` cycles where the member's
  press release praises a client whose lobbyist used to staff that client's
  funding agency. The headline structural finding.
- **Hubs** — clients receiving both agency dollars AND legislator mentions
  (score = `log10(dollars+1) × mentions`).
- **Bridges** — clients shared by two or more lobbyists in the top-N scan.

Renders four ways: a markdown summary (terminal / report PDF), a d3-force
JSON adjacency for the Reporter UI's `/graph` route (interactive force-
directed graph with zoom, pan, drag-to-pin, click-to-inspect), a static SVG
(pure-Python, no Graphviz dependency), and a Graphviz DOT source for users
who want to compile their own layouts.

Client-name canonicalization is what makes this work: scan's `AMSTED
INDUSTRIES`, pressrel's `Amsted Industries`, and trace's `Cargill (operating
entities)` all collapse onto the same `client:CARGILL` node, so the
triangles actually form.

Implementation: `scripts/06_coi_graph.py` (NetworkX for the graph + layout;
pure-Python SVG renderer; no system Graphviz dependency). See
`skill/coi-graph/SKILL.md`.

### Skill 8 — `comment-tracker` (`comment`)

The drafts in `notes/comment_requests/` are ready to send — this skill
turns those drafts into a *workflow*. Six event kinds (sent, acknowledged,
substantive_reply, followup_sent, closed, legal_threat), ten derived
statuses with deadline-pressure rules, one-line CLI for logging events, and
a Reporter UI `/comments` route that surfaces the status table with
color-coded chips (⚠ urgent, ⏳ active, ✓ replied, ❌ no reply, ⬜ not sent).
The source of truth is the committed `notes/comment_requests/comment_log.json`;
the script mirrors a slimmer derived view to `web/public/comment_log.json`
on every event log. A documented request for comment is a publication gate,
not a courtesy — this skill makes that gate auditable.

Implementation: `scripts/07_comment_tracker.py`. See
`skill/comment-tracker/SKILL.md`.

### Skill 9 — `archive-on-cite` (`archive`)

Snapshots every cited URL to **both** Wayback Machine and Archive.today
before publication. Walks the on-disk output of every other skill
(`findings.json`, `trails.json`, `press_releases.json`) for cited URLs,
submits each to both services with retry/backoff on 429s and timeouts, and
writes `output/archive_registry.json` mapping cited URL → snapshot URLs.
Two-service redundancy is the journalism standard — Wayback for static
pages, Archive.today for paywalled / dynamic content. Incremental
re-runnable: a `--skip-recent N` flag skips URLs successfully archived
within the last N days, so the script is cheap to run periodically right
up to publication.

Implementation: `scripts/08_archive_cite.py`. See
`skill/archive-on-cite/SKILL.md`.

### Tool — AP-style lint (`scripts/09_ap_style_lint.py`)

Not a `/fair-guard` mode (intentionally — it runs across many files at once
rather than as a single-shot mode). A focused, false-positive-controlled
AP-style checker for the findings report and notes: numbers under 10
(spelled out vs. numeral), `percent` vs. `%`, smart-quote / ASCII-quote
mixing, Oxford commas, `over` vs `more than` with numbers, postal-code
abbreviations outside table cells, and AP month abbreviations. Output is
grep-able (`PATH:LINE:COL message`); exit code 1 on findings so it works
as a pre-commit gate or PostToolUse hook (`--hook` mode reads Claude Code
hook context from stdin). 22 unit tests pin each rule plus its
false-positive counter-cases.

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

**Status:** Draft complete. 139 candidates identified across 22 agencies.

Ranks all Bridenstine-pattern cases across 23 federal agencies. Extends the
Artemis Group case study from one instance to a systemic analysis. Top cases:
Benjamin Steinberg (DOE, 90.2%), Mark Limbaugh (Interior, 72.6%),
Scott Parsons (CFTC, 89.8%), Jim Newsome (CFTC, 96.0%).

**External verification:** The prior senior-agency role of 8 of the top 10
candidates was independently confirmed against public sources (CFTC.gov, FCC.gov,
USDA, Senate committee releases, agency bios). A deepened, recipient-name-verified
money trail was then traced via the USAspending.gov API (reproducible via
`scripts/_probe_usaspending.py`): Steinberg's nine battery/critical-minerals clients
hold **~$1.08B** in discretionary DOE infrastructure-law grants; Limbaugh's nineteen
water-district clients hold **~$161.7M** in Interior/Reclamation awards; and the four
USDA cases (initially dismissed) turn out to have large USDA award trails — though
mostly *routine* program participation (commodity purchases, food aid, rural-utility
financing), a weaker conflict signal than discretionary grants. Details and
conflict-of-interest framing: `notes/08_external_verification_top_candidates.md`.

Output: `notes/06_structural_pattern_findings.md` (auto-generated)
Reporter UI: `web/` — run `cd web && npm install && npm run dev` → http://localhost:3000.
The UI ships 11 routes: `/` (landing), `/findings` (ranked list), `/findings/[id]`
(four-gate permalink per candidate, SSG), `/search` (name-first inverse lookup),
`/trails`, `/pressrel`, `/graph`, `/comments`, `/methods`, `/glossary`.

---

## Outside data used

Per the challenge guidance, all outside data used in the findings is disclosed here.

| Source | Used by | How it affects findings about named individuals/organizations |
|--------|---------|----------------------------------------------------------------|
| **USAspending.gov** (live HTTPS API, `api.usaspending.gov/api/v2/search/spending_by_award/`) | `trace` skill (`scripts/04_award_tracer.py`) | All money-trail dollar figures attributed to named firms and their clients (Steinberg/DOE $1.08B, Limbaugh/Interior $161.7M, USDA cases $1.40B) come from this source. Recipient names are verified against the API's returned `Recipient Name` field; the fuzzy `recipient_search_text` is treated as untrusted and filtered against caller-supplied `name_tokens`. |
| **CFTC.gov, FCC.gov, USDA.gov, Senate committee press releases** (manual look-ups during external verification) | `notes/08_external_verification_top_candidates.md` | Used to independently confirm the prior senior-agency role of 8 of the top 10 scan candidates. Specific URLs are cited under "Source URLs" in `notes/08`. |
| **Public agency bios and historical news archives** (manual, case-by-case) | `notes/09_reportability_gates_207_and_comment.md` — §207 analysis | Used to estimate the departure month/year for each top candidate. Four cases (Sherman/FCC, Newsome/CFTC, Bailey/USDA, Johnson/USDA) are flagged with † because the departure date is not yet pinned to the month — the §207 timed-ban conclusion is robust to that uncertainty (gaps exceed 2 years in every examined case), but the precise date should be confirmed against the official record before any publication. |

**Not used:** FEC contribution data, OpenSecrets aggregations, LinkedIn employment histories, or any non-public source. The corpus (Senate LDA + House LDA + Congressional press releases) and USAspending.gov are the entirety of the data underlying the findings.

---

## Conflicts of interest

Neither team member is a registered federal lobbyist, has been an employee of any U.S. federal agency named in the findings, has equity in or compensated relationships with any firm named in the findings (Venn Strategies, The Ferguson Group, Delta Strategy Group, The Russell Group, FGS Global, Torrey Advisory Group, Invariant LLC, Waneta Strategies, Spirit Rock Consulting), or has personal relationships with any of the named lobbyists. Neither team member has received funding from any party with an interest in this corpus or these findings beyond the GAIN challenge itself. We will declare in writing if that changes before submission.

---

## Legal-risk flags for the evaluation panel

The structural findings name specific living individuals and active lobbying firms. Per the Code of Conduct, we flag the following to the evaluation panel:

1. **No DOJ-referrable findings.** Our §207 cooling-off analysis (`notes/09_reportability_gates_207_and_comment.md`) found that **every examined top case clears the timed §207(c)/(d) bans by more than two years**. The structure we surface is the *legal* revolving door operating within current rules; we do not assert any violation of 18 USC §207 against any named individual.
2. **The permanent §207(a)(1) particular-matter bar is a live question, not a finding.** §207(a)(1) is matter-specific and cannot be established from the corpus alone — it requires matching a current lobbying matter to a specific matter the official personally and substantially worked on in government. We treat this as a question to put to each firm in the request-for-comment process (see `notes/comment_requests/`), not as a claim we make.
3. **Two residual timing questions** before any of the named cases are publication-ready: (a) pin the four †-flagged departure dates (Sherman/FCC, Newsome/CFTC, Bailey/USDA, Johnson/USDA) to the month against the official record; (b) confirm Kenneth Barbic had no USDA contact in 2021 (Barbic's case has the tightest §207 window in our top 10, with a ~3-year gap to first observed lobbying).
4. **Defamation guardrails.** All claims in the findings report cite a specific Senate LDA UUID, USAspending award ID, or named public source. Money-trail figures are characterized as **conflict-of-interest structure**, not proven wrongdoing; routine program participation (e.g., AMS commodity purchases, FAS food aid, RUS financing) is separated from discretionary, competitively-awarded grants in every table. Request-for-comment drafts for all seven firms are ready in `notes/comment_requests/`.

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
