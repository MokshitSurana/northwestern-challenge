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
/fair-guard trace                   # follow the money (federal-award-tracer; USAspending.gov)
/fair-guard pressrel                # cross-ref Congressional press releases (press-release-cross-ref)
/fair-guard coi                     # build the conflict-of-interest graph (coi-graph)
/fair-guard comment                 # request-for-comment tracker (comment-tracker)
/fair-guard archive                 # snapshot cited URLs to Wayback + Archive.today (archive-on-cite)
```

`argument-hint` shows `[mode: doctor | index | scan | resolve | trace | pressrel | coi | comment | archive]` in CLI autocomplete. The dispatcher reads `skill/<full-name>/SKILL.md` at runtime and executes its instructions. `allowed-tools: Read Bash` is pre-approved — no permission prompts during execution.

**Prerequisite guard (enforced by dispatcher):** `scan`, `resolve`, and `pressrel` require `output/investigation.duckdb`. If it doesn't exist, the dispatcher stops and shows two recovery options before attempting anything. `trace` does **not** need the DuckDB; it makes live calls to api.usaspending.gov and takes a case file. `coi` does **not** need the DuckDB either — it reads `web/public/findings.json` (the on-disk output of scan, enriched by trace and pressrel) and produces a composed graph.

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

# trace — USAspending money trail (agency → a lobbyist's clients); needs network
uv run scripts/04_award_tracer.py --print-template            # show case-file schema
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/usda_cases.json --out notes/usda_trail.md --json output/usda_awards.json
uv run scripts/04_award_tracer.py --case <case.json> --no-web # skip web/public writes

# pressrel — Congressional press-release cross-ref (no network; uses press_releases table)
uv run scripts/05_pressrel_search.py --print-template         # show case-file schema
uv run scripts/05_pressrel_search.py --mention "Cargill" --since 2024-01-01
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/limbaugh_clients.json --out notes/pressrel_limbaugh.md --json output/pressrel_limbaugh.json
uv run scripts/05_pressrel_search.py --enrich-findings        # auto-attach matches to every scan finding row
uv run scripts/05_pressrel_search.py --mention "X" --no-web   # skip web writes

# coi — conflict-of-interest graph (composes scan + trace + pressrel outputs; no DB or network)
uv run scripts/06_coi_graph.py                                # top-10 findings, all outputs (markdown + JSON + SVG + DOT)
uv run scripts/06_coi_graph.py --top 5                        # narrower scope
uv run scripts/06_coi_graph.py --finding-rank 1               # subgraph for one finding
uv run scripts/06_coi_graph.py --out notes/coi_summary.md     # persist markdown
uv run scripts/06_coi_graph.py --no-web --no-svg              # CI / offline mode

# comment — request-for-comment workflow tracker
uv run scripts/07_comment_tracker.py list                      # all firms with derived status + deadlines
uv run scripts/07_comment_tracker.py status venn_strategies    # one firm with full timeline
uv run scripts/07_comment_tracker.py log venn_strategies sent --addresses "press@x.com,b@x.com" [--deadline DATE]
uv run scripts/07_comment_tracker.py log <firm> acknowledged --by "Press Office" --summary "..."
uv run scripts/07_comment_tracker.py log <firm> substantive_reply --pointer URL --summary "..."
uv run scripts/07_comment_tracker.py log <firm> followup_sent --addresses press@firm
uv run scripts/07_comment_tracker.py log <firm> closed --kind response|no_response [--summary "..."]
uv run scripts/07_comment_tracker.py log <firm> legal_threat --by "Counsel" --summary "..."
uv run scripts/07_comment_tracker.py export                    # only write web/public/comment_log.json

# archive — snapshot every cited URL to Wayback + Archive.today (needs network)
uv run scripts/08_archive_cite.py                              # archive every cited URL across the project
uv run scripts/08_archive_cite.py --url <single-url>
uv run scripts/08_archive_cite.py --urls notes/extra_urls.txt
uv run scripts/08_archive_cite.py --service wayback            # or archive_today
uv run scripts/08_archive_cite.py --skip-recent 7              # only re-archive URLs older than N days
uv run scripts/08_archive_cite.py --dry-run                    # list URLs without submitting

# AP-style lint (intentionally not a /fair-guard mode — runs directly on markdown)
uv run scripts/09_ap_style_lint.py findings/findings_report.md
uv run scripts/09_ap_style_lint.py findings/*.md notes/*.md
uv run scripts/09_ap_style_lint.py --quiet findings/findings_report.md   # only print findings
uv run scripts/09_ap_style_lint.py --json findings/findings_report.md    # machine-readable
```

