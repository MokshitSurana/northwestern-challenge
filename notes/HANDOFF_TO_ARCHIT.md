# Handoff Note — Mokshit → Archit

**Date:** May 20, 2026
**Where we are:** End of week 1. Infrastructure done, anchor finding drafted, ready for Track 2 and skill packaging.

---

## TL;DR

Read `README.md` first (full project overview). Then read `notes/05_finding_bridenstine.md` (the anchor finding). Then come back here for what's next.

Three weeks until July 15. Plenty of runway, but the work compounds — don't sit on it.

---

## What's done

- ETL pipeline (`scripts/01_build_index.py`) — fully working, all parser bugs found and fixed
- DuckDB analytical store (`output/investigation.duckdb`, 2.84 GB, 10 tables)
- Anchor finding written and Senate-side verified: The Artemis Group / Bridenstine case study
- House LDA data parsed correctly (was broken; took two rebuilds to fix)
- Cross-chamber reconciliation between Senate and House Artemis Group filings

## What's NOT done — your priorities, in order

### 1. Verify the finding holds against the corrected House data (URGENT, 1 hour)

The Bridenstine writeup was finalized **before** the most recent House parser fix landed. The numbers might shift slightly. Specifically:

- Re-run `notebooks/05d_house_crossval.py` — confirm the 115 House filings and 125 Bridenstine row counts still match
- Re-run `notebooks/05c_verification_round_2.py` — confirm Section 4's "top twelve NASA-targeting lobbyists" table is still accurate when you query the _combined_ Senate + House data
- Open `notes/05_finding_bridenstine.md` and update any numbers that have drifted

If any claim shifts materially (e.g., a top-12 lobbyist now ranks at top-15), tighten the language. Don't preserve a number for narrative convenience.

### 2. Save all conversation traces to `traces/` (30 min)

Competition requires full logs of model sessions. I've been having long Claude conversations through the entire build. We need to capture them:

- Open `traces/`
- For every Claude.ai chat we've had on this project, hit the "share" button and save the URL, OR copy the conversation to a markdown file
- Name them `trace_NN_short_description.md` (e.g., `trace_01_setup_and_data_exploration.md`)
- I'll send you the ones I have. Save them all.

This is annoying but critical. Without it we cap at 1/3 on every scoring dimension.

### 3. Start Track 2 — the structural pattern query (2-4 days)

This is the big one. The Bridenstine case is one example; the actual journalism is "how many other former agency heads run firms like this?"

**The question:** Identify every lobbyist in the corpus whose `covered_position` indicates they held a senior role at a federal agency, who now lobbies that same agency.

**Why this needs more than SQL:**

- "Administrator, NASA" in covered_position → "Natl Aeronautics & Space Administration (NASA)" in gov_entities. The strings don't match.
- "Deputy Secretary, Treasury" → "Treasury, Dept of (TREAS)". Also doesn't match.
- This is an entity-resolution problem that the entity-resolver skill (Skill 2) needs to solve.

**Suggested approach:**

