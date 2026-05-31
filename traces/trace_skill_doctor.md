# Trace — `/fair-guard doctor`

**Date:** 2026-05-30
**Skill invoked:** `doctor` (setup-validator)
**Platform:** Windows 11 (PowerShell), Python 3.11.15
**Outcome:** PASS — setup ready; next action surfaced.

---

## Invocation

User typed `/fair-guard doctor` in Claude Code.

Dispatcher routed to `skill/doctor/SKILL.md`, which instructs the agent to
run `scripts/doctor.py` and surface its output verbatim. Because `doctor` has
no DB prerequisite, the dispatcher's prerequisite guard passes immediately.

```
uv run scripts/doctor.py
```

## Agent action

The agent ran the single command above. No interpretive branching — the
Python script handles every check itself. No prompting between steps.

## Output (verbatim)

```
FairGuard — setup check
────────────────────────────────────────────────────────────
  [PASS]  Python ≥ 3.11: Python 3.11.15
  [PASS]  uv installed: uv 0.11.16 (135a36367 2026-05-21 x86_64-pc-windows-msvc)
  [PASS]  Node.js installed: v24.9.0
  [PASS]  npm installed: 11.6.0
  [PASS]  Python deps (duckdb, polars, rapidfuzz): all importable
  [PASS]  web/ dependencies installed: node_modules present
  [WARN]  data/ layout: raw corpus found under data/data/ (nested) — set DATA_ROOT=data/data
  [PASS]  data/senate/: found at data\data\senate
  [PASS]  data/house/: found at data\data\house
  [PASS]  data/congress_press/: found at data\data\congress_press
  [PASS]  Pre-built DB integrity: senate_filings: 418,170 rows
────────────────────────────────────────────────────────────
  10 passed, 1 warning(s), 0 failure(s)

Next action:
  Setup is ready. You can run:  /fair-guard scan
```

## Notes on output

- **Single WARN** is the known `data/data/` nesting caused by the corpus zip
  extracting one level deep. The script detects this case automatically and
  prints a fix (`set DATA_ROOT=data/data`). It is non-blocking because the
  pre-built DB is also present.
- **Next action** is computed deterministically in `compute_next_action()` —
  the agent doesn't decide what to suggest, the script does. This is the
  single most important property of this rewrite: the routing is part of
  the script, not the prompt.

## What was tested

| Property | Tested by |
|---|---|
| Python version gate | `check_python` |
| Tooling presence (uv, node, npm) | `check_uv`, `check_node`, `check_npm` |
| Project venv + key imports | `check_python_env` |
| Web deps | `check_web_env` |
| Raw data presence with nested fallback | `check_raw_data` |
| Pre-built DB opens and answers a real query | `check_built_db` |

## Cross-platform note

The skill SKILL.md previously mixed `ls`, `head`, `2>/dev/null` (bash) with
`Get-ChildItem`, `Test-Path` (PowerShell). The current implementation is a
single Python script — same behaviour on Linux, macOS, and Windows. Confirmed
on Windows in this trace; tested on Linux via `WSL` (output identical except
for path separators).

## Human review

A reporter using this skill confirms environment readiness in under 5
seconds. No follow-up commands needed if all checks pass; if any fail, the
script tells them exactly what to fix.
