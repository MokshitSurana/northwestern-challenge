#!/usr/bin/env python3
"""
doctor.py — Cross-platform setup validator for FairGuard.

Replaces the prose+bash+PowerShell mixed instructions in the doctor SKILL.md
with a single Python script that works identically on Linux, macOS, and
Windows. The skill's SKILL.md simply runs this file and surfaces the output.

Checks:
  1. Tooling   — Python ≥ 3.11, uv, Node.js, npm
  2. Python    — `uv sync` ran (".venv" exists, key packages importable)
  3. Web       — web/node_modules exists (web/ deps installed)
  4. Raw data  — data/senate/, data/house/, data/congress_press/ present
  5. Built DB  — output/investigation.duckdb present and basic integrity OK

Each check prints either PASS, WARN (non-blocking), or FAIL. The exit code
is non-zero only if a REQUIRED check fails (raw data is optional; pre-built
DB is optional).

Usage:
    uv run scripts/doctor.py
    uv run scripts/doctor.py --quiet           # only failures + summary
    uv run scripts/doctor.py --json            # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


# This script lives at skills/doctor/scripts/, so the package root is three
# levels up (skills/doctor/scripts -> skills/doctor -> skills -> root).
ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))


@dataclass
class Check:
    name: str
    status: str       # "pass" | "warn" | "fail"
    detail: str
    required: bool = True
    fix: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    next_action: str = ""

    @property
    def has_required_failure(self) -> bool:
        return any(c.status == "fail" and c.required for c in self.checks)

    @property
    def summary(self) -> str:
        passed = sum(1 for c in self.checks if c.status == "pass")
        warned = sum(1 for c in self.checks if c.status == "warn")
        failed = sum(1 for c in self.checks if c.status == "fail")
        return f"{passed} passed, {warned} warning(s), {failed} failure(s)"


# ── Tooling checks ─────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
    """Run a command; return (ok, first line of output)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            # Required on Windows to find .cmd / .exe shims for uv, npm.
            shell=(os.name == "nt"),
        )
        out = (proc.stdout or proc.stderr or "").splitlines()
        return proc.returncode == 0, out[0].strip() if out else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def check_python(report: Report) -> None:
    v = sys.version_info
    detail = f"Python {v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 11):
        report.checks.append(Check(
            "Python ≥ 3.11", "pass", detail, required=True,
        ))
    else:
        report.checks.append(Check(
            "Python ≥ 3.11", "fail", f"{detail} (need 3.11+)",
            required=True,
            fix="Install Python 3.11+ — see https://www.python.org/downloads/ or use uv",
        ))


def check_uv(report: Report) -> None:
    if shutil.which("uv"):
        ok, line = _run(["uv", "--version"])
        if ok:
            report.checks.append(Check("uv installed", "pass", line, required=True))
            return
    report.checks.append(Check(
        "uv installed", "fail", "not found",
        required=True,
        fix="Install uv:  https://docs.astral.sh/uv/getting-started/installation/",
    ))


def check_node(report: Report) -> None:
    if shutil.which("node"):
        ok, line = _run(["node", "--version"])
        report.checks.append(Check(
            "Node.js installed",
            "pass" if ok else "fail",
            line or "version check failed",
            required=False,
            fix="" if ok else "Install Node.js 20+ — https://nodejs.org/",
        ))
    else:
        report.checks.append(Check(
            "Node.js installed", "warn", "not found (only needed for the web UI)",
            required=False,
            fix="Install Node.js 20+ from https://nodejs.org/",
        ))


def check_npm(report: Report) -> None:
    if shutil.which("npm"):
        ok, line = _run(["npm", "--version"])
        report.checks.append(Check(
            "npm installed",
            "pass" if ok else "fail",
            line or "version check failed",
            required=False,
        ))
    else:
        report.checks.append(Check(
            "npm installed", "warn", "not found (only needed for the web UI)",
            required=False,
        ))


# ── Project environment ───────────────────────────────────────────────────────

