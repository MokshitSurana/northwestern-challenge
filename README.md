# FairGuard — Northwestern Agentic AI Investigative Journalism Challenge

**Team:** FairGuard
**Members:** Mokshit Surana (lead, agent orchestration & investigation logic), Archit Rathod (data pipelines, reproducibility, reporter-facing tooling)
**Competition:** [Northwestern GAIN Agentic AI Investigative Journalism Challenge](https://www.gain-agent-challenge.northwestern.edu/details/)
**Deadline:** July 15, 2026

---

## What this competition is

Northwestern's GAIN initiative is running a competition asking teams to use AI agents to investigate a large corpus of federal lobbying records and congressional press releases. The corpus covers 2022 through Q1 2026 and combines:

- **Senate LDA filings** — quarterly lobbying disclosures from the Secretary of the Senate
- **House LDA filings** — the equivalent from the House Clerk
- **Congressional press releases** — scraped from official House and Senate member websites

The deliverable is **not** a one-off investigation. It is a **reusable Agent Skill** that another journalist could pick up and run on a completely different investigation, plus a findings report demonstrating that the skill produces real journalism on this corpus.

Submissions are scored on two gates:

1. **Findings must be real journalism** — accurate, sourced to specific records, of genuine public interest. If findings don't clear this bar, nothing else is scored.
2. **The skill is scored on four equal-weight dimensions:** (a) keeps a long investigation organized, (b) is efficient with the corpus, (c) produces human-verifiable claims, (d) extends what an agent can do for investigations.

**Reproducibility is a hard gate.** If a judge can't re-run the skill, it caps at 1/3 on every scoring dimension regardless of quality. Everything we build must run from a clean clone of this repo.

Prizes: $5,000 / $2,500 / $1,000 for top three. Top submissions get individual writeups on the GAIN blog and may be invited to present at the Computation + Journalism Symposium.

Full details: `https://www.gain-agent-challenge.northwestern.edu/details/`

---

## What we're building

Two-to-three reusable Agent Skills, plus an anchor investigation that demonstrates each one:

### Skill 1 — `lda-corpus-indexer` (built, needs packaging)

Converts raw federal lobbying disclosure dumps (Senate JSON, House XML, Congress press release JSONL) into a flat, queryable DuckDB analytical store with per-row provenance. Built around `scripts/01_build_index.py`.

**Why it's reusable:** Any journalist receiving a fresh bulk LDA export — Senate and House both publish quarterly — can run this and get a queryable database in roughly 2.5 hours instead of spending days wrangling 409K XML files and inconsistent JSON schemas.

### Skill 2 — `entity-resolver` (designed, not yet built)

Normalizes and clusters messy organization/person name strings across LDA records so that "MICROSOFT CORP", "Microsoft Corporation", and "Microsoft Corp." resolve to a single canonical entity, with originals preserved for audit. Two algorithms in one skill: one for organizations (normalize + fuzzy match), one for people (parse into structured form + exact-on-first + fuzzy-on-last).

**Why it's reusable:** Every messy government dataset has this problem — FARA filings, FEC donor lists, state contractor records, hospital ownership filings. The skill is corpus-agnostic.

**Why it's a prerequisite:** Without entity resolution, every cross-corpus join is noisy. The structural pattern query (Skill 3) cannot run cleanly until names across House and Senate (and across years) are resolved.

### Skill 3 — Possibly `revolving-door-detector` + `cross-corpus-temporal-coupling`, possibly merged into one skill (not yet built)

Identifies former senior government officials who now lobby their former agency, and pairs that with the say-vs-pay analysis of cross-corpus temporal alignment between lobbying activity and congressional press release rhetoric.

This is downstream of skills 1 and 2 and depends on the entity resolver to work. Design TBD.

### The anchor investigation: The Artemis Group

Our primary finding (in `notes/05_finding_bridenstine.md`) is a structural analysis of The Artemis Group, the lobbying firm founded by former NASA Administrator Jim Bridenstine in Q4 2024. The firm employs five lobbyists who collectively rank among the most active NASA-targeting lobbyists in the entire Senate LDA corpus, four of whom worked directly under Bridenstine in his prior government roles.

**This finding is the demo.** It proves the skills produce real journalism. Track 2 — extending the analysis to find other agency heads following the same pattern — is the structural finding that turns the case study into a piece on systemic revolving-door dynamics. That work is in progress.

---

## Where we are right now

### ✅ Done

- **Repo set up**, `pyproject.toml` with pinned dependencies (`duckdb`, `polars`, `orjson`, `lxml`, `rapidfuzz`, `tqdm`).
- **Data downloaded** (~8.6 GB, lives in `data/data/` due to nested zip extraction).
- **`scripts/01_build_index.py` built and working.** ETL pipeline that reads all three datasets, writes Parquet files, then loads everything into `output/investigation.duckdb` (2.84 GB).
- **Multiple parser bugs found and fixed:**
    - Senate JSON: lobbyist names were nested under `lobbyist.first_name`/`last_name`, not at the top level
    - House XML: lobbyist names use `<lobbyistFirstName>` + `<lobbyistLastName>`, not `<lobbyistName>`
    - House XML: ALI codes are nested under `<alis>/<ali_info>/<issueAreaCode>`, not at `<alis>/<ali_Code>` (parser was missing 94% of ALI codes before fix)
    - Polars schema inference: forced explicit `pl.Utf8` schemas on House writes to prevent integer-inference bug when columns are all-null in some files
- **DuckDB analytical store built.** Ten tables (3 House, 6 Senate, 1 press releases), plus convenience views `revolving_door` and `senate_spend_by_issue`.
- **Anchor finding written** in `notes/05_finding_bridenstine.md`.
- **Cross-validation between Senate and House confirmed** for the Artemis Group filings (115 House filings, 133 Senate filings, consistent client roster, 125 House lobbyist rows naming Bridenstine).

### 🚧 In progress / not yet done

- **Track 2** — structural pattern query across all former agency heads. Designed in concept (see `notes/05_finding_bridenstine.md` §12), but no code yet.
- **Entity resolver (Skill 2)** — designed, not built. See "Plan for entity resolver" below.
- **Skill packaging** — `01_build_index.py` is working code; needs to be packaged as an Agent Skill per the [Agent Skills specification](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview). This means a `SKILL.md` with YAML frontmatter, organized `scripts/` and `references/` folders, etc.
- **Interaction trace logging** — competition requires full logs of model sessions, keyed to skill invocations. Right now we have raw Claude chat transcripts in `traces/` (still being saved manually). Needs a more systematic capture mechanism once we start running the skill agentically.
- **House parser still has known minor issues:** `inactive_lobbyists` section is intentionally skipped. `<lobbyistSuffix>` is captured. Legacy XML schema (pre-2024 or so) handled via fallback path in `parse_house_xml`.

---

## Repository structure

```
.
├── README.md                         # this file
├── pyproject.toml                    # pinned dependencies, Python 3.11+
├── uv.lock
├── data/                             # raw data — gitignored, not in repo
│   └── data/                         # zip extraction nesting
│       ├── congress_press/           # JSONL files, 504 MB
│       ├── senate/                   # JSON files, 2.2 GB
│       └── house/                    # XML files, 5.9 GB, 409K files
├── output/                           # gitignored
│   ├── parquet/                      # intermediate Parquet files, ~1 GB total
│   └── investigation.duckdb          # 2.84 GB analytical store
├── scripts/                          # runnable scripts
│   ├── 01_build_index.py             # main ETL pipeline (full or sample mode)
│   ├── 01b_rebuild_house_lobbyists.py  # targeted House lobbyist rebuild (deprecated; use 01c)
│   └── 01c_rebuild_house_all.py      # targeted full House rebuild (filings + activities + lobbyists)
├── notebooks/                        # exploratory scripts, query runs
│   ├── 04_revolving_door_leads.py
│   ├── 05b_bridenstine_recheck.py
│   ├── 05c_verification_round_2.py
│   ├── 05d_house_crossval.py
│   ├── 05e_house_lobbyist_diagnostic.py
│   └── 05f_ali_diagnostic.py
├── notes/                            # markdown findings, design docs, query logs
│   ├── 03_skill_packaging_plan.md
│   ├── 04_revolving_door_leads.txt
│   ├── 05_finding_bridenstine.md     # ← THE ANCHOR FINDING
│   ├── 05b_bridenstine_recheck.txt
│   ├── 05c_verification_round_2.txt
│   ├── 05d_house_crossval.txt
│   └── 01c_rebuild_log.txt
├── skill/                            # eventual Agent Skill packaging — empty so far
└── traces/                           # interaction traces with Claude
```

**What's gitignored:** `data/`, `output/`, `__pycache__/`, `.venv/`.

---

## How to set up from scratch

```bash
# Clone the repo
git clone <repo-url> fairguard
cd fairguard

# Install dependencies with uv
uv sync

# Download the corpus from the GAIN organizers' Google Drive link
# (URL in original registration email; not in this repo for licensing reasons)
# Extract to ./data/data/  (note the nested data/data/ due to zip structure)

# Sanity check the data
du -sh data/data/congress_press data/data/house data/data/senate
# Should be approximately: 504M  5.9G  2.2G

# Build the full DuckDB index (~2.5 hours on a typical laptop)
uv run scripts/01_build_index.py

# Verify the build
uv run python -c "
import duckdb
con = duckdb.connect('output/investigation.duckdb', read_only=True)
for t in ('press_releases', 'senate_filings', 'house_filings', 'house_lobbyists'):
    print(f'{t}: {con.execute(f\"SELECT COUNT(*) FROM {t}\").fetchone()[0]:,}')
"
```

Expected row counts after a clean build:

| Table                | Rows      |
| -------------------- | --------- |
| press_releases       | 141,332   |
| senate_filings       | 418,170   |
| senate_activities    | 799,192   |
| senate_lobbyists     | 2,121,863 |
| senate_gov_entities  | 2,016,363 |
| senate_contributions | 636,833   |
| house_filings        | 409,640   |
| house_activities     | ~781K     |
| house_lobbyists      | ~540K     |

(House counts may shift slightly between rebuilds depending on parser edge cases. The Senate counts should be deterministic.)

---

## The corpus, briefly

### Congressional press releases (`congress_press/`)

- ~141K records covering 2022-01 through 2026-03
- JSONL format, one record per line
- Each record has the member info (`bioguide_id`, name, party, state, chamber), date, URL, title, and full text body
- ~48K releases in 2025 alone
- Source: thescoop.org/congress-press

### Senate LDA (`senate/`)

- 418K filings, JSON arrays
- Includes registrations, quarterly activity reports, semiannual contribution reports
- Fields: filing UUID, registrant, client, lobbying activities (with ALI issue codes), lobbyists (with `covered_position` describing prior government roles), government entities targeted
- Source: Senate LDA API

### House LDA (`house/`)

- 409K filings, XML format — one file per filing
- Two schemas: `LOBBYINGDISCLOSURE1` (registrations) and `LOBBYINGDISCLOSURE2` (quarterly reports)
- Fields parallel to Senate. Note: `senate_id` field links a House filing to its Senate counterpart (format: `{senate_registrant_id}-{engagement_id}` for the post-2024 schema)
- Source: House Clerk

### Cross-dataset joins

- **Press → Senate/House LDA:** via member name and quarter. Press releases identify members by `bioguide_id` but LDA records target government entities ("SENATE", "HOUSE OF REPRESENTATIVES") and specific committees, not individual members.
- **Senate ↔ House LDA:** via `senate_id` field in House records. Note that House's `senate_id` is the Senate's _registrant_-_client engagement_ ID, not the Senate's `filing_uuid`. The link is firm-engagement-level, not filing-level.

A more detailed manual on the corpus structure ships in the data download as `data/data/README.md` or equivalent.

---

## Quick reference: how to query the DB

```python
import duckdb
con = duckdb.connect("output/investigation.duckdb", read_only=True)

# Top 10 lobbying firms by total disclosed Senate income 2025
con.execute("""
    SELECT registrant_name, SUM(income)/1e6 AS income_M, COUNT(*) AS filings
    FROM senate_filings
    WHERE filing_year = 2025
    GROUP BY registrant_name
    ORDER BY income_M DESC NULLS LAST
    LIMIT 10
""").fetchall()

# Lobbyists with covered_position mentioning a former agency role
con.execute("""
    SELECT lobbyist_name, covered_position, COUNT(*) AS filings
    FROM senate_lobbyists
    WHERE covered_position ILIKE '%NASA%'
    GROUP BY lobbyist_name, covered_position
    ORDER BY filings DESC
    LIMIT 20
""").fetchall()
```

Useful convenience views (already in the DB):

- `revolving_door` — Senate lobbyists with non-empty `covered_position`, joined to filing context
- `senate_spend_by_issue` — quarterly aggregate spend by ALI issue code

---

## Next steps (for whoever picks this up next)

### Immediate (this week)

1. **Re-verify the Bridenstine finding numbers** against the now-corrected House data. Specifically: re-run `notebooks/05d_house_crossval.py` and `notebooks/05c_verification_round_2.py` and confirm the writeup in `notes/05_finding_bridenstine.md` still matches. Small numerical drift is OK; large drift means a claim needs softening or removal.

2. **Save this conversation thread (and prior threads) to `traces/`.** Competition requires full logs of model sessions.

3. **Track 2 (the structural query).** Find all former senior agency officials in the corpus whose covered_position mentions a federal agency, who now lobby that same agency. Bridenstine becomes one example among many. The skill required to surface this — entity resolution between covered_position text and government_entities table — is itself a deliverable. See `notes/05_finding_bridenstine.md` §12 for the framing.

### Plan for entity resolver (Skill 2)

Two algorithms in one skill, dispatched by entity type:

**For organization names:**

1. Lowercase, replace `&` → "and", strip punctuation
2. Remove legal suffixes from end only: `["llc", "inc", "incorporated", "corp", "corporation", "co", "company", "lp", "llp", "ltd", "limited", "plc", "pllc", "pc", "p.c.", "the"]` (also strip leading "the")
3. Collapse whitespace
4. Exact match on normalized form → cluster
5. Fuzzy match with `rapidfuzz.token_sort_ratio`, threshold ~92 → cluster
6. Output `match_method`: `exact`, `normalized_exact`, `fuzzy_high`, `fuzzy_low` (for human review)

**For person names:**

1. Detect format (comma-separated "Smith, John" vs space-separated "John Smith")
2. Normalize to `(last, first, middle_initial)` tuple
3. Exact match on last name (after lowercase + strip suffix); exact-or-initial match on first name
4. Use fuzzy matching only on last name with threshold 95+

**Build the eval set first.** Free labeled positives come from the data itself: any `registrant_id` (or `client_id`) with 2+ distinct names is a known positive cluster. Sample 500 of these + 500 random cross-cluster negatives. Hold this out as a test set. The threshold and normalization rules get tuned against this eval.

Time-box this skill to 2-3 days. Resolvers are a black hole — there's always more precision to squeeze. The skill is good enough when F1 hits ~0.92 on the held-out eval set.

### Skill 1 packaging

`scripts/01_build_index.py` is working production code. Repackage as an Agent Skill:

```
skill/lda-corpus-indexer/
├── SKILL.md              # YAML frontmatter + instructions to the agent
├── scripts/
│   ├── build_index.py    # the ETL itself (renamed from 01_build_index.py)
│   └── rebuild_house.py  # the targeted-rebuild script (renamed from 01c)
├── references/
│   ├── senate_schema.md  # what fields exist in the Senate JSON, with examples
│   ├── house_schema.md   # what fields exist in the House XML, with examples
│   ├── known_quirks.md   # parser gotchas: lobbyistFirstName, ali_info nesting, schema inference
│   └── joins.md          # how to cross-reference between datasets
└── assets/
    └── example_filing.json  # sample for the agent to reference
```

The SKILL.md should describe:

- What the skill does in one sentence
- Inputs it expects (paths to raw LDA dumps)
- Outputs it produces (Parquet files + DuckDB)
- How to invoke it
- Common failure modes (schema inference, encoding issues on Windows)

See the [Agent Skills specification](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) for exact format requirements.

### Reproducibility checklist (before submission)

- [ ] `pyproject.toml` pins all dependencies with explicit versions, not ranges
- [ ] `python_requires` set to `>=3.11`
- [ ] Data path is fully configurable via `DATA_ROOT` env var
- [ ] Output paths configurable via `OUTPUT_ROOT` env var
- [ ] `--sample` flag works for fast validation
- [ ] `--clean` flag removes stale Parquet files before rebuild
- [ ] Code runs identically on Linux and Windows (we developed on Windows; test on Linux before submission)
- [ ] Every script has a docstring describing what it does and how to run it
- [ ] At least one end-to-end test that runs the sample mode and verifies expected row counts

---

## Known issues, gotchas, and design decisions

**Why DuckDB and not Postgres?** Single-file analytical database, no server to run, reads Parquet natively, columnar so aggregations are fast. Reproducibility wins.

**Why Parquet intermediate before DuckDB?** Two reasons. First, if the DuckDB build fails halfway, we don't reparse 409K XML files. Second, the Parquet files are themselves a deliverable — other people can use them without DuckDB.

**Why explicit Polars schemas?** Polars infers schemas per file. If a particular Parquet file has all-null values in a column, Polars infers a numeric type and DuckDB's `union_by_name=True` produces a broken table. We learned this the hard way (see commit history). All House writes now use explicit `pl.Utf8` schemas to prevent the issue.

**Why the `data/data/` nesting?** The competition zip extracts that way on some systems. Set `DATA_ROOT=data` if your extraction is flat.

**The Senate data has two name structures.** In `lobbying_activities[].lobbyists[]`, names are nested as `lob["lobbyist"]["first_name"]` + `["last_name"]`, not at the top level. This is undocumented in the official LDA spec and caused our initial parser to populate `lobbyist_name = None` for the entire Senate corpus until we found and fixed it.

**The House data has two ALI schemas.** Pre-2024 (roughly) used `<alis>/<ali_Code>` with flat lists, post-2024 uses `<alis>/<ali_info>/<issueAreaCode>` with nested blocks where each block has its own activity description and lobbyists. Our parser handles both via fallback logic in `parse_house_xml`.

**The House LDA filing IDs are NOT Senate `filing_uuid`s.** Within House records, the `senate_id` field uses the format `{senate_registrant_id}-{engagement_id}`. This is an engagement-level identifier, not a filing-level one. Cross-chamber joins on this field are firm-engagement-level, not filing-level.

**Press release dates are strings, not timestamps.** We parse to derive a `filing_quarter` column at ETL time for easier joins; the raw `date` column is preserved as-is in case any downstream needs the original format.

**The `senate_lobbyists` table has 2.1M rows, larger than expected.** This is because a single lobbyist appears once per `lobbying_activity` within a filing, not once per filing. A filing with 5 activities and 3 lobbyists generates 15 rows. Deduplication on `(filing_uuid, lobbyist_name)` is necessary for most "how many lobbyists" queries.

---

## Open questions for the team

1. Should `revolving-door-detector` and `cross-corpus-temporal-coupling` be one skill or two? (Two = better scoring on "novel capabilities" criterion; one = simpler to package and validate.)
2. What's our position on bringing in external data (Congress.gov bill text, FEC contributions, FARA filings)? The challenge allows it but every external source we add multiplies the reproducibility burden.
3. How do we want to capture interaction traces — write our own logger or use Anthropic's API features? The competition specifies "raw JSON or rendered page" and "keyed to skill invocations."

---

## Contact

- Mokshit Surana — mokshitsurana3110@gmail.com (primary contact for the submission)
- Archit Rathod — architrathod77@gmail.com

For competition-related questions: Nick Hagar, Jeremy Gilbert (organizers).