### Tests

`pytest` lives in the `dev` extra, which plain `uv sync` does NOT install. Install it
once, then invoke via `python -m pytest` (the bare `pytest` entrypoint is not on PATH):

```bash
uv sync --extra dev                                      # one-time: install pytest + ruff
uv run python -m pytest                                  # full suite (174 tests)
uv run python -m pytest tests/test_agency_registry.py -v # scan regex coverage (111 tests)
uv run python -m pytest tests/test_entity_resolver.py -v # resolver unit + F1 (33 tests)
uv run python -m pytest tests/test_entity_resolver.py::test_f1_on_db -s  # show F1 eval output
uv run python -m pytest tests/test_pressrel.py -v        # pressrel regex + DB integration (30 tests)
uv run python -m pytest tests/test_coi_graph.py -v       # coi-graph canonicalization + patterns + outputs (26 tests)
uv run python -m pytest tests/test_comment_tracker.py -v # comment-tracker schema + status + CLI (25 tests)
uv run python -m pytest tests/test_archive_cite.py -v    # archive URL collection + registry (14 tests)
uv run python -m pytest tests/test_ap_style_lint.py -v   # AP-style rules + false-positive control (22 tests)
```

The single F1-on-DB test is `@pytest.mark.skipif(not DB_PATH.exists())`, so the suite
runs green without `output/investigation.duckdb` (CI relies on this).

### Reporter UI (web/)

```bash
cd web && npm ci && npm run dev   # http://localhost:3000  (also serves /trails, /pressrel, /graph, /comments)
cd web && npm run build           # production build (also gated in CI)
cd web && npm run lint            # next lint
cd web && npm run typecheck       # tsc --noEmit
```

The UI reads two static JSON files from `web/public/`: `findings.json` (written by
`scan`) and `trails.json` (written by `trace`). Both pages have a ↻ Refresh button
that re-fetches the JSON without a page reload, so the flow is: run `/fair-guard scan`
or `/fair-guard trace`, switch to the browser tab, click refresh. The trace script
also embeds each trail into the matching scan-finding row (keyed on the case file's
`match: [{lobbyist_name, agency_short}]` block, case-insensitive), so a Money-trail
panel appears inline on the matching candidate's card on `/`.

### Linting

```bash
uv run ruff check scripts/
uv run ruff check scripts/ --fix
```

### Findings report → PDF

The report builds with Pandoc + Typst (Typst ships as a self-contained Python wheel,
so this works cross-platform with no GTK/LaTeX). The `findings/*.pdf` and `_report.typ`
are gitignored — the `.md` is the tracked source.

```bash
pandoc -s findings/findings_report.md -t typst -o findings/_report.typ
uv run --with typst python -c "import typst; typst.compile('findings/_report.typ', output='findings/findings_report.pdf')"
rm findings/_report.typ
```

### Continuous integration

`.github/workflows/ci.yml` runs on every push/PR to `master` across **Linux, macOS,
and Windows**: `uv sync --extra dev`, `npm ci`, `doctor`, the pytest suite, `ruff`, and
`npm run build`. `doctor` exits 0 with no corpus/DB (they are optional checks → WARN),
so the workflow is a true clean-clone reproducibility gate without shipping the 8.6 GB
data or the DuckDB.

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
scripts/04_award_tracer.py        → web/public/trails.json (upserts per case_id)
                                   → web/public/findings.json (enriches matching rows with `trail`)
scripts/05_pressrel_search.py     → web/public/press_releases.json (upserts per case_id)
                                   → web/public/findings.json (enriches matching rows with `press_releases`)
scripts/06_coi_graph.py           → web/public/coi_graph.json (d3-force shape for /graph route)
                                   → output/coi_graph.svg (static SVG, pure-Python, no Graphviz)
                                   → output/coi_graph.dot (Graphviz DOT source)
scripts/07_comment_tracker.py     → notes/comment_requests/comment_log.json (source of truth)
                                   → web/public/comment_log.json (slimmed mirror for /comments route)
scripts/08_archive_cite.py        → output/archive_registry.json (per-URL Wayback + Archive.today snapshot URLs)
                                   → web/public/archive_registry.json (mirror for UI badges)
scripts/09_ap_style_lint.py       → stdout (one finding per line: PATH:LINE:COL message)
    │
    ▼
web/src/app/page.tsx             (reporter UI — findings + inline Money trail / Press-release panels)
web/src/app/trails/page.tsx      (reporter UI — money-trail index, refresh button)
web/src/app/pressrel/page.tsx    (reporter UI — press-release report index, refresh button)
web/src/app/graph/page.tsx       (reporter UI — interactive D3 force-directed CoI graph)
web/src/app/comments/page.tsx    (reporter UI — request-for-comment status table, derived from event timelines)
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

