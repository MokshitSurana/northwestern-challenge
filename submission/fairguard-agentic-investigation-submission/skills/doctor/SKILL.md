---
name: doctor
description: >
  Cross-platform setup validator for FairGuard. Checks Python 3.11+, uv,
  Node.js, npm, project dependencies, raw LDA data presence, and the
  optional pre-built investigation.duckdb. Prints a pass/fail checklist plus
  a recommended next action ("ready to scan", "run index", "download pre-built").
  Run this first on a fresh clone or new machine.
license: MIT
compatibility: Runs on Linux, macOS, and Windows. Requires Python 3.11+ and uv; also checks for Node.js and npm.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# doctor

## Instructions for the agent

Run the doctor script and surface its output verbatim to the user. The
script is self-contained and outputs a final "Next action:" line — pass
that recommendation through to the user without modification.

```bash
uv run skills/doctor/scripts/doctor.py
```

If the user asks for a machine-readable form (for piping into another tool):

```bash
uv run skills/doctor/scripts/doctor.py --json
```

If the user wants only failures and warnings (shorter output):

```bash
uv run skills/doctor/scripts/doctor.py --quiet
```

## Behavior

The script exits with code 1 only if a REQUIRED check fails (Python < 3.11,
uv not installed, dependencies not installed). Missing raw data and missing
pre-built DB are warnings — the user is expected to choose between building
or downloading.

## What it checks

| # | Check | Required? |
|---|-------|-----------|
| 1 | Python ≥ 3.11 | yes |
| 2 | `uv` on PATH | yes |
| 3 | Node.js on PATH | no (only for web UI) |
| 4 | npm on PATH | no (only for web UI) |
| 5 | `.venv` exists with duckdb/polars/rapidfuzz importable | yes |
| 6 | `web/node_modules` present | no |
| 7 | `data/senate/`, `data/house/`, `data/congress_press/` | no (alternative: pre-built DB) |
| 8 | `output/investigation.duckdb` opens and has senate_filings rows | no |

For each check, the output is one line: `[PASS|WARN|FAIL]  <check name>: <detail>`.
Failing checks include a `→ <suggested fix>` line.

The script also detects the common `data/data/` extraction-nesting case and
suggests setting `DATA_ROOT=data/data`.

## Next-action routing

After all checks, the script prints exactly one of:

- `Install Python 3.11+ before continuing.`
- `Install uv: <link>`
- `Run:  uv sync`
- `Setup is ready. You can run:  /fair-guard scan` — when the pre-built DB
  is present and opens cleanly.
- `Raw data found. Build the DB:  /fair-guard index` — when raw data is
  present but no DB is built.
- A two-option block (download pre-built output OR download raw data + index)
  — when neither raw data nor a DB is present.

## Why a Python script (not bash + PowerShell)

The previous version of this skill mixed `ls`, `head`, and `2>/dev/null`
(bash) with `Get-ChildItem`, `Test-Path` (PowerShell). That meant the agent
had to interpret which branch to run per platform — fragile, and it broke
on Windows. The current version is one Python script that runs the same way
everywhere, so the SKILL.md is short and unambiguous.

## Reproducibility note

The script is deterministic on a given machine and has no side effects (it
only reads files and runs `--version` commands). It is safe to run any
number of times.
