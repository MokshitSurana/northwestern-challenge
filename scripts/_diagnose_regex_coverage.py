"""
For each agency, pull covered_position strings that mention the agency
(by name or abbreviation) and check how many our AGENCY_REGISTRY regexes match.

A low ratio means we're under-matching real senior-role disclosures.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location("ac", Path(__file__).parent / "03_agency_concentration.py")
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)

import duckdb

DB = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"
con = duckdb.connect(str(DB), read_only=True)

# Hand-built mapping: short_name -> list of keyword patterns to grep covered_position
AGENCY_KEYWORDS = {
    "nasa":     [r"\bNASA\b", r"National Aeronautics", r"Aeronautics and Space"],
    "epa":      [r"\bEPA\b", r"Environmental Protection Agency"],
    "fda":      [r"\bFDA\b", r"Food and Drug Administration"],
    "fcc":      [r"\bFCC\b", r"Federal Communications Commission"],
    "sec":      [r"\bSEC\b", r"Securities and Exchange"],
    "ftc":      [r"\bFTC\b", r"Federal Trade Commission"],
    "dod":      [r"\bDOD\b", r"Department of Defense", r"\bPentagon\b", r"\bDefense Department\b"],
    "treasury": [r"\bTreasury\b", r"\bTreas\b"],
    "hhs":      [r"\bHHS\b", r"Health and Human Services"],
    "dhs":      [r"\bDHS\b", r"Homeland Security"],
    "interior": [r"\bDOI\b", r"Department of (the )?Interior"],
    "energy":   [r"\bDOE\b", r"Department of Energy"],
    "state":    [r"State Department", r"Department of State", r"\bDOS\b"],
    "dot":      [r"\bDOT\b", r"Department of Transportation"],
    "faa":      [r"\bFAA\b", r"Federal Aviation"],
    "ferc":     [r"\bFERC\b"],
    "cftc":     [r"\bCFTC\b", r"Commodity Futures"],
    "cfpb":     [r"\bCFPB\b", r"Consumer Financial Protection"],
    "usda":     [r"\bUSDA\b", r"Department of Agriculture"],
    "va":       [r"Veterans Affairs", r"\bVA\b"],
    "sba":      [r"\bSBA\b", r"Small Business Administration"],
    "omb":      [r"\bOMB\b", r"Office of Management"],
    "ustr":     [r"\bUSTR\b", r"Trade Representative"],
    "cms":      [r"\bCMS\b", r"Centers for Medicare"],
}

# Senior role keywords — must appear together with agency keyword to qualify as a senior prior role
SENIOR_KW = re.compile(
    r"\b(Administrator|Commissioner|Secretary|Chairman|Chairwoman|"
    r"Chief of Staff|Director|Deputy Director|Deputy Administrator|"
    r"Deputy Secretary|Deputy Commissioner|Under Secretary|Assistant Secretary|"
    r"Associate Administrator|Assistant Administrator|Associate Commissioner|"
    r"Deputy Assistant Secretary|General Counsel|Inspector General)\b",
    re.IGNORECASE,
)

print(f"{'agency':<10} {'pool':>6} {'our-matched':>12} {'coverage':>10}  example MISSED senior-mentioning string")
print("-" * 130)

for short, keywords in AGENCY_KEYWORDS.items():
    # build SQL filter: any of the keywords + senior keyword
    kw_clauses = " OR ".join(["regexp_matches(covered_position, ?, 'i')" for _ in keywords])
    rows = con.execute(f"""
        SELECT DISTINCT covered_position FROM senate_lobbyists
        WHERE covered_position IS NOT NULL
          AND length(covered_position) > 10
          AND ({kw_clauses})
    """, keywords).fetchall()

    pool = []
    for (cov,) in rows:
        if SENIOR_KW.search(cov):
            pool.append(cov)

    # how many of those does our registry catch as belonging to this agency?
    matched = 0
    missed_examples = []
    for cov in pool:
        results = ac.classify_covered_position(cov)
        agencies = {r[0] for r in results}
        if short in agencies:
            matched += 1
        else:
            if len(missed_examples) < 3:
                missed_examples.append(cov)

    coverage = (matched / len(pool)) if pool else 0
    example = missed_examples[0][:90] if missed_examples else ""
    marker = "  ⚠" if coverage < 0.5 and len(pool) > 5 else ""
    print(f"{short:<10} {len(pool):>6,} {matched:>12,} {coverage:>9.1%}  {example}{marker}")

    if missed_examples and coverage < 0.5 and len(pool) > 5:
        for ex in missed_examples[1:]:
            print(f"{'':<43}{ex[:90]}")
