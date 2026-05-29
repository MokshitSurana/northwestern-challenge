# Handoff Note — Archit → Mokshit

**Date:** May 29, 2026
**Topic:** New `/fair-guard doctor` mode — setup validator

---

## TL;DR

A fourth mode called `doctor` has been designed and placed in both skill locations.
It's a setup validator: it checks all prerequisites (Python, uv, Node.js, npm, data
dirs), prints a pass/fail checklist, and offers to launch `index` when everything
looks good. The instruction spec is complete. **Your job: test it across platforms
and fill in any gaps.**

---

## What was built (do not redo this)

Two files with the complete implementation spec:

| File | Purpose |
|------|---------|
| `skill/doctor/SKILL.md` | Standalone submission artifact (original format) |
| `.agents/skills/fair-guard/modes/doctor/SKILL.md` | agentskills.io compliant copy |

The dispatcher (`.claude/skills/fair-guard/SKILL.md`) already routes
`/fair-guard doctor` to `skill/doctor/SKILL.md`. The argument-hint now reads
`[mode: doctor | index | scan | resolve]`.

---

## What doctor does (spec summary)

1. Checks: Python ≥ 3.11, uv, Node.js, npm
2. Runs `uv sync` (idempotent)
3. Runs `cd web && npm ci`
4. Checks `data/senate/`, `data/house/`, `data/congress_press/`
5. Checks `output/investigation.duckdb` (optional — pre-built can skip the raw corpus)
6. Prints a ✓/✗ checklist with all results
7. If raw data is missing → prints both recovery options (Drive download or raw corpus)
8. If all required checks pass and DuckDB doesn't exist → asks user to choose full / sample / skip build

The Drive link for the pre-built output (judges use this to skip the 2.5 hr build):
https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing

---

## Your tasks

### 1. Test on Linux / macOS (~2 hr)

Run `/fair-guard doctor` on a clean Linux or macOS machine (fresh clone, no pre-installed deps).
Verify:
- Python version detection works for both `python` and `python3` invocations
- `uv sync` runs and creates `.venv/`
- `npm ci` runs from inside `web/`
- The data directory checks work (test with data present AND absent)
- The Drive download path actually works — download the zip, place `output/`, then run `/fair-guard scan`

### 2. Test on Windows PowerShell (~1 hr)

The data-check commands in the spec provide both Bash and PowerShell variants. Verify
that Claude Code on Windows selects the right one. If Claude picks Bash even on Windows,
update the skill to force PowerShell checks with a note like:
"On Windows, replace `ls` with `Get-ChildItem`."

### 3. Test the Drive download path end-to-end

1. Download from the Drive link above
2. Verify the zip extracts to `output/` (not `output/output/` — nested extraction is a known gotcha)
3. Place `output/` at project root
4. Run `/fair-guard scan` — confirm it works without running `index` first
5. If the zip structure is wrong, fix the Drive folder and update the link in both SKILL.md files

### 4. Handle `uv sync` inside an already-active venv

Some CI environments activate a venv before running. Check whether `uv sync` behaves
correctly in that case. If it creates a nested venv or errors, add a note to the skill.

### 5. (Optional) Extract into standalone scripts

If the Bash checks become complex enough to warrant it, create:
- `skill/doctor/scripts/check_prerequisites.sh` (Linux/macOS)
- `skill/doctor/scripts/check_prerequisites.ps1` (Windows)

Reference them from `SKILL.md` so Claude runs them instead of inline commands.

---

## After testing: files to update

| File | What to change |
|------|---------------|
| `skill/doctor/SKILL.md` | Fix any commands that failed during testing |
| `.agents/skills/fair-guard/modes/doctor/SKILL.md` | Mirror the same fixes |
| `CLAUDE.md` | Run `/init` in Claude Code to sync docs |

Keep both SKILL.md files identical in body content — only the frontmatter differs
(original format vs. agentskills.io compliant).

---

## Mode name changes (effective today)

All mode names have been shortened. The original `skill/` files are unchanged.
Only the `.agents/skills/fair-guard/modes/` directories and the dispatcher use
the short names.

| Old name | Short name | What it does |
|----------|-----------|-------------|
| `lda-corpus-indexer` | `index` | Build DuckDB from raw LDA data |
| `revolving-door-detector` | `scan` | Find revolving-door patterns |
| `entity-resolver` | `resolve` | Normalize org/person names |
| *(new)* | `doctor` | Setup validation + guided onboarding |

Users now type:
```
/fair-guard doctor    ← was not available before
/fair-guard index     ← was /fair-guard lda-corpus-indexer
/fair-guard scan      ← was /fair-guard revolving-door-detector
/fair-guard resolve   ← was /fair-guard entity-resolver
```

---

## Priority of this task

Medium-high. Doctor is the most user-facing addition — it's the first thing a judge
runs after cloning. A broken `doctor` means they see a failure before they see any
journalism. Get it working reliably on at least Linux and Windows before the July 15
deadline.

Estimated time: 3–4 hours across platforms.
