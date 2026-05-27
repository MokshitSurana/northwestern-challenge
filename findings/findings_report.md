# FairGuard — Findings Report

**Team:** FairGuard (Mokshit Surana, Archit Rathod)
**Competition:** Northwestern GAIN Agentic AI Investigative Journalism Challenge
**Deadline:** July 15, 2026
**Status:** In progress — this document will become the PDF findings report

---

> **Instructions for final submission:**
> Convert this file to PDF using Pandoc or a Markdown → PDF tool:
> ```bash
> pandoc findings/findings_report.md -o findings/findings_report.pdf \
>     --pdf-engine=weasyprint \
>     --variable margin-top=1in --variable margin-bottom=1in
> ```
> Or export from a tool like Notion, Obsidian, or Typora.

---

## Executive Summary

*(To be written after Track 2 analysis is complete.)*

FairGuard's investigation of the 2022-2026 federal lobbying disclosure corpus
identifies a structural pattern in the revolving door between government
agencies and private lobbying firms. Using a novel "agency concentration ratio"
metric — the share of a firm's Senate LDA filings that target the agency its
founding lobbyist previously led — we surface cases where former senior
officials have built lobbying practices specifically around their former agencies.

**Anchor finding:** The Artemis Group, LLC, founded by former NASA Administrator
Jim Bridenstine in Q4 2024, directs 39.1% of its filings at NASA — the highest
concentration of any third-party lobbying firm with significant volume. Five of
the top twelve most-active NASA-targeting lobbyists in the Senate corpus are
Artemis Group employees, four of whom worked directly under Bridenstine.

**Structural finding:** *(Results from `scripts/03_agency_concentration.py` —
to be inserted after Track 2 run is complete.)*

---

## Finding 1: The Artemis Group — Anchor Case Study

*(Full text in `notes/05_finding_bridenstine.md` — insert here for final report.)*

### Key claims (sourced to `output/investigation.duckdb`)

- 133 Senate LDA filings by The Artemis Group, 52 targeting NASA (39.1%)
- 115 House LDA filings for the same firm
- 5 of the top 12 most-active NASA-targeting lobbyists in the 2024-2026
  Senate corpus work at this single firm
- 4 of those 5 held positions in Bridenstine's congressional or NASA offices

### Verification status

See `notes/05_finding_bridenstine.md §2.5` for item-by-item verification status.

---

## Finding 2: Structural Pattern — Former Agency Heads Across Agencies

*(To be completed after `uv run scripts/03_agency_concentration.py` is run.
Results will be in `output/agency_concentration.md` and
`notes/06_structural_pattern_findings.md`.)*

**Expected contents:**
- Methodology: how the agency concentration ratio is computed
- Top 8-15 cases across different agencies
- Comparison to the Artemis Group baseline
- Verification checklist for each case

---

## Methodology

### Data sources

| Source | Coverage | Format | Rows |
|--------|----------|--------|------|
| Senate LDA filings | 2022-Q1 2026 | JSON | 418,170 |
| House LDA filings | 2022-Q1 2026 | XML | 409,640 |
| Congressional press releases | 2022-Q1 2026 | JSONL | 141,332 |

All sourced from the Northwestern GAIN challenge corpus download.

### ETL pipeline

Raw data → `scripts/01_build_index.py` → Parquet intermediate files →
`output/investigation.duckdb` (2.92 GB, 10 tables). See
`skill/lda-corpus-indexer/SKILL.md` for full documentation.

### Agency concentration analysis

`scripts/03_agency_concentration.py` — see `skill/revolving-door-detector/SKILL.md`
for methodology documentation.

---

## Outside Data Used

| Source | Used for | Effect on findings |
|--------|----------|--------------------|
| NASA biography (nasa.gov) | Bridenstine tenure dates | Confirms 2018-2021 role |
| Payload Space (May 2026) | Bridenstine → Quantum Space CEO | Extends the revolving-door arc |
| SpaceX public statement (Oct 2025) | Public conflict-of-interest context | Framing only, no new data |
| LegiStorm | Mark Piland prior role | Supplementary sourcing |
| ZoomInfo (Kathryn Wall) | Prior role at National Space Council | Low-confidence, needs verification |

---

## Conflicts of Interest

Neither team member (Mokshit Surana, Archit Rathod) has any financial
relationship with The Artemis Group, Jim Bridenstine, or any of the
organizations named as clients in the findings.

---

## Legal Flags

No legal violations are alleged. The Bridenstine cooling-off period
(1-year bar on lobbying former agency) expired in January 2022, nearly
3 years before his first lobbying registration in Q4 2024.

If findings from Track 2 suggest a cooling-off violation (first lobbying
registration within 12 months of leaving a senior agency role), that will
be flagged here for the evaluation panel.

---

## Skill Index

| Skill | Status | Key script | What it does |
|-------|--------|------------|--------------|
| lda-corpus-indexer | ✅ Complete | scripts/01_build_index.py | ETL: raw → DuckDB |
| entity-resolver | 🚧 Planned | scripts/ (TBD) | Normalize org/person names |
| revolving-door-detector | ✅ Complete | scripts/03_agency_concentration.py | Find Bridenstine-pattern cases |

---

## Trace Index

| File | Description |
|------|-------------|
| traces/trace_01_setup_and_data_exploration.md | Initial setup, data download, first queries |
| traces/trace_02_parser_debugging.md | Senate JSON lobbyist name bug, House XML ALI schema |
| *(additional traces from Mokshit to be added)* | |
