# Skill Packaging Plan

_Written while 01_build_index.py is running its full build._

---

## The 3 Skills We're Submitting

The competition wants **reusable skills** — tools another journalist could lift into a completely different investigation. Below are the three we're building, ordered by dependency.

---

### Skill 1 — `lda-corpus-indexer`

**One sentence:** Converts raw LDA lobbying disclosure dumps (Senate JSON + House XML) into a flat, queryable DuckDB analytical store with provenance preserved on every row.

| | Detail |
|---|---|
| **Input** | `data/senate/` (JSON arrays), `data/house/` (XML files), `data/congress_press/` (JSONL) |
| **Output** | `output/parquet/*.parquet` per chunk + `output/investigation.duckdb` |
| **Key script** | `scripts/01_build_index.py` |
| **Reuse scenario** | Any journalist receiving a bulk LDA data export (Senate/House both publish quarterly) can run this to get a queryable DB in ~1 hour instead of spending days wrangling XML |

**What makes it a skill, not just a script:**
- `DATA_ROOT` / `OUTPUT_ROOT` env vars make it path-agnostic
- `--sample` flag for fast validation on new data
- Writes Parquet first (intermediate deliverable) then DuckDB (analytical layer)
- Every row has `source_path` — every finding traces back to a specific file

---

### Skill 2 — `entity-resolver`

**One sentence:** Normalizes and clusters messy organization/person name strings across datasets so that "MICROSOFT CORP", "Microsoft Corporation", and "Microsoft Corp." resolve to a single canonical entity — with the original strings preserved for audit.

| | Detail |
|---|---|
| **Input** | A DuckDB/Parquet table with a raw name column + entity type |
| **Output** | `entity_map` table: `(raw_name, canonical_name, cluster_id, confidence, match_method)` |
| **Key script** | `scripts/02_entity_resolver.py` _(to be built)_ |
| **Reuse scenario** | Any messy government dataset with org names — FARA filings, FEC donors, state contractor lists, hospital ownership records |

**Algorithm (planned):**
1. Normalize: lowercase, strip punctuation, remove legal suffixes (LLC, Inc., Corp., L.P., etc.)
2. Block by first token (avoids O(n²) comparisons across 50K names)
3. Within each block: `rapidfuzz.token_sort_ratio` — threshold ~88
4. Cluster with union-find; pick most frequent variant as canonical
5. Output `match_method` column: `"exact"`, `"fuzzy"`, or `"manual"` — so a reporter can quickly audit low-confidence matches

**Why this is the prerequisite:**
- Revolving door analysis: "John Smith" ≠ "Smith, John J." across years
- Say-vs-pay: client names in Senate filings ≠ company names in press releases

---

### Skill 3 — `say-vs-pay-investigator`

**One sentence:** Cross-references what members of Congress say publicly (press release topics by quarter) with who is paying to lobby their chamber on the same issues, surfacing members where public rhetoric and private lobbying pressure diverge most.

| | Detail |
|---|---|
| **Input** | `investigation.duckdb` (built by Skill 1) + `entity_map` (built by Skill 2) |
| **Output** | Ranked findings report: member × issue × quarter with spend, press release count, and divergence score |
| **Key scripts** | `scripts/03_say_vs_pay.py`, `scripts/04_revolving_door.py` _(to be built)_ |
| **Reuse scenario** | Any corpus pairing public statements with private financial activity — state legislatures, city councils, regulatory comment periods vs. lobbying on the same rule |

**Composition note:** This skill calls the output of skills 1 and 2. The SKILL.md will make that dependency explicit with a `requires:` section.

---

## How the Skills Compose

```
Raw data (8 GB)
    │
    ▼
[Skill 1: lda-corpus-indexer]
    │
    ▼
investigation.duckdb + Parquet files
    │
    ▼
[Skill 2: entity-resolver]
    │
    ▼
entity_map table (canonical org/person names)
    │
    ▼
[Skill 3: say-vs-pay-investigator]
    │
    ▼
findings_report.md  ←  every claim cites a filing_uuid or press URL
```

A journalist with a new lobbying corpus can run skills 1 + 2 alone and get a clean, queryable DB with resolved entities — without ever touching skill 3. That's the "lift into a different investigation" moment.

---

## Open Questions / Decisions

- [ ] **Skill 2 threshold**: 88 is a starting guess for fuzzy match threshold. Need to tune against a labeled sample of Senate+House name pairs after the full build.
- [ ] **Skill 3 topic detection**: Press releases don't have ALI codes. We need a keyword→topic mapping (e.g., "insulin", "prescription", "Medicare" → `HCR`). Options: (a) simple keyword list, (b) zero-shot classification with a small LLM. Decide after looking at actual press release text.
- [ ] **Provenance UI (Archit's lane)**: How does a reporter verify a finding? The skill should output something human-readable — probably a per-finding exhibit with: the specific filing UUID + link, the press release URL + date, and the specific text excerpt. Format TBD.
- [ ] **Number of submitted skills**: We could split skill 3 into `revolving-door` + `say-vs-pay` as two separate skills that both depend on skills 1+2. That gives us 4 skills, which might score better on the "novel capabilities" dimension. Revisit after the build.
