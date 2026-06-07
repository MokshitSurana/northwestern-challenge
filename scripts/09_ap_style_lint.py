#!/usr/bin/env python3
"""
09_ap_style_lint.py — AP-style lint for findings markdown and exports.

A small, focused AP-style checker. It does NOT try to be a complete AP
Stylebook implementation — that would require natural-language understanding
the script can't sensibly do. It does catch a set of patterns that
investigative reporters and copy editors actually flag:

  1. Numbers under 10 spelled out where they should be (in the body).
     We don't apply the rule indiscriminately — versions, percentages,
     dollar amounts, ages, and ordinals are excluded.
  2. Percent symbol vs. spelled "percent" (AP prefers the symbol in copy
     since 2019 — but we flag the spelled form so the team chooses
     consistently).
  3. Smart quotes inside ASCII-quoted block text where the rest is ASCII
     (typography inconsistency).
  4. Oxford comma in serial lists (AP traditionally drops it; we flag
     occurrences so the team confirms intent).
  5. "Over" vs "more than" with numbers (AP changed this rule in 2014;
     both are acceptable but we flag uses of "over" with a number so the
     team's house style stays consistent).
  6. State abbreviations vs AP standards (AP uses Wis. not WI in body
     text, but allows postal codes in tables; this is a context-sensitive
     check we do conservatively — only flag two-letter postal codes
     OUTSIDE table cells).
  7. Month abbreviations (AP: Jan., Feb., Aug., Sept., Oct., Nov., Dec.;
     spelled-out: March, April, May, June, July). Flag spelled-out
     abbreviables in body text.

Output is one finding per line in a grep-able format: PATH:LINE:COL message.
Exit codes: 0 = no findings; 1 = at least one finding (suitable for use as
a pre-commit / CI gate or PostToolUse hook).

Usage:
    uv run scripts/09_ap_style_lint.py findings/findings_report.md
    uv run scripts/09_ap_style_lint.py findings/*.md notes/05_finding_*.md
    uv run scripts/09_ap_style_lint.py --quiet findings/findings_report.md
    uv run scripts/09_ap_style_lint.py --hook findings/findings_report.md
        # As a PostToolUse hook on Edit/Write of findings markdown.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── Rules ─────────────────────────────────────────────────────────────────────

# Numbers under 10 in body text (basic check; excludes versions, percentages,
# dollar amounts, dates, ordinals, addresses, page numbers).
_NUMBER_PATTERN = re.compile(
    r"(?<![\d$.\-:/+])(?<!\.)\b([1-9])\b(?!\d)(?![\s]*(?:%|\$|st|nd|rd|th|am|pm|million|billion|trillion|cents?|dollars?|years?|months?|weeks?|days?|hours?|minutes?|seconds?))",
    re.IGNORECASE,
)
_NUMBER_EXCLUDE = {
    # Numbered list markers, footnote refs, version strings, common code.
    r"^\s*\d[.)]\s",      # "1. " or "1) " — markdown list
    r"\[\d\]",            # [1] — footnote
    r"§207\(\w\)\(\d\)",  # §207(a)(1) — statute
    r"\d{4}-\d{2}-\d{2}", # 2026-06-07 — ISO date
    r"v\.?\d",            # v1, v.1
    r"#\d+",              # PR numbers etc
}

# AP changed in 2019 to recommend the % symbol in copy.
_PERCENT_SPELLED = re.compile(r"\b(\d+(?:\.\d+)?)\s+percent\b")

# Smart quotes in mostly-ASCII contexts.
_SMART_QUOTE = re.compile(r"[‘’“”]")
_ASCII_QUOTE_NEARBY = re.compile(r"[\"']")

# Oxford comma in a serial list — heuristic: 'A, B, and C'. AP drops the
# comma before 'and' in simple series; flag occurrences for review.
_OXFORD_COMMA = re.compile(r"(\w+),\s+(\w+),\s+and\s+(\w+)")

# 'over' with a number (AP since 2014 says both 'over' and 'more than' are
# fine, but house style usually wants one).
_OVER_NUMBER = re.compile(r"\bover\s+\$?\d", re.IGNORECASE)

# Postal codes outside table cells (rough heuristic — assume table cells
# contain '|').
_POSTAL_CODE = re.compile(r"\b([A-Z]{2})\b")
_POSTAL_VALID = {  # Two-letter codes we'd flag as postal abbreviations.
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC",
}

# AP month abbreviations
_AP_MONTH_ABBREVS = {
    "January": "Jan.",
    "February": "Feb.",
    "August": "Aug.",
    "September": "Sept.",
    "October": "Oct.",
    "November": "Nov.",
    "December": "Dec.",
}
_MONTH_DAY_RE = re.compile(
    r"\b(January|February|August|September|October|November|December)\s+\d{1,2}\b"
)

# Skip lines that are clearly code blocks, tables, headers, or YAML
# frontmatter. Linting these creates noise.
def _should_skip_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith(("#", "```", "    ", "|", "- ", "* ", "> ", "---")):
        return True
    if s.startswith(("/", "$", "uv run", "python", "npm", "cd ", "git ")):
        return True
    return False


# ── Lint engine ───────────────────────────────────────────────────────────────


def _matches(pat: re.Pattern, line: str) -> list[re.Match]:
    return list(pat.finditer(line))


def _has_excluded_context(line: str, m: re.Match) -> bool:
    """Return True if the match position is inside one of the excluded
    contexts (e.g. inside a `code span`, a markdown link target, etc.).
    Conservative: only flags clearly outside-of-code text."""
    start = m.start()
    # Inside a `code span` if there's an unmatched backtick before us.
    pre = line[:start]
    if pre.count("`") % 2 == 1:
        return True
    # Inside [link text](url) parens — skip the URL.
    if "](" in pre and ")" not in pre[pre.index("]("):]:
        return True
    return False


def lint_file(path: Path) -> list[tuple[int, int, str]]:
    """Returns list of (line, col, message) findings for a single file."""
    findings: list[tuple[int, int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [(0, 0, f"read error: {e}")]

    in_frontmatter = False
    in_code_block = False
    for i, raw_line in enumerate(text.splitlines(), 1):
        # Track frontmatter and fenced code blocks so we don't lint them.
        if raw_line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if raw_line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_frontmatter or in_code_block:
            continue
        if _should_skip_line(raw_line):
            continue

        # Rule 1: spelled-out numbers under 10.
        for m in _matches(_NUMBER_PATTERN, raw_line):
            if any(re.search(pat, raw_line) for pat in _NUMBER_EXCLUDE):
                continue
            if _has_excluded_context(raw_line, m):
                continue
            findings.append((i, m.start() + 1,
                             f"AP: number under 10 — consider spelling out '{m.group(1)}' "
                             f"(or confirm this is a measurement/ratio/age)"))

        # Rule 2: spelled "percent".
        for m in _matches(_PERCENT_SPELLED, raw_line):
            findings.append((i, m.start() + 1,
                             f"AP: prefer % symbol — '{m.group(0)}' → '{m.group(1)}%'"))

        # Rule 3: smart quotes when ASCII quotes are nearby in same line.
        if _SMART_QUOTE.search(raw_line) and _ASCII_QUOTE_NEARBY.search(raw_line):
            m = _SMART_QUOTE.search(raw_line)
            findings.append((i, m.start() + 1,
                             "Typography: smart quote alongside ASCII quote — pick one style"))

        # Rule 4: Oxford comma.
        for m in _matches(_OXFORD_COMMA, raw_line):
            findings.append((i, m.start() + 1,
                             f"AP: Oxford comma in series '{m.group(0)}' — AP drops the "
                             f"comma before 'and' in simple series"))

        # Rule 5: 'over' with a number.
        for m in _matches(_OVER_NUMBER, raw_line):
            findings.append((i, m.start() + 1,
                             f"AP house-style: 'over' before a number — confirm "
                             f"'{m.group(0)}' vs. 'more than'"))

        # Rule 6: postal-code abbreviations outside table cells.
        if "|" not in raw_line:
            for m in _matches(_POSTAL_CODE, raw_line):
                if m.group(1) in _POSTAL_VALID:
                    # Skip if it's part of a longer all-caps identifier
                    # (e.g. 'CTIA' detection — we match 'CT' inside).
                    s, e = m.span()
                    if e < len(raw_line) and raw_line[e].isupper():
                        continue
                    if s > 0 and raw_line[s - 1].isupper():
                        continue
                    findings.append((i, m.start() + 1,
                                     f"AP: '{m.group(1)}' is a postal code — AP body uses "
                                     f"abbreviation in text (e.g. 'Wis.' not 'WI')"))

        # Rule 7: spelled-out abbreviable months.
        for m in _matches(_MONTH_DAY_RE, raw_line):
            month = m.group(1)
            abbrev = _AP_MONTH_ABBREVS.get(month)
            if abbrev:
                findings.append((i, m.start() + 1,
                                 f"AP: month with day — '{month}' should be '{abbrev}' "
                                 f"per AP style"))

    return findings


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("paths", nargs="+", help="Markdown files to lint.")
    ap.add_argument("--quiet", action="store_true",
                    help="Only print findings; suppress the per-file header.")
    ap.add_argument("--json", action="store_true",
                    help="Emit findings as JSON (one object per file) for tooling.")
    ap.add_argument("--hook", action="store_true",
                    help="PostToolUse hook mode: read stdin JSON, lint the file, "
                         "exit 1 if findings exist so the hook surfaces them.")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Hook mode: Claude Code passes hook context on stdin; we lint the file
    # in tool_input.file_path. Print findings to stderr so Claude sees them.
    if args.hook:
        try:
            hook_data = json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            return 0  # Don't break the tool if we can't read context.
        tool_input = hook_data.get("tool_input") or {}
        file_path = tool_input.get("file_path") or tool_input.get("path")
        if not file_path:
            return 0
        path = Path(file_path)
        if not path.suffix == ".md":
            return 0
        findings = lint_file(path)
        if findings:
            sys.stderr.write(f"AP-style lint: {len(findings)} finding(s) in {path}:\n")
            for line, col, msg in findings:
                sys.stderr.write(f"  {path}:{line}:{col}: {msg}\n")
            # Non-blocking: emit findings but don't fail the tool.
            return 0
        return 0

    total = 0
    all_findings: list[dict] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            sys.stderr.write(f"warn: {raw_path} not found\n")
            continue
        findings = lint_file(path)
        if not findings:
            if not args.quiet and not args.json:
                print(f"{path}: clean")
            continue
        total += len(findings)
        all_findings.append({
            "path": str(path),
            "n_findings": len(findings),
            "findings": [{"line": ln, "col": c, "message": m} for ln, c, m in findings],
        })
        if not args.json:
            if not args.quiet:
                print(f"{path}: {len(findings)} finding(s)")
            for line, col, msg in findings:
                print(f"{path}:{line}:{col}: {msg}")

    if args.json:
        print(json.dumps(all_findings, indent=2, ensure_ascii=False))

    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
