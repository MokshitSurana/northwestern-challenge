#!/usr/bin/env python3
"""
02_revolving_door_scan.py — Rank revolving-door lobbying candidates.

Mines the covered_position field across Senate and House lobbyist records
to surface former government officials who became lobbyists, ranked by
seniority of prior role × client spend × breadth of clients.

Usage:
    uv run scripts/02_revolving_door_scan.py
    uv run scripts/02_revolving_door_scan.py --top 50
    uv run scripts/02_revolving_door_scan.py --category members   # ex-Congress only
    uv run scripts/02_revolving_door_scan.py --category chiefs    # ex-chiefs of staff
    uv run scripts/02_revolving_door_scan.py --category agency    # ex-agency heads

Output:
    output/revolving_door_candidates.md   — ranked list, human-readable
    output/revolving_door_candidates.csv  — full table for further analysis
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH     = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))


# ── Role classification patterns ───────────────────────────────────────────────
# Each category: (label, regex patterns, seniority_score)
# Higher seniority = more interesting for journalism

ROLE_CATEGORIES = [
    (
        "former_member",
        "Former Member of Congress",
        5,
        re.compile(
            r"\b(Senator|Congressman|Congresswoman|Representative|Member of Congress|"
            r"US Congressman|US Senator)\b(?!.*\b(Aide|Assistant|Counsel|Staff|Clerk|Director|Advisor)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "agency_head",
        "Former Agency Head / Commissioner",
        5,
        re.compile(
            r"\b(Administrator|Commissioner|Secretary|Under Secretary|Deputy Secretary|"
            r"Chairman|Chairwoman|Director)\b.{0,60}"
            r"\b(SEC|FTC|FCC|FDA|CFTC|EPA|DOJ|DOD|DOE|HHS|USTR|CFPB|"
            r"Treasury|State Department|OMB|NSC|CIA|FBI|DEA)",
            re.IGNORECASE,
        ),
    ),
    (
        "committee_staff_director",
        "Former Committee Staff Director",
        4,
        re.compile(
            r"\b(Staff Director|Chief Counsel|General Counsel|Majority Staff|Minority Staff|"
            r"Clerk of the Committee)\b.{0,80}\b(Committee|Subcommittee)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chief_of_staff",
        "Former Chief of Staff (Member/Committee)",
        4,
        re.compile(
            r"\bChief of Staff\b.{0,80}\b(Sen\.|Senator|Rep\.|Representative|Congressman|"
            r"Congresswoman|Committee|Subcommittee|Conference)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "senior_staff",
        "Former Senior Congressional Staff",
        3,
        re.compile(
            r"\b(Legislative Director|Policy Director|Senior Policy Advisor|"
            r"Senior Counsel|Deputy Chief of Staff|Communications Director|"
            r"Press Secretary|Senior Advisor|Counsel)\b.{0,80}"
            r"\b(Sen\.|Rep\.|Senate|House|Congress|Committee)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "agency_staff",
        "Former Senior Agency Staff",
        3,
        re.compile(
            r"\b(Deputy Administrator|Associate Administrator|Deputy Director|"
            r"Assistant Secretary|Deputy Assistant Secretary|General Counsel|"
            r"Chief of Staff|Senior Advisor)\b.{0,60}"
            r"\b(SEC|FTC|FCC|FDA|CFTC|EPA|DOJ|DOD|DOE|HHS|USTR|CFPB|"
            r"Treasury|White House|OMB|NSC)\b",
            re.IGNORECASE,
        ),
    ),
]

# Fast-pivot: left government within 2 years of first lobbying filing
FAST_PIVOT_PATTERN = re.compile(
    r"(?:^|[\s,;])(20\d{2})\s*[-–]\s*(20\d{2}|present)",
    re.IGNORECASE,
)


def classify_position(text: str) -> tuple[str, str, int]:
    """Return (category_key, category_label, seniority_score) for a covered_position string."""
    if not text:
        return ("other", "Other Government", 1)
    for key, label, score, pattern in ROLE_CATEGORIES:
        if pattern.search(text):
            return (key, label, score)
    return ("other", "Other Government", 1)


def extract_end_year(text: str) -> int | None:
    """Extract the most recent year from a covered_position string."""
    years = re.findall(r'\b(20\d{2})\b', text)
    if years:
        return max(int(y) for y in years)
    return None


def is_fast_pivot(end_year: int | None, first_filing_year: int | None) -> bool:
    """True if left government within 2 years of first lobbying filing."""
    if end_year is None or first_filing_year is None:
        return False
    return (first_filing_year - end_year) <= 2


# ── Main scan ──────────────────────────────────────────────────────────────────

def run_scan(top: int = 30, category_filter: str | None = None) -> list[dict]:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return _run_scan_inner(con, top, category_filter)


def _run_scan_inner(con: duckdb.DuckDBPyConnection, top: int, category_filter: str | None) -> list[dict]:
    print("Loading Senate lobbyist/filing data…")
    senate_rows = con.execute("""
        SELECT
            sl.lobbyist_name,
            sl.covered_position,
            sf.registrant_name,
            sf.client_name,
            sf.filing_year,
            sf.filing_period,
            sf.income,
            sf.expenses,
            sa.general_issue_code,
            sf.filing_uuid,
            sf.source_path,
            'senate' AS chamber
        FROM senate_lobbyists sl
        JOIN senate_filings   sf USING (filing_uuid)
        LEFT JOIN senate_activities sa ON sa.filing_uuid = sl.filing_uuid
                                      AND sa.activity_idx = sl.activity_idx
        WHERE sl.covered_position IS NOT NULL
          AND length(sl.covered_position) > 10
    """).fetchall()
    senate_cols = ["lobbyist_name", "covered_position", "registrant_name", "client_name",
                   "filing_year", "filing_period", "income", "expenses",
                   "general_issue_code", "filing_uuid", "source_path", "chamber"]

    print("Loading House lobbyist/filing data…")
    house_rows = con.execute("""
        SELECT
            hl.lobbyist_name,
            hl.covered_position,
            hf.org_name             AS registrant_name,
            hf.client_name,
            hf.filing_year,
            hf.filing_period,
            hf.income,
            hf.expenses,
            ha.ali_code             AS general_issue_code,
            hf.house_id             AS filing_uuid,
            hf.source_path,
            'house'                 AS chamber
        FROM house_lobbyists  hl
        JOIN house_filings    hf USING (house_id)
        LEFT JOIN house_activities ha ON ha.house_id = hl.house_id AND ha.activity_idx = 0
        WHERE hl.covered_position IS NOT NULL
          AND length(hl.covered_position) > 10
    """).fetchall()

    all_rows = [dict(zip(senate_cols, r)) for r in senate_rows] + \
               [dict(zip(senate_cols, r)) for r in house_rows]

    print(f"Total rows with covered_position: {len(all_rows):,}")

    # ── Classify and aggregate per lobbyist ───────────────────────────────────
    # Key: (lobbyist_name or covered_position snippet, registrant_name)
    # Using covered_position as the identity anchor when name is missing
    buckets: dict[str, dict] = defaultdict(lambda: {
        "lobbyist_name": None,
        "covered_position": None,
        "category_key": None,
        "category_label": None,
        "seniority": 0,
        "registrant_name": None,
        "clients": set(),
        "issue_codes": set(),
        "filing_uuids": set(),
        "total_income": 0.0,
        "total_expenses": 0.0,
        "filing_years": set(),
        "source_paths": set(),
    })

    for row in all_rows:
        name   = row["lobbyist_name"] or ""
        cov    = row["covered_position"] or ""
        # Use first 80 chars of covered_position as identity when name is missing
        key_id = (name.strip().lower() if name.strip() else cov[:80].lower(),
                  (row["registrant_name"] or "").strip().lower())

        b = buckets[key_id]
        b["lobbyist_name"]    = b["lobbyist_name"] or row["lobbyist_name"]
        b["covered_position"] = b["covered_position"] or cov
        b["registrant_name"]  = row["registrant_name"]
        b["source_paths"].add(row["source_path"])

        if not b["category_key"]:
            key, label, score = classify_position(cov)
            b["category_key"]   = key
            b["category_label"] = label
            b["seniority"]      = score

        if row["client_name"]:
            b["clients"].add(row["client_name"])
        if row["general_issue_code"]:
            b["issue_codes"].add(row["general_issue_code"])
        if row["filing_uuid"]:
            b["filing_uuids"].add(str(row["filing_uuid"]))
        if row["income"]:
            b["total_income"] += float(row["income"])
        if row["expenses"]:
            b["total_expenses"] += float(row["expenses"])
        if row["filing_year"]:
            b["filing_years"].add(row["filing_year"])

    # ── Score and rank ────────────────────────────────────────────────────────
    candidates = []
    for (name_key, _), b in buckets.items():
        if b["category_key"] == "other" and not category_filter:
            # Only keep "other" if explicitly requested — too noisy
            pass

        cat_key = b["category_key"]
        if category_filter and cat_key != category_filter:
            continue

        seniority     = b["seniority"]
        n_clients     = len(b["clients"])
        n_filings     = len(b["filing_uuids"])
        income        = b["total_income"]
        end_year      = extract_end_year(b["covered_position"] or "")
        first_year    = min(b["filing_years"]) if b["filing_years"] else None
        fast_pivot    = is_fast_pivot(end_year, first_year)

        # Heuristic score: seniority dominates, then spend, then breadth
        score = (seniority * 10) + (income / 1e6) + (n_clients * 0.5) + (5 if fast_pivot else 0)

        candidates.append({
            "score":             round(score, 2),
            "category":          b["category_label"],
            "lobbyist_name":     b["lobbyist_name"] or "(name from position)",
            "covered_position":  b["covered_position"],
            "registrant_name":   b["registrant_name"],
            "n_clients":         n_clients,
            "top_clients":       " | ".join(sorted(b["clients"])[:3]),
            "issue_codes":       " ".join(sorted(b["issue_codes"])[:5]),
            "n_filings":         n_filings,
            "total_income_M":    round(income / 1e6, 2),
            "filing_years":      ",".join(str(y) for y in sorted(b["filing_years"])),
            "end_year":          end_year,
            "first_filing_year": first_year,
            "fast_pivot":        fast_pivot,
            "sample_uuid":       next(iter(b["filing_uuids"]), None),
            "source_path":       next(iter(b["source_paths"]), None),
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


# ── Output ─────────────────────────────────────────────────────────────────────

def write_markdown(candidates: list[dict], top: int, path: Path):
    lines = [
        "# Revolving Door Candidates — Ranked",
        "",
        f"_Top {top} of {len(candidates):,} total candidates with identifiable prior government roles._",
        "_Score = (seniority × 10) + (income_M) + (n_clients × 0.5) + (5 if fast pivot ≤2yr)_",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(candidates[:top], 1):
        fast = " **[FAST PIVOT]**" if c["fast_pivot"] else ""
        lines += [
            f"## {i}. {c['lobbyist_name']}{fast}",
            f"**Score:** {c['score']}  |  **Category:** {c['category']}",
            "",
            f"**Prior role:** {c['covered_position']}",
            "",
            f"**Firm:** {c['registrant_name']}  |  "
            f"**Clients:** {c['n_clients']}  |  "
            f"**Income:** ${c['total_income_M']}M  |  "
            f"**Filings:** {c['n_filings']}",
            "",
            f"**Top clients:** {c['top_clients']}",
            "",
            f"**Issue codes:** {c['issue_codes']}",
            "",
            f"**Years active:** {c['filing_years']}  |  "
            f"**Left gov:** {c['end_year']}  |  "
            f"**First filing:** {c['first_filing_year']}",
            "",
            f"**Source:** `{c['source_path']}`",
            f"**Filing UUID/ID:** `{c['sample_uuid']}`",
            "",
            "---",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nMarkdown written to {path}")


def write_csv(candidates: list[dict], path: Path):
    if not candidates:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(candidates[0].keys()))
        writer.writeheader()
        writer.writerows(candidates)
    print(f"CSV written to {path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top",      type=int, default=30,
                        help="Number of candidates to show (default: 30)")
    parser.add_argument("--category", choices=["former_member","agency_head",
                                               "committee_staff_director",
                                               "chief_of_staff","senior_staff","agency_staff"],
                        help="Filter to one category")
    args = parser.parse_args()

    candidates = run_scan(top=args.top, category_filter=args.category)

    if not candidates:
        print("No candidates found.")
        return

    # Print top 10 to terminal
    print(f"\n=== Top 10 Revolving Door Candidates ===\n")
    for i, c in enumerate(candidates[:10], 1):
        fast = " [FAST PIVOT]" if c["fast_pivot"] else ""
        print(f"{i:2}. [{c['score']:6.1f}] {c['lobbyist_name']}{fast}")
        print(f"      {c['category']}")
        print(f"      Role: {c['covered_position'][:100]}")
        print(f"      Firm: {c['registrant_name']}  |  Clients: {c['n_clients']}  |  Income: ${c['total_income_M']}M")
        print()

    output_md  = OUTPUT_ROOT / "revolving_door_candidates.md"
    output_csv = OUTPUT_ROOT / "revolving_door_candidates.csv"
    write_markdown(candidates, args.top, output_md)
    write_csv(candidates, output_csv)

    # Summary stats by category
    cats = Counter(c["category"] for c in candidates)
    print("\n=== Candidates by category ===")
    for label, count in cats.most_common():
        print(f"  {label:<45} {count:,}")


if __name__ == "__main__":
    main()
