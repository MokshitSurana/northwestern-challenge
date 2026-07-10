---
name: revolving-door-detector
description: >
  Identifies former senior government officials who now lobby the exact federal
  agency they previously led, measuring an "agency concentration ratio" —
  the share of their firm's filings that target their former agency.
  Produces a ranked list of Bridenstine-pattern cases across 23 federal agencies,
  with journalism-ready sourcing to specific LDA filing records.
  Use this skill after running lda-corpus-indexer to build the DuckDB store.
license: MIT
compatibility: Requires Python 3.11+, uv, and duckdb. Run the lda-corpus-indexer skill first (reads output/investigation.duckdb).
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# revolving-door-detector

## What this skill does

Scans the Senate LDA `covered_position` field across 2.1M lobbyist records to
find former senior officials (Administrator, Commissioner, Secretary, Director,
Chairman, Deputy Secretary, Chief of Staff) at named federal agencies, then
measures what fraction of their current lobbying targets that same former agency.

The result is a ranked list of "Bridenstine-pattern" cases — named after The
Artemis Group / Jim Bridenstine case study (see `notes/05_finding_bridenstine.md`),
where a former NASA Administrator launched a lobbying firm that now directs 39% of
its filings at NASA.

**Why it's novel:** Prior revolving-door trackers (OpenSecrets, LegiStorm) identify
individual former officials. This skill measures the *structural concentration* of a
firm around its founding official's former agency — a pattern that requires the
LDA database to surface.

## Inputs

- `output/investigation.duckdb` — built by the `lda-corpus-indexer` skill
- No additional inputs required

## Outputs

| File | Description |
|------|-------------|
| `output/agency_concentration.csv` | Full ranked table, all candidates |
| `output/agency_concentration.md` | Human-readable findings, top N |
| `notes/06_structural_pattern_findings.md` | Journalism-ready draft with sourcing |

## Invocation

```bash
# Default run: top 40 results, concentration ≥ 20%, filings ≥ 10
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py

# Looser thresholds for broader coverage
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --min-filings 5 --min-conc 0.15

# Filter to a single agency
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --agency nasa
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --agency fda
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --agency epa

# Expand the output
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --top 100
```

## Agencies covered

23 agencies are currently in the registry:

| Code | Full name |
|------|-----------|
| nasa | Natl Aeronautics & Space Administration |
| epa | Environmental Protection Agency |
| fda | Food & Drug Administration |
| fcc | Federal Communications Commission |
| sec | Securities & Exchange Commission |
| ftc | Federal Trade Commission |
| dod | Defense, Dept of |
| treasury | Treasury, Dept of |
| hhs | Health & Human Services, Dept of |
| dhs | Homeland Security, Dept of |
| interior | Interior, Dept of |
| energy | Energy, Dept of |
| state | State, Dept of |
| dot | Transportation, Dept of |
| faa | Federal Aviation Administration |
| ferc | Federal Energy Regulatory Commission |
| cftc | Commodity Futures Trading Commission |
| cfpb | Consumer Financial Protection Bureau |
| usda | Agriculture, Dept of |
| va | Veterans Affairs, Dept of |
| sba | Small Business Administration |
| omb | Office of Management & Budget |
| ustr | U.S. Trade Representative |
| cms | Centers for Medicare and Medicaid |

## Scoring methodology

```
score = concentration × log(total_filings + 1) × seniority_score
```

- `concentration` = agency_filings / total_filings
- `seniority_score` = 5 for Administrator/Secretary/Commissioner, 4 for Deputy
- Higher score = more Bridenstine-like (concentrated AND high-volume AND senior prior role)

This rewards cases where the pattern is both statistically strong (high concentration)
and journalistically significant (many filings, senior prior role).

## Interpreting results

**High-confidence findings:** lobbyist_name matches a public figure with a
documented prior role at the named agency, and the concentration ratio is ≥ 30%
with ≥ 20 total filings.

**Requires verification:** `covered_position` is a free-text self-disclosure.
Lobbyists occasionally misstate or embellish prior roles. Always confirm:
1. The prior role via an authoritative source (agency staff directory, news archives)
2. The cooling-off period status (18 USC §207, typically 1-year bar)
3. Active contracts between the firm's clients and the former agency (USAspending.gov)

## Data limitations

- **Senate LDA only.** The concentration is computed from Senate filings.
  House LDA is not yet included. Adding House data would change rankings.
- **covered_position is self-reported.** Lobbyists fill it in voluntarily.
  Many former officials have no covered_position, so the scan misses them.
- **Entity matching uses ILIKE.** The agency registry uses string fragments,
  not the full entity-resolver pipeline. Upgrade to entity-resolver skill
  for higher precision.
- **Income figures are firm-level.** The `total_income` is the registrant's
  disclosed revenue across all clients, not personal lobbyist compensation.

## Anchor finding

The Artemis Group / Jim Bridenstine case is documented in
`notes/05_finding_bridenstine.md`. It scores highly on this skill:
- Agency: NASA
- Concentration: 39.1% (52/133 Senate filings)
- Firm: The Artemis Group, LLC
- Prior role: Administrator, NASA (highest possible seniority score)

Run `uv run skills/revolving-door-detector/scripts/03_agency_concentration.py --agency nasa` to reproduce
this finding and find comparable cases.