### Nine Agent Skills

| Short name | Full name | Status | Implementation | Tests |
|-----------|-----------|--------|---------------|-------|
| `doctor` | setup-validator | Shipped | `scripts/doctor.py` + `skill/doctor/` | CI-verified on Linux + macOS + Windows (`.github/workflows/ci.yml`) |
| `index` | lda-corpus-indexer | Shipped | `scripts/01_build_index.py` + `skill/lda-corpus-indexer/` | `scripts/verify_build.py` — 34 invariants |
| `resolve` | entity-resolver | Shipped | `scripts/02_entity_resolver.py` + `skill/entity-resolver/` | `tests/test_entity_resolver.py` — 33 tests, F1 = 0.963 |
| `scan` | revolving-door-detector | Shipped | `scripts/03_agency_concentration.py` + `skill/revolving-door-detector/` | `tests/test_agency_registry.py` — 111 tests |
| `trace` | federal-award-tracer (v1.1.0) | Shipped | `scripts/04_award_tracer.py` + `skill/federal-award-tracer/` | 3 reproducible case files (Steinberg DOE $1.08B, USDA $1.40B exact) + a no-case-file generalization eval; `evals/evals.json` |
| `pressrel` | press-release-cross-ref (v1.0.0) | Shipped | `scripts/05_pressrel_search.py` + `skill/press-release-cross-ref/` | `tests/test_pressrel.py` — 30 tests; 3 reproducible case files (Steinberg, Limbaugh, USDA) |
| `coi` | coi-graph (v1.0.0) | Shipped | `scripts/06_coi_graph.py` + `skill/coi-graph/` | `tests/test_coi_graph.py` — 26 tests (canonicalization, build, triangle/hub/bridge detection, output renderers, determinism, real-DB integration) |
| `comment` | comment-tracker (v1.0.0) | Shipped | `scripts/07_comment_tracker.py` + `skill/comment-tracker/` | `tests/test_comment_tracker.py` — 25 tests (schema, status derivation with deadline pressure, CLI roundtrip) |
| `archive` | archive-on-cite (v1.0.0) | Shipped | `scripts/08_archive_cite.py` + `skill/archive-on-cite/` | `tests/test_archive_cite.py` — 14 tests (URL collection, registry persistence, is_recent filter); network-touching paths intentionally not covered in CI |