1. **Build the agency-name lookup table first.** Pull all distinct `entity_name` values from `senate_gov_entities`. Manually (or with Claude's help) map common variants to canonical names: NASA, FDA, FCC, SEC, EPA, Treasury, etc. This becomes a reference asset for the skill.

2. **Pattern-match senior roles in covered_position.** Regex/keyword for: "Administrator", "Commissioner", "Secretary", "Deputy Secretary", "Under Secretary", "Director", "General Counsel", "Chief of Staff", "Chairman/Chairwoman/Chair". Look for these followed by an agency name.

3. **Join the two.** For each candidate lobbyist:
    - Their inferred former-agency
    - Their NASA-style ratio: what % of their filings target that same agency?
    - Their firm and clients
4. **Rank.** Sort by some interestingness score (filing count × concentration × seniority of prior role).

5. **Eyeball the top 30.** Some will be false positives (e.g., intern who once worked at NASA). Filter manually. Pick the 5-8 strongest cases.

**Expected output:** A ranked CSV in `output/` and a draft `notes/06_structural_pattern_findings.md` describing 5-8 cases like Bridenstine across different agencies.

This is the FINDING for the competition. Bridenstine is the case study; the structural list is the original journalism.

### 4. Skill packaging (parallel with Track 2, 1-2 days)

The competition wants reusable Agent Skills. We have working code (`scripts/01_build_index.py`) but it's not packaged as a Skill yet.

Format required by competition (per `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview`):

skill/lda-corpus-indexer/
├── SKILL.md # YAML frontmatter + instructions to the agent
├── scripts/
│ ├── build_index.py
│ └── rebuild_house.py
├── references/
│ ├── senate_schema.md # what the Senate JSON looks like
│ ├── house_schema.md # what the House XML looks like
│ ├── known_quirks.md # parser gotchas (CRITICAL — see below)
│ └── joins.md # how to link Senate ↔ House ↔ press
└── assets/
└── example_filing.json # one sample record from each dataset

**`SKILL.md` must contain:**

- One-sentence description (what the skill does)
- When the skill is relevant (triggering conditions)
- Inputs (paths to raw LDA dumps)
- Outputs (Parquet + DuckDB)
- How to invoke it
- Common failure modes

**`references/known_quirks.md` is the most important file.** Document every parser bug we hit:

- Senate JSON: lobbyist names nested under `lobbyist.first_name`/`last_name`
- House XML: lobbyist names use `<lobbyistFirstName>` + `<lobbyistLastName>`, not `<lobbyistName>`
- House XML: two ALI schemas — modern (`<alis>/<ali_info>/<issueAreaCode>`) and legacy (`<alis>/<ali_Code>`)
- Polars schema inference bug — needs explicit `schema_overrides`
- House `senate_id` is firm-engagement-level, not filing-level
- `data/data/` nesting from zip extraction

This file is the highest-value piece of the skill — it's what saves future journalists from rediscovering bugs.

### 5. Reporter-facing review interface (1-2 days, your specialty)

The competition's third scoring dimension is "can a human verify the work." This is your lane.

We need a simple web UI (React/Next.js, your strength) that:

- Takes a finding (e.g., a row from the Track 2 output) and displays it with full provenance
- Shows the filing UUIDs, source files, raw text excerpts
- Lets a reporter click through to the underlying records
- For each entity-resolution match, shows the `match_method` (exact, fuzzy_high, fuzzy_low) so the reporter can audit ambiguous matches

Keep it minimal. Tailwind + a single Next.js page is fine. Doesn't need a backend — read JSON from the file system at build time.

This is the "extends what an agent can do" dimension. A skill that produces a verifiable interface ranks higher than one that just dumps a table.

---

## Things I tried and what I learned

- **Don't trust Polars schema inference on Parquet writes** — explicit `schema_overrides` everywhere
- **DuckDB `union_by_name=True`** papers over schema-mismatch issues, but if the first file has the wrong type, you're still stuck. Belt and suspenders: explicit schemas at write time.
- **The Senate JSON has lobbyist names nested under `lobbyist.first_name`/`last_name`**, not at the top level. Burned an hour figuring this out.
- **The House XML has TWO ALI schemas** depending on year. The legacy schema uses `<alis>/<ali_Code>` (flat); the modern schema uses `<alis>/<ali_info>/<issueAreaCode>` (nested). Parse both.
- **Bridenstine isn't named in House LDA filings the way I expected** — fixed by switching to `lobbyistFirstName`+`lobbyistLastName`. Without this fix the entire House revolving-door angle is broken.

Read the git log if you want the full timeline.

---

## Things to NOT do

- **Don't rebuild the indexer from scratch.** It works. Polish it for the skill submission, but the logic is correct.
- **Don't add new external data sources yet.** Congress.gov / FEC / FARA all sound useful but each one multiplies the reproducibility burden. Master what's in the corpus first.
- **Don't spend more than 2 days on the entity resolver.** It's a black hole. Build the eval set first, target F1 ≥ 0.92, stop when you hit it.
- **Don't write code without thinking about the trace.** Every interesting Claude call gets logged.

---

## Open questions (no answer needed yet)

1. Should `revolving-door-detector` and `cross-corpus-temporal-coupling` be one skill or two?
2. Do we add Congress.gov bill text as external enrichment? Increases reproducibility burden.
3. What's the cleanest format for `traces/` — raw JSON, rendered HTML, or markdown?

---

## When you're stuck

Use Claude Code, not Claude.ai chat, for any agentic exploration of the corpus. The competition specifically rewards Agent Skills used through Claude Code.

Daily 15-min sync. If something blocks you for >2 hours, ping me.

---

## What success looks like by July 1

- [ ] Track 2 produces a ranked list of 8-15 candidate Bridenstine-pattern cases
- [ ] At least 3 cases pass external verification (their LinkedIn / agency staff records confirm the prior role)
- [ ] Entity resolver skill produces ≥0.92 F1 on a labeled eval set of 500 pairs
- [ ] LDA-corpus-indexer skill is packaged with full SKILL.md + references
- [ ] Reporter review UI is functional for at least 2 case-study findings
- [ ] All trace files are saved
- [ ] README is current with all changes since today

Two weeks of buffer after that for polish, internal review, and submission prep.
