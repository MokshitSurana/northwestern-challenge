---
name: fair-guard
description: >
  FairGuard investigative journalism toolkit for federal lobbying analysis.
  Routes to: doctor (validate setup and guided onboarding), index (build DuckDB
  from raw LDA dumps), resolve (normalize org/person names), scan (find former
  officials lobbying their old agency), trace (follow the money — federal awards
  from an agency to a lobbyist's clients on USAspending.gov), pressrel
  (cross-reference Congressional press releases for mentions of a client / firm /
  topic — pairs with scan and trace to turn the structural pattern into a story
  with named legislators in it), or coi (compose the outputs of scan, trace, and
  pressrel into a conflict-of-interest graph that surfaces triangles, hubs, and
  bridges across all the other skills). Use when the user wants to run any part
  of the FairGuard pipeline.
argument-hint: "[mode: doctor | index | scan | resolve | trace | pressrel | coi]"
allowed-tools: Read Bash
---

# FairGuard — dispatcher

## Available modes

| Mode | Full skill name | Purpose | Prerequisite |
|------|----------------|---------|-------------|
| `doctor` | setup-validator | Cross-platform setup check + next-action routing | None — always safe |
| `index` | lda-corpus-indexer | Parse raw LDA data → `output/investigation.duckdb` (+ verify) | Raw data in `data/` |
| `resolve` | entity-resolver | Normalize org/person name strings; write `entity_map` (F1 = 0.963) | DuckDB built |
| `scan` | revolving-door-detector | Rank former officials by agency concentration ratio | DuckDB built |
| `trace` | federal-award-tracer | Follow the money: agency → lobbyist's clients on USAspending.gov | Network + a case file |
| `pressrel` | press-release-cross-ref | Cross-reference Congressional press releases for mentions of a client / firm / topic | DuckDB built |
| `coi` | coi-graph | Compose scan + trace + pressrel into a conflict-of-interest graph; surface triangles, hubs, bridges | findings.json (run scan first) |

## Invocation examples

```
/fair-guard doctor                  # validate setup, guided onboarding
/fair-guard index                   # build the database (full corpus, ~2.5 hr)
/fair-guard scan                    # find revolving-door patterns (all agencies)
/fair-guard scan --agency nasa      # filter to NASA only
/fair-guard resolve                 # normalize entity names
/fair-guard trace                   # follow the money (lists bundled case files)
/fair-guard pressrel                # cross-ref press releases (lists bundled case files)
/fair-guard coi                     # build the conflict-of-interest graph from existing findings
```

## Prerequisite: output/investigation.duckdb

`scan`, `resolve`, and `pressrel` all require `output/investigation.duckdb`.

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

2. **Valid mode name** (`doctor`, `index`, `resolve`, `scan`, `trace`, `pressrel`, `coi`):

   First, check prerequisites deterministically:
   - `scan`, `resolve`, or `pressrel`: check whether `output/investigation.duckdb`
     exists. If it does **not** exist, stop immediately and print both options
     above (Drive download or run `/fair-guard index`). Do not proceed.
   - `coi`: check whether `web/public/findings.json` exists. If it does not,
     stop and tell the user to run `/fair-guard scan` first. coi reads only
     the on-disk JSON outputs of scan / trace / pressrel — no DB, no network.
   - `index`: check whether `data/senate/`, `data/house/`, and
     `data/congress_press/` exist. If missing, print both options and stop.
   - `trace`: does **not** need the DuckDB — it makes live calls to
     api.usaspending.gov and takes a case file. If no case file is named in the
     arguments, point the user at the bundled cases in
     `skill/federal-award-tracer/cases/` and at `--print-template` to author a new
     one. Do not require `output/investigation.duckdb`.
   - `doctor`: no prerequisites — always proceed.

   Then read the corresponding skill file and follow its instructions exactly:
   - `doctor`   → read `skill/doctor/SKILL.md`                   (runs `scripts/doctor.py`)
   - `index`    → read `skill/lda-corpus-indexer/SKILL.md`       (runs `scripts/01_build_index.py`; verify with `scripts/verify_build.py`)
   - `resolve`  → read `skill/entity-resolver/SKILL.md`          (runs `scripts/02_entity_resolver.py`)
   - `scan`     → read `skill/revolving-door-detector/SKILL.md`  (runs `scripts/03_agency_concentration.py`)
   - `trace`    → read `skill/federal-award-tracer/SKILL.md`     (runs `scripts/04_award_tracer.py`)
   - `pressrel` → read `skill/press-release-cross-ref/SKILL.md`  (runs `scripts/05_pressrel_search.py`)
   - `coi`      → read `skill/coi-graph/SKILL.md`                (runs `scripts/06_coi_graph.py`)

   For `pressrel` with no further arguments: point the user at the bundled cases
   in `skill/press-release-cross-ref/cases/` (steinberg_clients.json,
   limbaugh_clients.json), at `--mention "<term>"` for ad-hoc search, and at
   `--enrich-findings` for the one-shot pass that attaches press-release
   evidence to every top scan finding.

3. **Invalid mode name:** Suggest the closest valid mode and ask for confirmation
   before proceeding.

4. **Extra arguments after the mode name** (e.g. `scan --agency nasa`):
   Strip the mode name, pass the remainder to the mode's invocation commands.

After reading the mode's SKILL.md, execute its instructions in full.
Do not summarize or skip steps.

All seven modes are currently shipped; there is no `Status: Planned` skill to
guard against. `trace` follows the money from an agency to a lobbyist's clients
on USAspending.gov and reproduces the verified trails in
`notes/08_external_verification_top_candidates.md`. `pressrel` closes the third
side of the triangle: which members of Congress have publicly mentioned the
companies surfaced by `scan` and `trace`.
