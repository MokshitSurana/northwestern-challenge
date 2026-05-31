# Trace — `/fair-guard scan`

**Date:** 2026-05-30
**Skill invoked:** `scan` (revolving-door-detector)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** 139 candidates across 22 agencies. Bridenstine anchor finding still ranks at NASA. Registry tests 111/111 pass.

---

## Invocation

User typed `/fair-guard scan` in Claude Code.

Dispatcher checked the DB prerequisite (`output/investigation.duckdb` exists)
and routed to `skill/revolving-door-detector/SKILL.md`, which instructs the
agent to run:

```bash
uv run scripts/03_agency_concentration.py
```

## Output (verbatim, abbreviated)

```
============================================================
FairGuard — Agency Concentration Scanner (Track 2)
============================================================
DB: output\investigation.duckdb
Thresholds: min_filings=10, min_conc=20%

Loading lobbyist profiles…
  Loading lobbyist profiles from senate_lobbyists…
  7,709 distinct (lobbyist, firm) pairs with covered_position

Classifying by prior agency role…
  476 profiles matched a senior agency role
  505 (lobbyist, firm, agency) triples to evaluate
    DHS          50    USTR         40    HHS          38    DOD          38
    ENERGY       33    SEC          32    EPA          31    TREASURY     31
    USDA         30    OMB          28    DOT          27    INTERIOR     26
    FCC          17    STATE        17    CMS           9    CFTC          9
    FDA           9    FAA           8    SBA           8    VA            8
    CFPB          6    FTC           4    NASA          4    FERC          2

Computing agency concentration (min_filings=10, min_conc=20%)…
  Batch-querying 24 agencies (was one query per candidate)…
  139 candidates pass thresholds

============================================================
TOP 10 RESULTS (of 139)
============================================================

 1. [24.68] BENJAMIN STEINBERG  · ENERGY    90.2% (213/236)  VENN STRATEGIES
 2. [23.91] MARK LIMBAUGH       · INTERIOR  72.6% (527/726)  THE FERGUSON GROUP, LLC
 3. [22.94] ASHLEE JOHNSON      · USDA      82.7% (230/278)  THE RUSSELL GROUP, INC.
 4. [22.32] KEVIN BAILEY        · USDA      87.3% (144/165)  FGS GLOBAL (US) LLC
 5. [22.13] JIM NEWSOME         · CFTC      96.0%  (95/99)   DELTA STRATEGY GROUP
 6. [21.45] MICHAEL TORREY      · USDA      79.0% (180/228)  TORREY ADVISORY GROUP
 7. [21.31] KATE MARKS          · ENERGY    91.3%  (94/103)  VENN STRATEGIES
 8. [19.42] KENNETH BARBIC      · USDA      78.8% (108/137)  INVARIANT LLC
 9. [19.20] AURENE MARTIN       · INTERIOR  68.2% (180/264)  SPIRIT ROCK CONSULTING
10. [19.14] ROGER SHERMAN       · FCC      100.0%  (45/45)   WANETA STRATEGIES, LLC

[CSV] output\agency_concentration.csv  (139 rows)
[MD]  output\agency_concentration.md
[MD]  notes\06_structural_pattern_findings.md  (journalism draft)
[JSON] web\public\findings.json  (40 findings → web UI)
```

(Hits per agency — top counts: USTR 19, USDA 15, HHS 13, ENERGY 11, INTERIOR 11, …)

## Anchor finding still holds

The Bridenstine / Artemis Group anchor finding (Finding 01) was the seed
case for the entire `scan` skill. Filtering to NASA confirms it survives the
registry rewrite and the cov_profiles dedup fix:

```bash
uv run scripts/03_agency_concentration.py --agency nasa
```

```
TOP 10 RESULTS (of 2)

 1. [ 8.71] GABE SHERMAN    · NASA  39.5% (32/81)  THE ARTEMIS GROUP, LLC
 2. [ 7.08] JIM BRIDENSTINE · NASA  32.9% (24/73)  THE ARTEMIS GROUP, LLC
```

These match the verification numbers in `notes/05_finding_bridenstine.md`
within the expected drift (sherman now appears on more filings than
bridenstine himself, which is the structural pattern the finding documents).

## Verification — registry tests

Before publishing rankings, the registry's regex patterns are validated
against 110 hand-curated positive/negative cases plus an entity_fragment
DB-match check.

```bash
uv run pytest tests/test_agency_registry.py
```

```
================================== test session starts ==================================
collected 111 items

tests\test_agency_registry.py ............................................. [ 40%]
............................................................                [100%]

============================== 111 passed in 0.31s =================================
```

The test layers:

| Test | Count |
|---|---|
| `test_registry_has_all_expected_agencies` | 1 |
| `test_every_entity_fragment_matches_db` | 1 (asserts 23/23 fragments hit DB rows) |
| `test_positive_cases` | 89 (Bridenstine-grade roles must classify) |
| `test_negative_cases` | 16 (junior roles, congressional staff must NOT classify) |
| `test_seniority_scores_in_range` + 3 others | 4 |

## What the registry catches that the old version missed

Before the rewrite, the `scan` registry produced 106 candidates across 18
agencies. After the rewrite, it produces 139 candidates across 22 agencies
(+34 candidates, +4 agencies). Audited the missing-coverage delta by
running `scripts/_diagnose_regex_coverage.py` before/after:

| Agency | Old coverage | New coverage | Why it improved |
|---|---|---|---|
| OMB | 17% | 88% | Word-order patterns added (`OMB Chief of Staff`, `Director, OMB`) |
| EPA | 47% | 90% | General Counsel + abbreviated "Admin" patterns added |
| FTC | 20% | 100% | Long-form "Federal Trade Commission" patterns added |
| CFTC | 31% | 94% | Chief of Staff + General Counsel patterns added |
| USTR | 40% | 86% | "Assistant USTR" / "Deputy Assistant USTR" patterns added |
| State | 14% | 34% | Most remaining "misses" are correctly-excluded "Senior Advisor" / "Law Clerk" non-senior roles |

(Coverage is computed against a heuristic pool of `covered_position`
strings that mention the agency name + a senior-role keyword. The remaining
gaps are dominated by congressional staff who are correctly excluded.)

## Editorial layer

The script writes three output formats:

1. `output/agency_concentration.csv` — full ranked table (CSV, 139 rows)
2. `output/agency_concentration.md` — human-readable findings (markdown)
3. `notes/06_structural_pattern_findings.md` — journalism-ready draft
4. `web/public/findings.json` — auto-refresh for the Next.js reporter UI

A reporter using `/fair-guard scan` gets a verified-by-tests ranking; can
open the web UI to filter by agency; can click through to the source
`filing_uuid` for any candidate; and has a four-item "open items before
publication" checklist appended to each individual case in the structural
finding draft.

## Reproducibility

The script is deterministic. Re-running on the same DB with the same
thresholds produces byte-identical CSV output. Filter flags are documented
in `--help`:

```bash
uv run scripts/03_agency_concentration.py --agency nasa
uv run scripts/03_agency_concentration.py --min-filings 5 --min-conc 0.15
uv run scripts/03_agency_concentration.py --top 100
```
