---
name: doctor
description: >
  Setup validator for FairGuard. Checks all system dependencies (Python 3.11+,
  uv, Node.js, npm), verifies the Python and web environments, confirms raw LDA
  data directories are present, and prints a pass/fail checklist. On a clean pass,
  offers to invoke lda-corpus-indexer to build the analytical database.
  Run before any other fair-guard mode on a fresh clone or new machine.
license: MIT
compatibility: Works on Linux, macOS, and Windows (PowerShell). Requires Bash or PowerShell.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "0.1.0"
  part-of: fair-guard
  tools: bash
---

# doctor

Setup validator for FairGuard. Runs a pass/fail checklist, then optionally
launches the `index` mode to build the analytical database.

## Instructions

Execute each check below using Bash (or PowerShell on Windows). Print each
result as it completes, then print the full formatted summary at the end.

---

## Step 1 — System dependencies

```bash
python --version 2>&1 || python3 --version 2>&1
uv --version 2>&1
node --version 2>&1
npm --version 2>&1
```

**Pass conditions:**
- Python: version string contains `3.11`, `3.12`, `3.13`, or higher
- uv / node / npm: any output not containing "not found", "not recognized", or "cannot be loaded"

---

## Step 2 — Project Python environment

```bash
uv sync
```

Pass: exits 0, `.venv/` is created or already present. This is idempotent.

---

## Step 3 — Web dependencies

```bash
cd web && npm ci
```

Pass: exits 0. (`npm ci` is used — not `npm install` — to reproduce the locked dependency tree.)

---

## Step 4 — Raw data presence

Check whether the LDA corpus is present:

```bash
# Linux / macOS
ls data/senate/ 2>/dev/null | head -3
ls data/house/ 2>/dev/null | head -3
ls data/congress_press/ 2>/dev/null | head -3
```

```powershell
# Windows (PowerShell fallback if ls fails)
Get-ChildItem data\senate -ErrorAction SilentlyContinue | Select-Object -First 3
Get-ChildItem data\house -ErrorAction SilentlyContinue | Select-Object -First 3
Get-ChildItem data\congress_press -ErrorAction SilentlyContinue | Select-Object -First 3
```

Pass: each directory exists and contains at least one file.

---

## Step 5 — Pre-built output (optional)

```bash
ls output/investigation.duckdb 2>/dev/null && echo "found" || echo "not found"
```

```powershell
# Windows
if (Test-Path output\investigation.duckdb) { "found" } else { "not found" }
```

This is an optional check. The pre-built file can substitute for raw data + a full build.

---

## Step 6 — Print the checklist

Format and print:

```
FairGuard — setup check
────────────────────────────────────────────────────────
✓/✗  Python X.X.X                      (≥ 3.11 required)
✓/✗  uv X.X.X
✓/✗  Node.js vXX.X.X
✓/✗  npm X.X.X
✓/✗  Python deps installed             (uv sync)
✓/✗  web/ deps installed               (npm ci)
✓/✗  data/senate/                      (raw corpus)
✓/✗  data/house/                       (raw corpus)
✓/✗  data/congress_press/              (raw corpus)
✓/✗  output/investigation.duckdb       (pre-built, optional)
────────────────────────────────────────────────────────
```

If raw data directories are missing, append:

```
  ✗ Raw data not found. Two options:

  Option A — Download pre-built output/ (recommended for evaluation, ~10 min):
    1. https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing
    2. Unzip the archive
    3. Place the output/ folder at the project root
    You can then run /fair-guard scan immediately — no 2.5 hr build required.

  Option B — Download the raw LDA corpus (~8.6 GB) from the challenge data
    portal, place it in data/, then run /fair-guard index.
```

---

## Step 7 — Offer to build the index

Conditions for offering: all required system checks pass (Python ≥ 3.11, uv, uv sync)
AND `output/investigation.duckdb` does NOT already exist AND raw data IS present.

Ask:

```
All required checks passed. Build the analytical database now?
  [1] Full build  — all 2022–Q1 2026 data  (~2.5 hr)
  [2] Sample build — one quarter per source (~2 min, validates pipeline)
  [3] Skip — I will download the pre-built output/ from Drive
```

- If [1]: read `skill/lda-corpus-indexer/SKILL.md` and run `uv run scripts/01_build_index.py`
- If [2]: read `skill/lda-corpus-indexer/SKILL.md` and run `uv run scripts/01_build_index.py --sample`
- If [3]: print the Drive link and exit successfully

If `output/investigation.duckdb` already exists:
Print "Pre-built database found at output/investigation.duckdb — /fair-guard scan is ready."
