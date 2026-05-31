---
name: doctor
description: >
  Cross-platform setup validator for FairGuard. Checks Python 3.11+, uv,
  Node.js, npm, project dependencies, raw LDA data presence, and the
  optional pre-built investigation.duckdb. Prints a pass/fail checklist plus
  a recommended next action. Run first on a fresh clone or new machine.
license: MIT
compatibility: Linux, macOS, Windows — single Python script, no shell-specific logic.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  status: shipped
  part-of: fair-guard
  tools: bash, python
---

# doctor

## Instructions for the agent

Run the doctor script and surface its output verbatim. The script is
self-contained and outputs a final "Next action:" line — pass that through
to the user without modification.

```bash
uv run scripts/doctor.py
```

Options:

```bash
uv run scripts/doctor.py --quiet   # hide passing checks
uv run scripts/doctor.py --json    # machine-readable
```

## Behavior

Exit code 1 only if a REQUIRED check fails (Python < 3.11, uv not installed,
deps not importable). Missing raw data and missing pre-built DB are warnings
— the script prints two recovery options (download pre-built `output/` from
Drive, or download raw data and run `/fair-guard index`).

## What it checks

| # | Check | Required? |
|---|-------|-----------|
| 1 | Python ≥ 3.11 | yes |
| 2 | uv on PATH | yes |
| 3 | Node.js on PATH | no |
| 4 | npm on PATH | no |
| 5 | .venv + duckdb/polars/rapidfuzz importable | yes |
| 6 | web/node_modules present | no |
| 7 | data/senate/, data/house/, data/congress_press/ | no |
| 8 | output/investigation.duckdb opens & contains senate_filings rows | no |

It detects the common `data/data/` extraction-nesting case and recommends
setting `DATA_ROOT=data/data`.

## Why a Python script

The previous version mixed bash and PowerShell, requiring agent-level
branching per platform. This version is one Python file that runs the same
way on Linux, macOS, and Windows. The skill instructions are correspondingly
short.

Full submission artifact: `skill/doctor/SKILL.md`.
