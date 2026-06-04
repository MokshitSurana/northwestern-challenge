"""One-shot money-trail probe against the USAspending.gov API.

Queries `/api/v2/search/spending_by_award/` for a recipient + awarding agency +
award class (grants or contracts) and prints the total obligated and the
individual award rows. Used to deepen the revolving-door money trail documented in
notes/08_external_verification_top_candidates.md.

Not part of the shipped skill pipeline — kept in scripts/ (prefixed `_probe`) as a
reproducible record of the queries behind the money-trail figures.

Usage:
    uv run scripts/_probe_usaspending.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Award type code groups
GRANTS = ["02", "03", "04", "05"]          # block/formula/project grants, coop agreements
CONTRACTS = ["A", "B", "C", "D"]            # definitive contract / purchase order / etc.
LOANS = ["07", "08"]                        # direct loan / guaranteed loan
DIRECT = ["06", "10"]                       # direct payment / other

FIELDS = [
    "Award ID",
    "Recipient Name",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Description",
    "Start Date",
]


def query(recipient: str, agency: str, award_codes: list[str],
          start: str = "2021-01-01", end: str = "2026-06-04",
          limit: int = 100) -> list[dict]:
    """Return award rows for a recipient at an awarding agency."""
    body = {
        "filters": {
            "recipient_search_text": [recipient],
            "award_type_codes": award_codes,
            "time_period": [{"start_date": start, "end_date": end}],
            "agencies": [
                {"type": "awarding", "tier": "toptier", "name": agency}
            ],
        },
        "fields": FIELDS,
        "limit": limit,
        "sort": "Award Amount",
        "order": "desc",
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        API, data=data, headers={"Content-Type": "application/json"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())["results"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            sys.stderr.write(f"HTTP {e.code} for {recipient!r}: {e.read()[:200]!r}\n")
            return []
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            sys.stderr.write(f"network error for {recipient!r}: {e}\n")
            return []
    return []


def total_for(recipient: str, agency: str, award_codes: list[str]) -> tuple[float, list[dict]]:
    rows = query(recipient, agency, award_codes)
    total = sum((r.get("Award Amount") or 0) for r in rows)
    return total, rows


def scan(label: str, recipients: list[str], agency: str,
         award_codes: list[str] = GRANTS) -> float:
    """Print a per-recipient breakdown for one lobbyist's client list."""
    print("=" * 78)
    print(f"{label}  —  awarding agency: {agency}  ({'grants' if award_codes==GRANTS else 'contracts' if award_codes==CONTRACTS else award_codes})")
    print("=" * 78)
    grand = 0.0
    for rec in recipients:
        total, rows = total_for(rec, agency, award_codes)
        if total <= 0:
            print(f"  --            {rec}")
            continue
        grand += total
        print(f"  ${total:>16,.0f}  {rec}  ({len(rows)} award(s))")
        for r in rows[:4]:
            amt = r.get("Award Amount") or 0
            sub = (r.get("Awarding Sub Agency") or "")[:28]
            desc = (r.get("Description") or "")[:46]
            print(f"        ${amt:>14,.0f}  [{sub:<28}] {desc}")
        time.sleep(0.4)
    print(f"\n  TOTAL for {label}: ${grand:,.0f}\n")
    return grand


def verified_total(search: str, agency: str, name_tokens: list[str],
                   groups: list[list[str]]) -> tuple[float, dict]:
    """Sum awards across award-type groups, keeping only those whose Recipient
    Name contains one of `name_tokens` (strips fuzzy recipient_search_text hits).
    De-dupes by Award ID. Returns (total, {award_id: (amount, recipient, subagency)})."""
    seen: dict = {}
    toks = [t.upper() for t in name_tokens]
    for codes in groups:
        for r in query(search, agency, codes):
            recip = (r.get("Recipient Name") or "").upper()
            if not any(t in recip for t in toks):
                continue
            seen[r.get("Award ID")] = (
                r.get("Award Amount") or 0, r.get("Recipient Name"),
                r.get("Awarding Sub Agency"),
            )
    return sum(v[0] for v in seen.values()), seen


# Reproduces the deepened money trail in
# notes/08_external_verification_top_candidates.md. Each entry is
# (label, recipient_search_text, [name tokens that must appear in Recipient Name]).
STEINBERG_DOE = [
    ("Cirba Solutions", "Cirba Solutions", ["CIRBA SOLUTIONS"]),
    ("EnerSys", "EnerSys", ["ENERSYS"]),
    ("South32 Hermosa", "South32 Hermosa", ["SOUTH32 HERMOSA"]),
    ("Sila Nanotechnologies", "Sila Nanotechnologies", ["SILA NANOTECHNOLOGIES"]),
    ("Anovion", "Anovion", ["ANOVION"]),
    ("Talon Nickel", "Talon Nickel", ["TALON NICKEL"]),
    ("Forge Battery", "Forge Battery", ["FORGE BATTERY"]),
    ("Cabot Corp", "Cabot Corporation", ["CABOT CORP"]),
    ("Nanoramic", "Nanoramic", ["NANORAMIC"]),
]

