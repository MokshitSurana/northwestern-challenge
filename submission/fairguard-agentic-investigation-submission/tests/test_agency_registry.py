"""
Tests for the AGENCY_REGISTRY used by scripts/03_agency_concentration.py (scan skill).

Three layers of assertions:

  1.  Every entity_fragment in the registry must match at least one row in
      senate_gov_entities.entity_name. A zero-match fragment silently breaks
      scan for that agency. (Requires output/investigation.duckdb.)

  2.  Hand-curated positive cases — `covered_position` strings that ARE
      senior roles at the named agency. Each must classify to the expected
      agency.

  3.  Hand-curated negative cases — strings that mention an agency but are
      NOT senior roles at it (congressional staff, junior positions, roles
      at sibling agencies). Each must NOT classify to the named agency.

The eval set is intentionally agency-balanced — adding more strings to one
agency without the others creates classification-coverage drift.

Run:
    uv run pytest tests/test_agency_registry.py -v
    uv run pytest tests/test_agency_registry.py::test_positive_cases -v
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "revolving-door-detector" / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("ac", ROOT / "skills" / "revolving-door-detector" / "scripts" / "03_agency_concentration.py")
ac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ac)


DB_PATH = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"


# ─── POSITIVE CASES ────────────────────────────────────────────────────────────
# (covered_position string, expected_agency_short_name)
# Sourced from the actual corpus; representative of real senior-role disclosures.
POSITIVE_CASES = [
    # NASA
    # NOTE: "Senior Advisor" is not Bridenstine-grade — only head-equivalent
    # roles qualify (Administrator, Deputy Administrator, Associate
    # Administrator, Chief of Staff, agency-confirmed counsel).
    ("Administrator, NASA (April 2018 - January 2021)", "nasa"),
    ("Chief of Staff, NASA", "nasa"),
    ("NASA Administrator (2018-2021); U.S. Representative OK-1 (2013-2018)", "nasa"),
    ("Deputy Administrator, NASA", "nasa"),
    ("Associate Administrator, National Aeronautics and Space Administration", "nasa"),

    # EPA
    ("Administrator, EPA (2017-2018)", "epa"),
    ("Deputy General Counsel, Environmental Protection Agency", "epa"),
    ("Assoc. Admin. Cong. Affairs, EPA (2001-03)", "epa"),
    ("Chief of Staff to Administrator, EPA", "epa"),
    ("Assistant Administrator, EPA Office of Air and Radiation", "epa"),

    # FDA
    ("Commissioner, FDA (2017-2019)", "fda"),
    ("Deputy Commissioner for Policy, FDA", "fda"),
    ("Chief of Staff, Food and Drug Administration", "fda"),
    ("Associate Commissioner for Legislation, FDA", "fda"),

    # FCC
    ("Chairman, FCC (2017-2021)", "fcc"),
    ("Counselor to the Chairman, Federal Communications Commission (2013-2016)", "fcc"),
    ("Commissioner, FCC", "fcc"),

    # SEC
    ("Chairman, SEC", "sec"),
    ("Commissioner, Securities and Exchange Commission", "sec"),
    ("Director, Division of Enforcement, SEC", "sec"),
    ("Chief of Staff, SEC", "sec"),

    # FTC
    ("Commissioner, FTC (2018-2022)", "ftc"),
    ("Chairman, Federal Trade Commission", "ftc"),

    # DOD
    ("Secretary of Defense", "dod"),
    ("Deputy Secretary of Defense", "dod"),
    ("Under Secretary for Policy, DoD", "dod"),
    ("Assistant Secretary of Defense", "dod"),
    ("Principal Deputy Assistant Secretary of Defense", "dod"),

    # Treasury
    ("Secretary of the Treasury", "treasury"),
    ("Deputy Secretary, Department of the Treasury", "treasury"),
    ("Under Secretary for International Affairs, Treasury", "treasury"),
    ("Assistant Secretary for Tax Policy, Treasury", "treasury"),
    ("Chief of Staff to the Secretary, Treasury", "treasury"),

    # HHS
    ("Secretary of HHS", "hhs"),
    ("Deputy Secretary, Health and Human Services", "hhs"),
    ("Assistant Secretary for Legislation, HHS", "hhs"),
    ("Chief of Staff, Department of Health and Human Services", "hhs"),

    # DHS
    ("Secretary, Department of Homeland Security", "dhs"),
    ("Deputy Secretary, DHS", "dhs"),
    ("Under Secretary, Homeland Security", "dhs"),
    ("Chief of Staff, DHS", "dhs"),

    # Interior
    ("Secretary, Department of the Interior", "interior"),
    ("Chief of Staff - DOI", "interior"),
    ("Assistant Secretary, Department of the Interior", "interior"),
    ("Director, Bureau of Land Management", "interior"),

    # Energy
    ("Secretary of Energy", "energy"),
    ("Deputy Secretary, Department of Energy", "energy"),
    ("Under Secretary for Science, DOE", "energy"),
    ("Assistant Secretary, Department of Energy Office of Fossil Energy", "energy"),
    ("Chief of Staff, DOE", "energy"),

    # State
    ("Secretary of State", "state"),
    ("Deputy Secretary of State", "state"),
    ("Under Secretary, Department of State", "state"),
    ("Chief of Staff, State Department", "state"),
    ("Assistant Secretary of State for Legislative Affairs", "state"),

    # DOT
    ("Secretary of Transportation", "dot"),
    ("Deputy Secretary, Department of Transportation", "dot"),
    ("Under Secretary, DOT", "dot"),

    # FAA
    ("Administrator, FAA", "faa"),
    ("Acting Administrator, Federal Aviation Administration", "faa"),
    ("Deputy Administrator, FAA", "faa"),
    ("FAA - Asst Administrator", "faa"),

    # FERC
    ("Chairman, FERC", "ferc"),
    ("Commissioner, Federal Energy Regulatory Commission", "ferc"),

    # CFTC
    ("Chairman, CFTC", "cftc"),
    ("Commissioner, Commodity Futures Trading Commission", "cftc"),
    ("Chief of Staff, Commodity Futures Trading Commission", "cftc"),
    ("General Counsel, CFTC", "cftc"),

    # CFPB
    ("Director, CFPB", "cfpb"),
    ("Deputy Director, Consumer Financial Protection Bureau", "cfpb"),
    ("Chief of Staff, CFPB", "cfpb"),

    # USDA
    ("Secretary of Agriculture", "usda"),
    ("Deputy Secretary, USDA", "usda"),
    ("Under Secretary for Trade and Foreign Agricultural Affairs, USDA", "usda"),
    ("Chief of Staff, Department of Agriculture", "usda"),

    # VA
    ("Secretary of Veterans Affairs", "va"),
    ("Deputy Secretary, Veterans Affairs", "va"),
    ("Under Secretary for Health, VA", "va"),

    # SBA
    ("Administrator, Small Business Administration", "sba"),
    ("Deputy Administrator, SBA", "sba"),

    # OMB
    ("Director, OMB", "omb"),
    ("Deputy Director, Office of Management and Budget", "omb"),
    ("OMB Chief of Staff", "omb"),
    ("Associate Director, OMB", "omb"),

    # USTR
    ("U.S. Trade Representative", "ustr"),
    ("Deputy U.S. Trade Representative", "ustr"),
    ("Assistant USTR for Congressional Affairs", "ustr"),
    ("Chief of Staff, USTR", "ustr"),

    # CMS
    ("Administrator, CMS", "cms"),
    ("Deputy Administrator, Centers for Medicare and Medicaid Services", "cms"),
    ("Chief of Staff, CMS", "cms"),
]


# ─── NEGATIVE CASES ────────────────────────────────────────────────────────────
# Strings that mention an agency keyword but should NOT classify as a senior
# role at that agency. Most are congressional staff with a passing reference,
# or junior agency positions.
NEGATIVE_CASES = [
    # Junior agency roles — should not be classified (Bridenstine-pattern wants seniority)
    ("Privacy Program Specialist, U.S. Department of Health and Human Services", "hhs"),
    ("Staff Assistant, Department of Energy", "energy"),
    ("Confidential Assistant, Dept of HHS", "hhs"),
    ("Press Office, USAID", "dod"),  # USAID is not DOD

    # Congressional staff merely referencing the agency
    ("Staff Director, Senate Veterans Affairs Committee", "va"),
    ("Counsel, House Energy and Commerce Committee", "energy"),
    ("Chief Counsel, Senate Homeland Security and Gov. Affairs Committee", "dhs"),
    ("Banking Counsel, Sen. Evan Bayh", "cfpb"),
    ("Staff Director, House Ag Approps", "usda"),
    ("Legislative Director for Sen. Lisa Murkowski (lobbying House and DOE only in Q4 2023)", "energy"),
    ("Legislative Assistant, Office of Frank Lucas", "ustr"),

    # Roles at sibling agencies that mention parent department
    ("Director, Federal Aviation Administration", "dot"),  # FAA, not DOT generic — DOT should not match, FAA should
    ("Administrator, FAA", "dot"),                          # same — DOT pattern shouldn't claim this

    # Pure name overlap (no role)
    ("Lobbyist representing tech clients before the FCC", "fcc"),
    ("Consulted on EPA matters", "epa"),
]


# ─── TESTS ─────────────────────────────────────────────────────────────────────

def test_registry_has_all_expected_agencies():
    """The registry must list all 23 expected short names."""
    expected = {
        "nasa", "epa", "fda", "fcc", "sec", "ftc", "dod", "treasury",
        "hhs", "dhs", "interior", "energy", "state", "dot", "faa",
        "ferc", "cftc", "cfpb", "usda", "va", "sba", "omb", "ustr", "cms",
    }
    got = {entry[0] for entry in ac.AGENCY_REGISTRY}
    assert got == expected, f"missing: {expected - got}, extra: {got - expected}"


@pytest.mark.skipif(not DB_PATH.exists(), reason="DB not built")
def test_every_entity_fragment_matches_db():
    """Every entity_fragment must match ≥1 row in senate_gov_entities.entity_name.

    A zero-match fragment silently breaks scan for that agency. This caught
    the original 23-agency audit (all passed, but the test exists so regressions
    on a new corpus rebuild surface immediately).
    """
    import duckdb
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        broken = []
        for short, fragment, _, _ in ac.AGENCY_REGISTRY:
            n = con.execute(
                "SELECT COUNT(*) FROM senate_gov_entities WHERE entity_name ILIKE ?",
                [f"%{fragment}%"],
            ).fetchone()[0]
            if n == 0:
                broken.append((short, fragment))
    assert not broken, (
        "entity_fragments with zero DB matches (scan will return empty for these agencies): "
        + ", ".join(f"{s}={f!r}" for s, f in broken)
    )


@pytest.mark.parametrize("text,expected_agency", POSITIVE_CASES,
                         ids=[f"{ea}::{t[:40]}" for t, ea in POSITIVE_CASES])
def test_positive_cases(text, expected_agency):
    """Each curated senior-role string must classify to its expected agency."""
    matched = {m[0] for m in ac.classify_covered_position(text)}
    assert expected_agency in matched, (
        f"expected {expected_agency!r} in matches, got {matched} for: {text!r}"
    )


@pytest.mark.parametrize("text,forbidden_agency", NEGATIVE_CASES,
                         ids=[f"NOT-{fa}::{t[:40]}" for t, fa in NEGATIVE_CASES])
def test_negative_cases(text, forbidden_agency):
    """Strings that merely reference an agency or hold junior roles must not match."""
    matched = {m[0] for m in ac.classify_covered_position(text)}
    assert forbidden_agency not in matched, (
        f"unexpected match {forbidden_agency!r} in {matched} for: {text!r}"
    )


def test_seniority_scores_in_range():
    """Seniority scores should be 3-5 (3=senior staff, 4=deputy, 5=head)."""
    for short, _, score, _ in ac.AGENCY_REGISTRY:
        assert 3 <= score <= 5, f"{short}: seniority {score} out of range"


def test_no_duplicate_short_names():
    """Each short name must be unique (used as a CLI arg)."""
    shorts = [entry[0] for entry in ac.AGENCY_REGISTRY]
    dups = {s for s in shorts if shorts.count(s) > 1}
    assert not dups, f"duplicate short names: {dups}"


def test_classify_returns_no_match_for_empty():
    assert ac.classify_covered_position("") == []
    assert ac.classify_covered_position(None) == []
    assert ac.classify_covered_position("x") == []  # too short