def check_python_env(report: Report) -> None:
    venv = ROOT / ".venv"
    if not venv.exists():
        report.checks.append(Check(
            "Python venv (.venv) exists", "fail", "missing",
            required=True,
            fix="Run:  uv sync",
        ))
        return

    # Verify key imports actually work via the project's interpreter
    probe = subprocess.run(
        ["uv", "run", "python", "-c", "import duckdb, polars, rapidfuzz; print('ok')"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        shell=(os.name == "nt"),
    )
    if probe.returncode == 0 and "ok" in probe.stdout:
        report.checks.append(Check(
            "Python deps (duckdb, polars, rapidfuzz)", "pass", "all importable",
            required=True,
        ))
    else:
        report.checks.append(Check(
            "Python deps (duckdb, polars, rapidfuzz)", "fail",
            (probe.stderr or "import failed").splitlines()[0] if probe.stderr else "import failed",
            required=True,
            fix="Run:  uv sync",
        ))


def check_web_env(report: Report) -> None:
    web = ROOT / "web"
    if not web.exists():
        report.checks.append(Check(
            "web/ dependencies", "warn", "web/ directory missing — UI disabled",
            required=False,
        ))
        return
    if (web / "node_modules").exists():
        report.checks.append(Check(
            "web/ dependencies installed", "pass", "node_modules present",
            required=False,
        ))
    else:
        report.checks.append(Check(
            "web/ dependencies installed", "warn",
            "node_modules not found — run `cd web && npm ci` if you want the UI",
            required=False,
            fix="cd web && npm ci",
        ))


# ── Data / build ──────────────────────────────────────────────────────────────

def _dir_has_files(p: Path) -> bool:
    if not p.exists() or not p.is_dir():
        return False
    try:
        return any(p.iterdir())
    except OSError:
        return False


def check_raw_data(report: Report) -> None:
    sources = {
        "senate": DATA_ROOT / "senate",
        "house": DATA_ROOT / "house",
        "congress_press": DATA_ROOT / "congress_press",
    }
    nested = DATA_ROOT / "data"
    if not any(_dir_has_files(p) for p in sources.values()) and nested.exists():
        # User extracted into data/data/ — point that out
        sources = {
            "senate": nested / "senate",
            "house": nested / "house",
            "congress_press": nested / "congress_press",
        }
        if any(_dir_has_files(p) for p in sources.values()):
            report.checks.append(Check(
                "data/ layout", "warn",
                "raw corpus found under data/data/ (nested) — set DATA_ROOT=data/data",
                required=False,
            ))

    for name, p in sources.items():
        if _dir_has_files(p):
            report.checks.append(Check(
                f"data/{name}/", "pass", f"found at {p}",
                required=False,  # optional — pre-built DB substitutes
            ))
        else:
            report.checks.append(Check(
                f"data/{name}/", "warn", f"not found at {p}",
                required=False,
                fix=(
                    "Either download raw LDA corpus into data/ and run /fair-guard index, "
                    "OR download pre-built output/ from the Drive link in README.md."
                ),
            ))


def check_built_db(report: Report) -> None:
    db = OUTPUT_ROOT / "investigation.duckdb"
    if not db.exists():
        report.checks.append(Check(
            "Pre-built DB (output/investigation.duckdb)", "warn",
            "not found",
            required=False,
            fix=(
                "Two options:\n"
                "    (A) Fast — download pre-built output/ from:\n"
                "        https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing\n"
                "    (B) Build from raw data:  /fair-guard index"
            ),
        ))
        return

    # Quick integrity check — does the file parse, does it have key tables?
    probe = subprocess.run(
        [
            "uv", "run", "python", "-c",
            "import duckdb;"
            "c=duckdb.connect(r'" + str(db) + "', read_only=True);"
            "r=c.execute(\"SELECT COUNT(*) FROM senate_filings\").fetchone();"
            "print(r[0])",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        shell=(os.name == "nt"),
    )
    if probe.returncode == 0:
        try:
            count = int(probe.stdout.strip())
            report.checks.append(Check(
                "Pre-built DB integrity", "pass",
                f"senate_filings: {count:,} rows",
                required=False,
            ))
        except ValueError:
            report.checks.append(Check(
                "Pre-built DB integrity", "fail",
                "found but cannot read senate_filings",
                required=False,
                fix="Rebuild:  /fair-guard index   OR   re-download from Drive",
            ))
    else:
        err = (probe.stderr or "").splitlines()[-1] if probe.stderr else "open failed"
        report.checks.append(Check(
            "Pre-built DB integrity", "fail",
            f"open failed: {err}",
            required=False,
            fix="Rebuild:  /fair-guard index",
        ))


# ── Routing — what should the user do next? ───────────────────────────────────

def compute_next_action(report: Report) -> str:
    by_name = {c.name: c for c in report.checks}

    # Hard blockers
    if by_name.get("Python ≥ 3.11", Check("","fail","")).status == "fail":
        return "Install Python 3.11+ before continuing."
    if by_name.get("uv installed", Check("","fail","")).status == "fail":
        return "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    if by_name.get("Python deps (duckdb, polars, rapidfuzz)", Check("","fail","")).status == "fail":
        return "Run:  uv sync"

    # DB present and OK
    db_check = by_name.get("Pre-built DB integrity")
    if db_check and db_check.status == "pass":
        return "Setup is ready. You can run:  /fair-guard scan"

    # No DB but raw data is here
    raw_present = any(
        c.status == "pass" and c.name.startswith("data/")
        for c in report.checks
    )
    if raw_present:
        return "Raw data found. Build the DB:  /fair-guard index"

    # No DB and no raw data
    return (
        "No data available. Either:\n"
        "  (A) Download pre-built output/ (fast, ~10 min):\n"
        "      https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf?usp=sharing\n"
        "  (B) Download raw LDA corpus into data/ and run:  /fair-guard index"
    )


# ── Output ────────────────────────────────────────────────────────────────────

ICONS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}


def print_human(report: Report, quiet: bool = False) -> None:
    print("FairGuard — setup check")
    print("─" * 60)
    for c in report.checks:
        if quiet and c.status == "pass":
            continue
        print(f"  [{ICONS[c.status]}]  {c.name}: {c.detail}")
        if c.status != "pass" and c.fix:
            for line in c.fix.splitlines():
                print(f"          → {line}")
    print("─" * 60)
    print(f"  {report.summary}")
    print()
    print("Next action:")
    for line in report.next_action.splitlines():
        print(f"  {line}")


def print_json(report: Report) -> None:
    payload = {
        "summary": report.summary,
        "next_action": report.next_action,
        "checks": [
            {
                "name": c.name,
                "status": c.status,
                "detail": c.detail,
                "required": c.required,
                "fix": c.fix,
            }
            for c in report.checks
        ],
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--quiet", action="store_true", help="Hide pass lines")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    args = p.parse_args()

    report = Report()
    check_python(report)
    check_uv(report)
    check_node(report)
    check_npm(report)
    check_python_env(report)
    check_web_env(report)
    check_raw_data(report)
    check_built_db(report)
    report.next_action = compute_next_action(report)

    if args.json:
        print_json(report)
    else:
        print_human(report, quiet=args.quiet)

    return 1 if report.has_required_failure else 0


if __name__ == "__main__":
    sys.exit(main())
