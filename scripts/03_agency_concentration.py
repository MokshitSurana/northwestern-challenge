#!/usr/bin/env python3
"""
03_agency_concentration.py — Find Bridenstine-pattern revolving-door cases.

Identifies former senior government officials who now lobby the exact agency
they previously led, measuring an "agency concentration ratio" — the share
of their firm's filings that target their former agency.

This is the structural version of the Artemis Group / Bridenstine finding:
instead of one case, it ranks every similar pattern across the full 2022-2026
Senate LDA corpus.

Methodology:
  1. Pull all distinct (lobbyist, firm, covered_position) triples from the DB.
  2. For each triple, match covered_position against AGENCY_REGISTRY patterns
     to detect a prior senior role at a named federal agency.
  3. For each matched lobbyist, query two counts:
       total_filings: all filings they appear on (at their firm)
       agency_filings: filings at that firm that target their former agency
  4. concentration = agency_filings / total_filings
  5. Filter: concentration >= MIN_CONC, total_filings >= MIN_FILINGS
  6. Rank: concentration × log(total_filings) × seniority_score

Usage:
    uv run scripts/03_agency_concentration.py
    uv run scripts/03_agency_concentration.py --min-filings 5 --min-conc 0.15
    uv run scripts/03_agency_concentration.py --agency nasa
    uv run scripts/03_agency_concentration.py --top 50

Output:
    output/agency_concentration.csv         — full ranked table
    output/agency_concentration.md          — human-readable findings
    notes/06_structural_pattern_findings.md — journalism-ready draft
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import duckdb

DB_PATH = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))
NOTES_DIR = Path("notes")

# ── Minimum thresholds (overridable via CLI) ───────────────────────────────────
DEFAULT_MIN_FILINGS = 10   # at least 10 filings at the firm
DEFAULT_MIN_CONC    = 0.20  # at least 20% of filings target former agency
DEFAULT_TOP         = 40

# ── Agency registry ────────────────────────────────────────────────────────────
# Each entry: (short_name, entity_fragment, seniority_score, cov_pos_patterns)
#
#   short_name       — used in --agency filter and output labels
#   entity_fragment  — substring to match against senate_gov_entities.entity_name
#   seniority_score  — 5 = head/administrator, 4 = deputy, 3 = senior staff
#   cov_pos_patterns — list of regex patterns that indicate a SENIOR prior role
#                      ALL matched against covered_position (case-insensitive)
#                      A match on ANY pattern qualifies the lobbyist.
#                      Patterns should require seniority keywords + agency name.

AGENCY_REGISTRY = [
    (
        "nasa",
        "Aeronautics & Space",  # matches "Natl Aeronautics & Space Administration (NASA)"
        5,
        [
            r"\bAdministrator\b.{0,60}\bNASA\b",
            r"\bAdministrator\b.{0,60}\bNational Aeronautics\b",
            r"\bNASA\b.{0,60}\bAdministrator\b",
            r"\bDeputy Administrator\b.{0,60}\bNASA\b",
            r"\bAssociate Administrator\b.{0,60}\bNASA\b",
            r"\bChief of Staff\b.{0,80}\bNASA\b",
            r"\bNASA\b.{0,60}\bChief of Staff\b",
            r"\bDirector\b.{0,60}\bNASA\b.{0,40}\b(Center|Division|Office)\b",
        ],
    ),
    (
        "epa",
        "Environmental Protection Agency",
        5,
        [
            r"\bAdministrator\b.{0,60}\bEPA\b",
            r"\bAdministrator\b.{0,60}\bEnvironmental Protection\b",
            r"\bEPA\b.{0,60}\bAdministrator\b",
            r"\bDeputy Administrator\b.{0,60}\bEPA\b",
            r"\bAssistant Administrator\b.{0,60}\bEPA\b",
            r"\bChief of Staff\b.{0,80}\bEPA\b",
            r"\bEPA\b.{0,60}\bChief of Staff\b",
        ],
    ),
    (
        "fda",
        "Food & Drug Administration",
        5,
        [
            r"\bCommissioner\b.{0,60}\bFDA\b",
            r"\bCommissioner\b.{0,60}\bFood and Drug\b",
            r"\bFDA\b.{0,60}\bCommissioner\b",
            r"\bDeputy Commissioner\b.{0,60}\bFDA\b",
            r"\bAssociate Commissioner\b.{0,60}\bFDA\b",
            r"\bChief of Staff\b.{0,80}\bFDA\b",
            r"\bCenter Director\b.{0,80}\bFDA\b",
        ],
    ),
    (
        "fcc",
        "Federal Communications Commission",
        5,
        [
            r"\bChairman\b.{0,60}\bFCC\b",
            r"\bChairwoman\b.{0,60}\bFCC\b",
            r"\bFCC\b.{0,60}\bChair(man|woman)?\b",
            r"\bCommissioner\b.{0,60}\bFCC\b",
            r"\bFCC\b.{0,60}\bCommissioner\b",
            r"\bChief of Staff\b.{0,80}\bFCC\b",
            r"\bFCC\b.{0,60}\bChief of Staff\b",
        ],
    ),
    (
        "sec",
        "Securities & Exchange Commission",
        5,
        [
            r"\bChairman\b.{0,60}\bSEC\b",
            r"\bChairwoman\b.{0,60}\bSEC\b",
            r"\bSEC\b.{0,60}\bChair(man|woman)?\b",
            r"\bCommissioner\b.{0,60}\bSEC\b",
            r"\bSEC\b.{0,60}\bCommissioner\b",
            r"\bDirector\b.{0,60}\bSEC\b",
            r"\bChief of Staff\b.{0,80}\bSEC\b",
        ],
    ),
    (
        "ftc",
        "Federal Trade Commission",
        5,
        [
            r"\bChairman\b.{0,60}\bFTC\b",
            r"\bChairwoman\b.{0,60}\bFTC\b",
            r"\bFTC\b.{0,60}\bChair(man|woman)?\b",
            r"\bCommissioner\b.{0,60}\bFTC\b",
            r"\bFTC\b.{0,60}\bCommissioner\b",
            r"\bChief of Staff\b.{0,80}\bFTC\b",
        ],
    ),
    (
        "dod",
        "Defense, Dept of",
        5,
        [
            r"\bSecretary of Defense\b",
            r"\bDeputy Secretary of Defense\b",
            r"\bUnder Secretary\b.{0,60}\bDefense\b",
            r"\bAssistant Secretary\b.{0,60}\bDefense\b",
            r"\bChief of Staff\b.{0,80}\bPentagon\b",
        ],
    ),
    (
        "treasury",
        "Treasury, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bTreasury\b",
            r"\bTreasury\b.{0,60}\bSecretary\b",
            r"\bDeputy Secretary\b.{0,60}\bTreasury\b",
            r"\bUnder Secretary\b.{0,60}\bTreasury\b",
            r"\bAssistant Secretary\b.{0,60}\bTreasury\b",
            r"\bDeputy Assistant Secretary\b.{0,60}\bTreasury\b",
            r"\bChief of Staff\b.{0,80}\bTreasury\b",
        ],
    ),
    (
        "hhs",
        "Health & Human Services",
        5,
        [
            r"\bSecretary\b.{0,60}\bHHS\b",
            r"\bSecretary\b.{0,60}\bHealth and Human Services\b",
            r"\bDeputy Secretary\b.{0,60}\bHHS\b",
            r"\bAssistant Secretary\b.{0,60}\bHHS\b",
            r"\bChief of Staff\b.{0,80}\bHHS\b",
        ],
    ),
    (
        "dhs",
        "Homeland Security, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bHomeland Security\b",
            r"\bSecretary\b.{0,60}\bDHS\b",
            r"\bDeputy Secretary\b.{0,60}\bDHS\b",
            r"\bUnder Secretary\b.{0,60}\bDHS\b",
            r"\bChief of Staff\b.{0,80}\bDHS\b",
        ],
    ),
    (
        "interior",
        "Interior, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bInterior\b",
            r"\bDeputy Secretary\b.{0,60}\bInterior\b",
            r"\bAssistant Secretary\b.{0,60}\bInterior\b",
            r"\bChief of Staff\b.{0,80}\bInterior\b",
            r"\bDirector\b.{0,60}\bBureau of Land Management\b",
            r"\bDirector\b.{0,60}\bBLM\b",
        ],
    ),
    (
        "energy",
        "Energy, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bEnergy\b",
            r"\bDeputy Secretary\b.{0,60}\bEnergy\b",
            r"\bUnder Secretary\b.{0,60}\bEnergy\b",
            r"\bAssistant Secretary\b.{0,60}\bDOE\b",
            r"\bChief of Staff\b.{0,80}\bDOE\b",
        ],
    ),
    (
        "state",
        "State, Dept of",
        5,
        [
            r"\bSecretary of State\b",
            r"\bDeputy Secretary of State\b",
            r"\bUnder Secretary\b.{0,60}\bState Department\b",
            r"\bAssistant Secretary\b.{0,60}\bState Department\b",
            r"\bChief of Staff\b.{0,80}\bState Department\b",
        ],
    ),
    (
        "dot",
        "Transportation, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bTransportation\b",
            r"\bDeputy Secretary\b.{0,60}\bTransportation\b",
            r"\bUnder Secretary\b.{0,60}\bTransportation\b",
            r"\bAdministrator\b.{0,60}\bFAA\b",
            r"\bAdministrator\b.{0,60}\bFederal Aviation\b",
            r"\bChief of Staff\b.{0,80}\bDOT\b",
        ],
    ),
    (
        "faa",
        "Federal Aviation Administration",
        5,
        [
            r"\bAdministrator\b.{0,60}\bFAA\b",
            r"\bAdministrator\b.{0,60}\bFederal Aviation\b",
            r"\bFAA\b.{0,60}\bAdministrator\b",
            r"\bDeputy Administrator\b.{0,60}\bFAA\b",
            r"\bChief of Staff\b.{0,80}\bFAA\b",
        ],
    ),
    (
        "ferc",
        "Federal Energy Regulatory Commission",
        5,
        [
            r"\bChairman\b.{0,60}\bFERC\b",
            r"\bChairwoman\b.{0,60}\bFERC\b",
            r"\bFERC\b.{0,60}\bChair(man|woman)?\b",
            r"\bCommissioner\b.{0,60}\bFERC\b",
            r"\bFERC\b.{0,60}\bCommissioner\b",
        ],
    ),
    (
        "cftc",
        "Commodity Futures Trading Commission",
        5,
        [
            r"\bChairman\b.{0,60}\bCFTC\b",
            r"\bChairwoman\b.{0,60}\bCFTC\b",
            r"\bCFTC\b.{0,60}\bChair(man|woman)?\b",
            r"\bCommissioner\b.{0,60}\bCFTC\b",
        ],
    ),
    (
        "cfpb",
        "Consumer Financial Protection Bureau",
        5,
        [
            r"\bDirector\b.{0,60}\bCFPB\b",
            r"\bCFPB\b.{0,60}\bDirector\b",
            r"\bDeputy Director\b.{0,60}\bCFPB\b",
            r"\bChief of Staff\b.{0,80}\bCFPB\b",
        ],
    ),
    (
        "usda",
        "Agriculture, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bAgriculture\b",
            r"\bSecretary\b.{0,60}\bUSDA\b",
            r"\bDeputy Secretary\b.{0,60}\bAgriculture\b",
            r"\bUnder Secretary\b.{0,60}\bUSDA\b",
            r"\bChief of Staff\b.{0,80}\bUSDA\b",
        ],
    ),
    (
        "va",
        "Veterans Affairs, Dept of",
        5,
        [
            r"\bSecretary\b.{0,60}\bVeterans Affairs\b",
            r"\bSecretary\b.{0,60}\b\bVA\b",
            r"\bDeputy Secretary\b.{0,60}\bVeterans Affairs\b",
            r"\bUnder Secretary\b.{0,60}\bVeterans Affairs\b",
            r"\bChief of Staff\b.{0,80}\bVA\b",
        ],
    ),
    (
        "sba",
        "Small Business Administration",
        5,
        [
            r"\bAdministrator\b.{0,60}\bSBA\b",
            r"\bAdministrator\b.{0,60}\bSmall Business Administration\b",
            r"\bSBA\b.{0,60}\bAdministrator\b",
            r"\bDeputy Administrator\b.{0,60}\bSBA\b",
        ],
    ),
    (
        "omb",
        "Office of Management & Budget",
        4,
        [
            r"\bDirector\b.{0,60}\bOMB\b",
            r"\bOMB\b.{0,60}\bDirector\b",
            r"\bDeputy Director\b.{0,60}\bOMB\b",
            r"\bAssociate Director\b.{0,60}\bOMB\b",
        ],
    ),
    (
        "ustr",
        "U.S. Trade Representative",
        5,
        [
            r"\bTrade Representative\b",
            r"\bUSTR\b.{0,60}\bRepresentative\b",
            r"\bDeputy Trade Representative\b",
        ],
    ),
    (
        "cms",
        "Centers For Medicare and Medicaid",
        5,
        [
            r"\bAdministrator\b.{0,60}\bCMS\b",
            r"\bAdministrator\b.{0,60}\bCenters for Medicare\b",
            r"\bCMS\b.{0,60}\bAdministrator\b",
            r"\bDeputy Administrator\b.{0,60}\bCMS\b",
            r"\bChief of Staff\b.{0,80}\bCMS\b",
        ],
    ),
]

# Pre-compile all patterns for speed
COMPILED_REGISTRY = [
    (short, fragment, score,
     [re.compile(p, re.IGNORECASE) for p in patterns])
    for short, fragment, score, patterns in AGENCY_REGISTRY
]


def classify_covered_position(text: str) -> list[tuple[str, str, int]]:
    """
    Returns list of (short_name, entity_fragment, seniority_score) for each
    agency detected as a senior prior role in covered_position.
    May return multiple if the person held senior roles at multiple agencies.
    """
    if not text or len(text) < 10:
        return []
    matches = []
    for short, fragment, score, compiled_patterns in COMPILED_REGISTRY:
        for pat in compiled_patterns:
            if pat.search(text):
                matches.append((short, fragment, score))
                break  # only one match per agency
    return matches


# ── Core SQL queries ───────────────────────────────────────────────────────────

def get_lobbyist_profiles(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """
    Pull all distinct (lobbyist_name, covered_position, registrant_id, registrant_name)
    from the Senate side. This is the universe of people to classify.

    total_filings = ALL filings for the lobbyist at the firm (not just the ones
    where covered_position is populated). This avoids the >100% concentration bug
    where agency_filings > total_filings because the latter was filtered by cov.
    """
    print("  Loading lobbyist profiles from senate_lobbyists…")
    rows = con.execute("""
        WITH
        -- The covered_position we care about (non-null rows only)
        cov_profiles AS (
            SELECT
                sl.lobbyist_name,
                sf.registrant_id,
                sf.registrant_name,
                MAX(sl.covered_position)    AS covered_position,
                MAX(sl.source_path)         AS sample_source,
                MAX(sf.filing_uuid)         AS sample_uuid
            FROM senate_lobbyists sl
            JOIN senate_filings sf USING (filing_uuid)
            WHERE sl.covered_position IS NOT NULL
              AND LENGTH(sl.covered_position) > 10
              AND sl.lobbyist_name IS NOT NULL
            GROUP BY sl.lobbyist_name, sf.registrant_id, sf.registrant_name
        ),
        -- ALL filings for the same (lobbyist, firm) regardless of covered_position
        all_filings AS (
            SELECT
                sl.lobbyist_name,
                sf.registrant_id,
                COUNT(DISTINCT sf.filing_uuid)  AS total_filings,
                SUM(sf.income)                  AS total_income,
                COUNT(DISTINCT sf.client_name)  AS n_clients,
                MIN(sf.filing_year)             AS first_year,
                MAX(sf.filing_year)             AS last_year
            FROM senate_lobbyists sl
            JOIN senate_filings sf USING (filing_uuid)
            WHERE sl.lobbyist_name IS NOT NULL
            GROUP BY sl.lobbyist_name, sf.registrant_id
        )
        SELECT
            cp.lobbyist_name,
            cp.registrant_id,
            cp.registrant_name,
            cp.covered_position,
            af.total_filings,
            af.total_income,
            af.n_clients,
            af.first_year,
            af.last_year,
            cp.sample_source,
            cp.sample_uuid
        FROM cov_profiles cp
        JOIN all_filings af
          ON cp.lobbyist_name = af.lobbyist_name
          AND cp.registrant_id = af.registrant_id
    """).fetchall()
    cols = ["lobbyist_name", "registrant_id", "registrant_name", "covered_position",
            "total_filings", "total_income", "n_clients", "first_year", "last_year",
            "sample_source", "sample_uuid"]
    return [dict(zip(cols, r)) for r in rows]


def get_agency_filing_count(
    con: duckdb.DuckDBPyConnection,
    lobbyist_name: str,
    registrant_id: str,
    entity_fragment: str,
) -> int:
    """
    Count how many filings this lobbyist has (at their firm) that target
    the specified agency (matched by entity_name fragment).
    """
    result = con.execute("""
        SELECT COUNT(DISTINCT sf.filing_uuid)
        FROM senate_lobbyists sl
        JOIN senate_filings sf USING (filing_uuid)
        WHERE sl.lobbyist_name = ?
          AND sf.registrant_id = ?
          AND sf.filing_uuid IN (
              SELECT DISTINCT filing_uuid
              FROM senate_gov_entities
              WHERE entity_name ILIKE ?
          )
    """, [lobbyist_name, registrant_id, f"%{entity_fragment}%"]).fetchone()
    return result[0] if result else 0


def get_top_clients_for_agency(
    con: duckdb.DuckDBPyConnection,
    lobbyist_name: str,
    registrant_id: str,
    entity_fragment: str,
    limit: int = 5,
) -> list[str]:
    """Top clients this lobbyist lobbied this agency on behalf of."""
    rows = con.execute("""
        SELECT sf.client_name, COUNT(DISTINCT sf.filing_uuid) AS n
        FROM senate_lobbyists sl
        JOIN senate_filings sf USING (filing_uuid)
        WHERE sl.lobbyist_name = ?
          AND sf.registrant_id = ?
          AND sf.filing_uuid IN (
              SELECT DISTINCT filing_uuid
              FROM senate_gov_entities
              WHERE entity_name ILIKE ?
          )
        GROUP BY sf.client_name
        ORDER BY n DESC
        LIMIT ?
    """, [lobbyist_name, registrant_id, f"%{entity_fragment}%", limit]).fetchall()
    return [r[0] for r in rows]


# ── Main scan ──────────────────────────────────────────────────────────────────

def run_scan(
    min_filings: int = DEFAULT_MIN_FILINGS,
    min_conc: float = DEFAULT_MIN_CONC,
    agency_filter: str | None = None,
    top: int = DEFAULT_TOP,
) -> list[dict]:
    con = duckdb.connect(str(DB_PATH), read_only=True)

    print(f"\nLoading lobbyist profiles…")
    profiles = get_lobbyist_profiles(con)
    print(f"  {len(profiles):,} distinct (lobbyist, firm) pairs with covered_position")

    # ── Classify each profile ──────────────────────────────────────────────────
    print(f"\nClassifying by prior agency role…")
    candidates = []
    n_classified = 0
    agency_counts: dict[str, int] = defaultdict(int)

    for profile in profiles:
        cov = profile["covered_position"] or ""
        matches = classify_covered_position(cov)
        if not matches:
            continue
        n_classified += 1

        for short_name, entity_fragment, seniority in matches:
            if agency_filter and short_name != agency_filter:
                continue
            agency_counts[short_name] += 1
            candidates.append({
                **profile,
                "agency_short":      short_name,
                "entity_fragment":   entity_fragment,
                "seniority":         seniority,
            })

    print(f"  {n_classified:,} profiles matched a senior agency role")
    print(f"  {len(candidates):,} (lobbyist, firm, agency) triples to evaluate")
    for short, cnt in sorted(agency_counts.items(), key=lambda x: -x[1]):
        print(f"    {short.upper():<12} {cnt:,}")

    # ── Filter by minimum total filings and compute agency concentration ───────
    print(f"\nComputing agency concentration (min_filings={min_filings}, min_conc={min_conc:.0%})…")
    results = []
    for i, cand in enumerate(candidates):
        if cand["total_filings"] < min_filings:
            continue
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(candidates)} processed…", end="\r")

        agency_filings = get_agency_filing_count(
            con,
            cand["lobbyist_name"],
            cand["registrant_id"],
            cand["entity_fragment"],
        )
        if agency_filings == 0:
            continue
        concentration = agency_filings / cand["total_filings"]
        if concentration < min_conc:
            continue

        top_clients = get_top_clients_for_agency(
            con,
            cand["lobbyist_name"],
            cand["registrant_id"],
            cand["entity_fragment"],
        )

        # Bridenstine-style interestingness score:
        #   concentration × log(total_filings+1) × seniority
        score = concentration * math.log(cand["total_filings"] + 1) * cand["seniority"]

        results.append({
            **cand,
            "agency_filings":  agency_filings,
            "concentration":   round(concentration, 4),
            "score":           round(score, 3),
            "top_clients_str": " | ".join(top_clients),
        })

    print(f"  {len(results):,} candidates pass thresholds")
    con.close()

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ── Output formatters ──────────────────────────────────────────────────────────

def write_csv(results: list[dict], path: Path) -> None:
    if not results:
        return
    keep = [
        "score", "agency_short", "lobbyist_name", "registrant_name",
        "covered_position", "concentration", "agency_filings", "total_filings",
        "n_clients", "total_income", "first_year", "last_year",
        "top_clients_str", "sample_uuid", "sample_source",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[CSV] {path}  ({len(results)} rows)")


def _pct(v: float) -> str:
    return f"{v:.1%}"


def write_markdown(results: list[dict], path: Path, top: int) -> None:
    lines = [
        "# Agency Concentration Analysis — Bridenstine-Pattern Findings",
        "",
        f"_Top {min(top, len(results))} of {len(results)} candidates passing thresholds._",
        "_Score = concentration × log(total_filings+1) × seniority. Higher = more Bridenstine-like._",
        "_All figures from Senate LDA corpus 2022-2026. Requires independent verification._",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(results[:top], 1):
        income_m = round((c["total_income"] or 0) / 1e6, 2)
        lines += [
            f"## {i}. {c['lobbyist_name']}  ·  {c['agency_short'].upper()}",
            f"**Score:** {c['score']}  |  "
            f"**Concentration:** {_pct(c['concentration'])}  |  "
            f"**Seniority:** {c['seniority']}",
            "",
            f"**Prior role:** {c['covered_position']}",
            "",
            f"**Firm:** {c['registrant_name']}",
            f"**Agency filings / Total filings:** {c['agency_filings']} / {c['total_filings']}",
            f"**Clients:** {c['n_clients']}  |  **Disclosed income:** ${income_m}M  "
            f"|  **Active:** {c['first_year']}–{c['last_year']}",
            "",
            f"**Top agency-targeting clients:** {c['top_clients_str']}",
            "",
            f"**Source filing:** `{c['sample_uuid']}`",
            f"**Source path:** `{c['sample_source']}`",
            "",
            "---",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[MD]  {path}")


def write_web_json(results: list[dict], web_dir: Path, top: int = 40) -> None:
    """
    Write findings as JSON to web/public/findings.json so the Next.js reporter
    UI picks them up automatically on the next `npm run dev` or `npm run build`.

    This is the automation bridge — running the script always refreshes the UI.
    No manual copy-paste required.

    Schema matches the Finding interface in web/src/app/page.tsx.
    """
    web_public = web_dir / "public"
    web_public.mkdir(parents=True, exist_ok=True)
    out_path = web_public / "findings.json"

    # Keys the web UI needs (matches Finding interface in page.tsx)
    web_keys = [
        "score", "agency_short", "lobbyist_name", "registrant_name",
        "covered_position", "concentration", "agency_filings", "total_filings",
        "n_clients", "total_income", "first_year", "last_year",
        "top_clients_str", "sample_uuid", "sample_source",
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(results),
        "findings": [
            {
                "rank": i + 1,
                **{k: c.get(k) for k in web_keys},
                "total_income": float(c.get("total_income") or 0),
                "senate_lda_url": (
                    f"https://lda.senate.gov/filings/public/filing/{c['sample_uuid']}/print/"
                    if c.get("sample_uuid") else None
                ),
                "verification_status": c.get("verification_status"),  # None until manually set
            }
            for i, c in enumerate(results[:top])
        ],
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[JSON] {out_path}  ({len(payload['findings'])} findings → web UI)")


def write_findings_draft(results: list[dict], path: Path, top: int = 10) -> None:
    """
    Write a journalism-ready draft note for the structural finding.
    Mirrors the structure of notes/05_finding_bridenstine.md.
    """
    top_results = results[:top]
    lines = [
        "# Finding 02 (Structural Pattern): Former Agency Heads Lobbying Their Former Agency",
        "",
        "**Status:** Draft. All quantitative claims sourced to `output/investigation.duckdb`.",
        "Biographical claims require independent verification before any publication.",
        "This finding extends the Artemis Group / Bridenstine case study (Finding 01)",
        "to the full corpus.",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "A systematic scan of the 2022-2026 Senate LDA corpus identifies former senior",
        "government officials who now lobby the exact federal agency they previously led,",
        "measuring the share of their firm's filings that target their former agency",
        "(the 'agency concentration ratio').",
        "",
        f"The scan identified **{len(results)} candidates** across {len(set(r['agency_short'] for r in results))} agencies",
        "who hold a former senior role at a named agency and whose firm has ≥10 filings",
        "targeting that agency at ≥20% concentration.",
        "",
        "The top cases, ranked by Bridenstine-style interestingness score",
        "(concentration × log(filings) × seniority), are:",
        "",
    ]
    for i, c in enumerate(top_results, 1):
        lines.append(
            f"{i}. **{c['lobbyist_name']}** ({c['agency_short'].upper()}) — "
            f"{_pct(c['concentration'])} concentration, "
            f"{c['agency_filings']}/{c['total_filings']} filings, "
            f"firm: {c['registrant_name']}"
        )
    lines += [
        "",
        "---",
        "",
        "## Methodology",
        "",
        "1. **Agency detection in covered_position.** For each of 23 named federal agencies,",
        "   regex patterns match senior-role indicators (Administrator, Commissioner, Secretary,",
        "   Deputy Secretary, Chairman, Director, Chief of Staff) combined with the agency name.",
        "   Patterns are documented in `scripts/03_agency_concentration.py` → `AGENCY_REGISTRY`.",
        "",
        "2. **Concentration ratio.** For each matched (lobbyist, firm, agency) triple:",
        "   `concentration = agency_filings / total_filings` where agency_filings counts",
        "   filings at that firm where `senate_gov_entities.entity_name` matches the agency.",
        "",
        "3. **Score.** `score = concentration × log(total_filings + 1) × seniority_score`",
        "   This rewards high concentration at high volume, penalizes one-filing flukes.",
        "",
        "4. **Thresholds.** Default: concentration ≥ 20%, total filings ≥ 10.",
        "   Adjustable via `--min-conc` and `--min-filings` flags.",
        "",
        "5. **Senate LDA only.** The concentration is computed on Senate-side records only.",
        "   A combined Senate+House ranking would shift the ordering.",
        "",
        "---",
        "",
        "## Individual Cases (Top 10)",
        "",
    ]
    for i, c in enumerate(top_results, 1):
        income_m = round((c["total_income"] or 0) / 1e6, 2)
        lines += [
            f"### {i}. {c['lobbyist_name']} → {c['agency_short'].upper()}",
            "",
            f"**Score:** {c['score']}  |  **Concentration:** {_pct(c['concentration'])}",
            "",
            f"**Prior role (per LDA disclosure):** {c['covered_position']}",
            "",
            f"**Firm:** {c['registrant_name']}",
            f"**Filings targeting former agency:** {c['agency_filings']} of {c['total_filings']} total ({_pct(c['concentration'])})",
            f"**Clients (agency-targeting):** {c['top_clients_str']}",
            f"**Disclosed firm income:** ${income_m}M across {c['n_clients']} clients, {c['first_year']}–{c['last_year']}",
            "",
            "**Verification status:** LDA figures are sourced directly from the corpus.",
            "Prior role characterization is verbatim from covered_position field — not independently",
            "verified against agency staff directories. See §2.5 of Finding 01 for precedent.",
            "",
            "**⚠️ Open items before this claim is reportable:**",
            f"- [ ] Confirm prior role at {c['agency_short'].upper()} via agency records / news archives",
            "- [ ] Verify cooling-off period status (18 USC §207)",
            "- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)",
            "- [ ] Request comment from lobbyist and firm",
            "",
            "---",
            "",
        ]
    lines += [
        "## Next Steps",
        "",
        "- [ ] Run combined Senate+House concentration analysis (currently Senate-only)",
        "- [ ] Cross-reference top cases against press release corpus for say-vs-pay alignment",
        "- [ ] External verification of top 5 cases (agency records, news, LinkedIn)",
        "- [ ] Identify cases where clients hold active contracts at the former agency (USAspending)",
        "- [ ] Request comment from top-ranked lobbyists and their firms",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[MD]  {path}  (journalism draft)")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--min-filings", type=int, default=DEFAULT_MIN_FILINGS,
                        help=f"Minimum total filings at firm (default: {DEFAULT_MIN_FILINGS})")
    parser.add_argument("--min-conc", type=float, default=DEFAULT_MIN_CONC,
                        help=f"Minimum agency concentration ratio (default: {DEFAULT_MIN_CONC})")
    parser.add_argument("--agency",
                        choices=[e[0] for e in AGENCY_REGISTRY],
                        help="Filter to a single agency")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"Number of results in output (default: {DEFAULT_TOP})")
    parser.add_argument("--web-dir", type=Path, default=Path("web"),
                        help="Path to the Next.js web directory (default: web/). "
                             "The script writes web/public/findings.json automatically.")
    parser.add_argument("--no-web", action="store_true",
                        help="Skip writing web/public/findings.json")
    args = parser.parse_args()

    print("=" * 60)
    print("FairGuard — Agency Concentration Scanner (Track 2)")
    print("=" * 60)
    print(f"DB: {DB_PATH}")
    print(f"Thresholds: min_filings={args.min_filings}, min_conc={args.min_conc:.0%}")
    if args.agency:
        print(f"Agency filter: {args.agency.upper()}")

    results = run_scan(
        min_filings=args.min_filings,
        min_conc=args.min_conc,
        agency_filter=args.agency,
        top=args.top,
    )

    if not results:
        print("\nNo results pass the thresholds.")
        return

    # Print top 10 to terminal
    print(f"\n{'='*60}")
    print(f"TOP 10 RESULTS (of {len(results)})")
    print(f"{'='*60}")
    for i, c in enumerate(results[:10], 1):
        income_m = round((c["total_income"] or 0) / 1e6, 2)
        print(f"\n{i:2}. [{c['score']:5.2f}] {c['lobbyist_name']}  ·  {c['agency_short'].upper()}")
        print(f"      Concentration: {_pct(c['concentration'])}  "
              f"({c['agency_filings']}/{c['total_filings']} filings)")
        print(f"      Firm: {c['registrant_name']}")
        print(f"      Role: {(c['covered_position'] or '')[:120]}")
        print(f"      Income: ${income_m}M  |  Clients: {c['n_clients']}")

    # Write outputs
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(results, OUTPUT_ROOT / "agency_concentration.csv")
    write_markdown(results, OUTPUT_ROOT / "agency_concentration.md", args.top)
    write_findings_draft(results, NOTES_DIR / "06_structural_pattern_findings.md")

    # Auto-update the web UI data (no --no-web flag needed normally)
    if not args.no_web:
        write_web_json(results, args.web_dir, top=args.top)

    # Summary by agency
    from collections import Counter
    agency_hits = Counter(r["agency_short"] for r in results)
    print(f"\n{'='*60}")
    print("HITS BY AGENCY")
    print(f"{'='*60}")
    for short, cnt in agency_hits.most_common():
        print(f"  {short.upper():<12}  {cnt:,} candidates")


if __name__ == "__main__":
    main()
