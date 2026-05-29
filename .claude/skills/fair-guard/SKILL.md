---
name: fair-guard
description: >
  FairGuard investigative journalism toolkit for federal lobbying analysis.
  Routes to: doctor (validate setup and guided onboarding), index (build DuckDB
  from raw LDA dumps), resolve (normalize org/person names), or scan (find former
  officials lobbying their old agency). Use when the user wants to run any part
  of the FairGuard pipeline.
argument-hint: "[mode: doctor | index | scan | resolve]"
allowed-tools: Read Bash
---

# FairGuard — dispatcher

## Available modes

| Mode | Full skill name | Purpose | Prerequisite |
|------|----------------|---------|-------------|
| `doctor` | setup-validator | Check all deps and data; guided onboarding | None — always safe |
| `index` | lda-corpus-indexer | Parse raw LDA data → `output/investigation.duckdb` | Raw data in `data/` |
| `resolve` | entity-resolver | Normalize org/person name strings for clean joins | DuckDB built |
| `scan` | revolving-door-detector | Rank former officials by agency concentration ratio | DuckDB built |

## Invocation examples

```
/fair-guard doctor                  # validate setup, guided onboarding
/fair-guard index                   # build the database (full corpus, ~2.5 hr)
/fair-guard scan                    # find revolving-door patterns (all agencies)
/fair-guard scan --agency nasa      # filter to NASA only
/fair-guard resolve                 # normalize entity names
```

## Prerequisite: output/investigation.duckdb

`scan` and `resolve` both require `output/investigation.duckdb`.

**Two ways to get it — choose one:**

**Option A — Download pre-built (~10 min, recommended for evaluation):**
Download the pre-built `output/` folder from Google Drive:
https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing
Unzip and place the `output/` folder at the project root.
You can then run `/fair-guard scan` immediately — no 2.5 hr build required.

**Option B — Build from raw data (~2.5 hr):**
Run `/fair-guard doctor` to validate your environment, then `/fair-guard index`.

## Routing instructions

When invoked with `$ARGUMENTS`:

1. **No argument:** Print the mode table above and ask which mode to run.

2. **Valid mode name** (`doctor`, `index`, `resolve`, `scan`):

   First, check prerequisites deterministically:
   - `scan` or `resolve`: check whether `output/investigation.duckdb` exists.
     If it does **not** exist, stop immediately and print both options above
     (Drive download or run `/fair-guard index`). Do not proceed.
   - `index`: check whether `data/senate/`, `data/house/`, and
     `data/congress_press/` exist. If missing, print both options and stop.
   - `doctor`: no prerequisites — always proceed.

   Then read the corresponding skill file and follow its instructions exactly:
   - `doctor`  → read `skill/doctor/SKILL.md`
   - `index`   → read `skill/lda-corpus-indexer/SKILL.md`
   - `resolve` → read `skill/entity-resolver/SKILL.md`
   - `scan`    → read `skill/revolving-door-detector/SKILL.md`

3. **Invalid mode name:** Suggest the closest valid mode and ask for confirmation
   before proceeding.

4. **Extra arguments after the mode name** (e.g. `scan --agency nasa`):
   Strip the mode name, pass the remainder to the mode's invocation commands.

After reading the mode's SKILL.md, execute its instructions in full.
Do not summarize or skip steps.
If the mode body contains `Status: Planned`, report that and stop.