(Plus one *tool*, not a /fair-guard mode: `scripts/09_ap_style_lint.py` —
the AP-style markdown linter, covered by `tests/test_ap_style_lint.py` (22
tests). Runs directly on findings/*.md and notes/*.md; suitable for a
PostToolUse hook on Edit/Write via `--hook` mode.)

### Agent Skills architecture (three layers)

Skills exist at three levels simultaneously — each serves a different audience:

| Layer | Path | Standard | Who uses it |
|-------|------|----------|-------------|
| Standalone submission artifacts | `skill/<full-name>/` | agentskills.io (original) | Challenge judges, direct skill users |
| Canonical agent store with modes | `.agents/skills/fair-guard/` | agentskills.io (modes architecture) | Other agents (Codex, Gemini, Qwen) |
| Claude Code dispatcher | `.claude/skills/fair-guard/` | Claude Code extensions | Claude Code CLI (`/fair-guard`) |

**Do not put Claude Code-specific fields** (`$ARGUMENTS`, `argument-hint`, `context: fork`, `disable-model-invocation`) into `skill/` files — those are the portable, submission-facing artifacts. Keep those extensions in `.claude/skills/` only.

The `.agents/skills/fair-guard/modes/` copies have cleaned-up frontmatter (non-standard fields like `version`, `author`, `tools` moved under `metadata:` and `compatibility:` per the agentskills.io spec). The originals in `skill/` are untouched.

The dispatcher routes `$ARGUMENTS` short names to `skill/<full-name>/SKILL.md` at runtime. It enforces prerequisites deterministically (DuckDB check for `scan`/`resolve`, data dir check for `index`, network + case file for `trace`) before reading any mode file.

**Editing `trace` (federal-award-tracer):** the load-bearing judgment in this skill is the **wide-net-first name-token discipline** in its "Choosing search terms and name tokens" section — search the *shortest distinctive core term* (`Group14`, not the full legal name), read every returned recipient name, then keep same-company project SPVs (e.g. `GROUP14 BAM-2, INC.`), exclude coincidental collisions, and surface/flag same-parent-but-distinct entities (e.g. `ICL SPECIALTY PRODUCTS INC` vs `ICL-IP America`). A too-narrow search silently undercounts a client's biggest awards by hundreds of millions with no visible warning — this is the exact failure the v1.0→v1.1 fix addressed (see the generalization eval). Preserve this guidance when editing, and keep the `.agents/.../modes/trace/SKILL.md` copy in sync (it defers full guidance to `skill/` but mirrors the version + a one-line summary).

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

### Structural finding (Track 2)

`notes/06_structural_pattern_findings.md` — auto-generated by `scripts/03_agency_concentration.py`
(139 candidates across 22 agencies). Run `uv run scripts/03_agency_concentration.py` to
regenerate. **This file is rewritten in full on every scan run** (`path.write_text`), so
never hand-edit it — durable annotations belong elsewhere.

### External verification (durable, human-authored)

`notes/08_external_verification_top_candidates.md` — independent confirmation of the
prior-agency role for 8 of the top 10 scan candidates (CFTC.gov, FCC.gov, USDA, Senate
committee releases), plus a deepened, recipient-name-verified USAspending.gov money trail
(reproducible via `scripts/_probe_usaspending.py`): Steinberg's 9 battery/critical-minerals
clients hold ~$1.08B in discretionary DOE BIL grants; Limbaugh's 19 water-district clients
hold ~$161.7M in Interior/Reclamation awards; and the four USDA cases — wrongly dismissed
as "not applicable" in the first pass — do have large USDA award trails (e.g. Cargill
$704.9M, National Rural Water $272.0M), though mostly routine program participation (AMS
commodity purchases, food aid, RUS financing) rather than discretionary grants. Kept here
(not in `notes/06`) precisely because `notes/06` is regenerated by the scan. Money trails
are framed as conflict-of-interest *structure*, not wrongdoing, and discretionary grants
are weighted over formulaic program payments.

---

## Priority Order (remaining work as of June 5, 2026)

All nine skills ship with tests/reproducible cases; cross-platform CI is green; the
findings report, external verification, and money trail are done. **All four
per-case reportability gates are now closed** (role, money trail → `notes/08`;
§207 cooling-off + request-for-comment → `notes/09`).

Remaining work for submission is editorial/operational, not in-repo:

1. **Actually send the drafted requests for comment** and log responses (the per-firm
   drafts + questions are ready in `notes/09_reportability_gates_207_and_comment.md`).
   Before print, also pin the four †-flagged departure dates to the month and confirm
   Barbic had no 2021 USDA contact (the one residual §207 timing check) — both noted in
   `notes/09`. The structural finding itself is reportable now: confirmed role, confirmed
   money trail, confirmed legality (timed §207 bans clear in all examined cases), fair-
   comment plan drafted.

Done this cycle (do not redo): external verification of top scan candidates; deepened,
recipient-name-verified USAspending money trail across all top candidates (Steinberg DOE
~$1.08B; Limbaugh Interior ~$161.7M; USDA cases checked + corrected) via
`scripts/_probe_usaspending.py`; `findings_report.md` numbers refreshed + exported to PDF;
README submission map refreshed; cross-platform CI workflow (Linux/macOS/Windows);
reconciled both firm-name discrepancies against the raw LDA corpus — Sherman's "Waneta
Strategies, LLC" (45 filings: CTIA/Crown Castle/Lynk) and Martin's "Spirit Rock
Consulting" (264 filings) are both authoritative in the filing record. **Built the fifth
skill, `trace` (federal-award-tracer): `scripts/04_award_tracer.py` productionizes the
probe into a case-driven CLI (markdown table + discretionary-vs-routine framing note),
with 3 reproducible case files in `skill/federal-award-tracer/cases/` (Steinberg DOE
$1,080,820,046 and USDA $1,398,877,777 reproduce to the dollar), wired into all three
skill layers + `evals/evals.json`.**

---

## Submission checklist

- [x] `uv run scripts/01_build_index.py --sample` runs clean from scratch on a new machine (note: validated against `scripts/verify_build.py --sample`)
- [x] `uv run scripts/03_agency_concentration.py` runs and produces output (139 candidates, 22 agencies)
- [x] `uv run scripts/02_entity_resolver.py` runs and writes entity_map (F1 = 0.963)
- [x] `uv run scripts/verify_build.py` runs and all 34 invariants pass
- [x] `uv sync --extra dev && uv run python -m pytest` — 261 tests passing (111 registry + 33 resolver + 30 pressrel + 26 coi-graph + 25 comment-tracker + 14 archive + 22 AP-style)
- [x] All SKILL.md files have valid YAML frontmatter + instructions
- [x] `/fair-guard doctor` runs without errors and prints a correct checklist (CI-verified Linux/macOS/Windows)
- [x] `/fair-guard scan` routes correctly and executes without permission prompts
- [x] `findings/findings_report.md` exported to PDF (pandoc + typst; see Commands)
- [x] `traces/` contains logs keyed to skill invocations
- [x] `README.md` maps all submission artifacts
- [x] CI workflow green on Linux + macOS + Windows (`.github/workflows/ci.yml`)
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
skill/federal-award-tracer/SKILL.md        # Skill: trace — submission artifact
skill/federal-award-tracer/cases/          # 3 reproducible USAspending case files
skill/press-release-cross-ref/SKILL.md     # Skill: pressrel — submission artifact
skill/press-release-cross-ref/cases/       # 3 reproducible press-release case files
skill/coi-graph/SKILL.md                   # Skill: coi — submission artifact (composes scan + trace + pressrel)
skill/comment-tracker/SKILL.md             # Skill: comment — request-for-comment workflow
skill/archive-on-cite/SKILL.md             # Skill: archive — Wayback + Archive.today snapshots

.agents/skills/fair-guard/SKILL.md         # agentskills.io master skill
.agents/skills/fair-guard/modes/
    doctor/SKILL.md                        # agentskills.io compliant copies
    index/SKILL.md                         # (short names; originals in skill/ unchanged)
    resolve/SKILL.md
    scan/SKILL.md
    trace/SKILL.md
    pressrel/SKILL.md
    coi/SKILL.md
    comment/SKILL.md
    archive/SKILL.md

.claude/skills/fair-guard/SKILL.md         # Claude Code dispatcher (/fair-guard)

scripts/doctor.py                          # Skill: doctor implementation (cross-platform)
scripts/01_build_index.py                  # Skill: index implementation (ETL)
scripts/02_entity_resolver.py              # Skill: resolve implementation
scripts/03_agency_concentration.py         # Skill: scan implementation
scripts/04_award_tracer.py                 # Skill: trace implementation (USAspending)
scripts/05_pressrel_search.py              # Skill: pressrel implementation (DuckDB press_releases)
scripts/06_coi_graph.py                    # Skill: coi implementation (NetworkX graph + pure-Python SVG)
scripts/07_comment_tracker.py              # Skill: comment implementation (CLI + JSON state machine)
scripts/08_archive_cite.py                 # Skill: archive implementation (Wayback + Archive.today)
scripts/09_ap_style_lint.py                # AP-style markdown linter (not a /fair-guard mode)
scripts/verify_build.py                    # post-index invariants (34 checks)
scripts/_probe_usaspending.py              # original money-trail probe (trace's ancestor)
scripts/_archive/                          # superseded scripts kept for history
scripts/_diagnose_*.py                     # one-shot data-quality probes

evals/evals.json                           # trace skill test prompts + assertions (incl. eval #4 generalization, no shipped case file)
tests/test_agency_registry.py              # 111 tests for scan registry
tests/test_entity_resolver.py              # 33 tests for resolver (incl. F1 eval)
tests/test_pressrel.py                     # 30 tests for pressrel (regex, snippet, schema, DB integration)
tests/test_coi_graph.py                    # 26 tests for coi-graph (canonicalization, patterns, renderers, determinism)
tests/test_comment_tracker.py              # 25 tests for comment-tracker (schema, status derivation, CLI roundtrip)
tests/test_archive_cite.py                 # 14 tests for archive (URL collection, registry, is_recent)
tests/test_ap_style_lint.py                # 22 tests for AP-style lint (per-rule + false-positive control)

findings/findings_report.md               # final findings (→ PDF via pandoc + typst)
notes/05_finding_bridenstine.md           # anchor finding (verified)
notes/06_structural_pattern_findings.md   # Track 2 output (AUTO-GENERATED — never hand-edit)
notes/08_external_verification_top_candidates.md  # durable verification + USAspending money trail (gates 1-2)
notes/09_reportability_gates_207_and_comment.md   # §207 cooling-off analysis + request-for-comment drafts (gates 3-4)
notes/HANDOFF_TO_MOKSHIT_SKILL_DOCTOR.md  # doctor skill spec + testing tasks for Mokshit

.github/workflows/ci.yml                  # cross-platform CI (Linux/macOS/Windows)

web/src/app/page.tsx                      # reporter UI — server component
web/src/app/FindingsClient.tsx            # reporter UI — interactive client
web/src/app/types.ts                      # shared TypeScript interfaces
docker-compose.yml                        # full system orchestration
```