LIMBAUGH_INTERIOR = [
    ("Sites Project Authority", "Sites Project Authority", ["SITES PROJECT"]),
    ("Glenn-Colusa Irrigation District", "Glenn-Colusa Irrigation", ["GLENN COLUSA", "GLENN-COLUSA"]),
    ("Friant Water Authority", "Friant Water Authority", ["FRIANT WATER"]),
    ("Reclamation District 108", "Reclamation District 108", ["RECLAMATION DISTRICT 108", "RECLAMATION DISTRICT NO. 108"]),
    ("Turlock Irrigation District", "Turlock Irrigation", ["TURLOCK IRRIGATION"]),
    ("The Freshwater Trust", "Freshwater Trust", ["FRESHWATER TRUST"]),
    ("North Unit Irrigation District", "North Unit Irrigation", ["NORTH UNIT IRRIGATION"]),
    ("Western Municipal Water District", "Western Municipal Water", ["WESTERN MUNICIPAL WATER"]),
    ("Sutter Mutual Water Company", "Sutter Mutual Water", ["SUTTER MUTUAL"]),
    ("El Dorado County Water Agency", "El Dorado County Water", ["EL DORADO"]),
    ("City of Woodland, CA", "City of Woodland", ["WOODLAND"]),
    ("Merced Irrigation District", "Merced Irrigation", ["MERCED IRRIGATION"]),
    ("Klamath Water Users", "Klamath Water Users", ["KLAMATH"]),
    ("Maricopa-Stanfield Irr. & Drainage", "Maricopa Stanfield Irrigation", ["MARICOPA"]),
    ("Solano Irrigation District", "Solano Irrigation", ["SOLANO IRRIGATION"]),
    ("City of Folsom, CA", "Folsom", ["FOLSOM"]),
    ("Yakima Basin", "Yakima Basin", ["YAKIMA"]),
    ("San Juan Water District", "San Juan Water District", ["SAN JUAN WATER"]),
    ("Central Arizona Irr. & Drainage", "Central Arizona Irrigation", ["CENTRAL ARIZONA IRRIGATION"]),
]

USDA_CASES = [
    ("Cargill (operating entities)", "Cargill",
     ["CARGILL, INCORPORATED", "CARGILL MEAT SOLUTIONS", "CARGILL KITCHEN SOLUTIONS"]),
    ("National Rural Water Assn", "National Rural Water", ["NATIONAL RURAL WATER"]),
    ("Tri-State Generation", "Tri-State Generation", ["TRI-STATE GENERATION"]),
    ("Land O'Lakes (Venture37)", "Land O'Lakes", ["LAND O'LAKES"]),
    ("McCain Foods USA", "McCain Foods", ["MCCAIN FOODS"]),
    ("Global Clean Energy", "Global Clean Energy", ["GLOBAL CLEAN ENERGY"]),
    ("Louis Dreyfus", "Louis Dreyfus", ["LOUIS DREYFUS"]),
    ("Ardent Mills", "Ardent Mills", ["ARDENT MILLS"]),
    ("California Prune Board", "California Prune", ["CALIFORNIA PRUNE"]),
    ("Shenandoah Valley Organic", "Shenandoah Valley Organic", ["SHENANDOAH VALLEY ORGANIC"]),
    ("Illinois Soybean Board", "Illinois Soybean", ["ILLINOIS SOYBEAN"]),
    ("California Rice Commission", "California Rice Commission", ["CALIFORNIA RICE"]),
]


def run_block(title: str, agency: str, cases: list, groups: list[list[str]]) -> float:
    print("=" * 78)
    print(f"{title}  (awarding agency: {agency})")
    print("=" * 78)
    grand = 0.0
    for label, search, tokens in cases:
        total, seen = verified_total(search, agency, tokens, groups)
        if total <= 0:
            print(f"  --                {label}")
            continue
        grand += total
        recips = sorted({v[1] for v in seen.values()})
        print(f"  ${total:>16,.0f}  {label}  ({len(seen)} award(s); {recips})")
        time.sleep(0.3)
    print(f"\n  TOTAL: ${grand:,.0f}\n")
    return grand


if __name__ == "__main__":
    # Steinberg -> DOE (discretionary BIL battery/critical-minerals grants).
    run_block("STEINBERG -> DOE", "Department of Energy", STEINBERG_DOE, [GRANTS])
    # Limbaugh -> Interior (Bureau of Reclamation water grants).
    run_block("LIMBAUGH -> INTERIOR", "Department of the Interior",
              LIMBAUGH_INTERIOR, [GRANTS])
    # USDA cases (grants + direct + contracts; loans excluded -> conservative).
    run_block("USDA CASES (Johnson/Bailey/Torrey/Barbic)", "Department of Agriculture",
              USDA_CASES, [GRANTS, DIRECT, CONTRACTS])
