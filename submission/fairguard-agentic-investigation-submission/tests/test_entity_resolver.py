"""
Tests for entity-resolver (scripts/02_entity_resolver.py).

Layers:

  1.  Unit tests for normalize_org and normalize_person — ensure the normalizer
      handles the spelling variants we know about (LLC vs L.L.C., "The" prefix,
      comma vs no-comma, FKA aliases).

  2.  Hand-curated positive and negative test cases — small, fast, deterministic.

  3.  Optional DB-backed F1 eval — harvest positive pairs from registrant_id
      collisions and easy negative pairs from disjoint ids. Skipped if no DB.
      Targets F1 ≥ 0.92 per the SKILL.md spec.

Run:
    uv run pytest tests/test_entity_resolver.py -v
    uv run pytest tests/test_entity_resolver.py::test_f1_on_db -v  (slower)
"""
import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "entity-resolver" / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("er", ROOT / "skills" / "entity-resolver" / "scripts" / "02_entity_resolver.py")
er = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(er)

DB_PATH = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"


# ─── normalize_org ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b", [
    ("MICROSOFT CORP", "Microsoft Corporation"),
    ("Microsoft Corp.", "MICROSOFT CORP"),
    ("Microsoft, Inc.", "Microsoft Inc"),
    ("Apple Inc.", "APPLE, INC."),
    ("THE ARTEMIS GROUP, LLC", "Artemis Group LLC"),
    ("Ballard Partners, LLC", "BALLARD PARTNERS"),
    ("Smart Policy Group", "SMART POLICY GROUP LLC"),
    ("American Defense International", "AMERICAN DEFENSE INTERNATIONAL, INC."),
    ("K&L Gates LLP", "K&L GATES, LLP"),
    ("BROOKS BAWDEN MOORE, LLC", "BROOKS BAWDEN MOORE, LLC, FORMERLY REPORTED AS BROOKS BAWDEN, LLC"),
])
def test_normalize_org_treats_as_same(a, b):
    """These pairs should normalize to identical strings."""
    assert er.normalize_org(a) == er.normalize_org(b), \
        f"{a!r} → {er.normalize_org(a)!r}  vs  {b!r} → {er.normalize_org(b)!r}"


@pytest.mark.parametrize("a,b", [
    ("Microsoft Corp", "Apple Corp"),                             # different orgs
    ("Ferguson Group LLC", "Ferguson & Associates LLC"),          # superficially similar
    ("Brooks Bawden Moore LLC", "Brooks Pierce LLP"),             # share one word
    ("The Artemis Group", "The Hermes Group"),                    # both "The ... Group"
    ("Smart Policy Group", "Smart Energy Coalition"),             # share "Smart"
])
def test_normalize_org_treats_as_different(a, b):
    """These pairs should NOT normalize to the same string."""
    assert er.normalize_org(a) != er.normalize_org(b), \
        f"unexpected match: {a!r} and {b!r} both → {er.normalize_org(a)!r}"


def test_normalize_org_strips_leading_the():
    assert er.normalize_org("The Artemis Group") == er.normalize_org("Artemis Group")


def test_normalize_org_handles_alias_marker():
    assert er.normalize_org("INFLECTION POINT (FKA ARISTOTLE INTERNATIONAL, INC.)") == "inflection point"


def test_normalize_org_empty_safe():
    assert er.normalize_org("") == ""
    assert er.normalize_org(None) == ""


# ─── normalize_person ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b", [
    ("Smith, John", "John Smith"),
    ("Smith, John A.", "John A. Smith"),
    ("Bridenstine, James", "James Bridenstine"),
    ("BRIDENSTINE, JIM", "Jim Bridenstine"),
    ("John Smith Jr.", "John Smith"),
    ("Dr. John Smith", "John Smith"),
    ("Smith, John Q.", "John Quincy Smith"),  # middle initial vs full middle
])
def test_normalize_person_treats_as_same(a, b):
    """Last + first should match across formats."""
    na = er.normalize_person(a)
    nb = er.normalize_person(b)
    assert (na[0], na[1]) == (nb[0], nb[1]), f"{a!r} → {na}  vs  {b!r} → {nb}"


@pytest.mark.parametrize("a,b", [
    ("John Smith", "Jane Smith"),
    ("Mark Piland", "Gabe Sherman"),
    ("Jim Bridenstine", "Jane Bridenstine"),  # same last, different first
])
def test_normalize_person_treats_as_different(a, b):
    na = er.normalize_person(a)
    nb = er.normalize_person(b)
    assert (na[0], na[1]) != (nb[0], nb[1])


def test_normalize_person_empty_safe():
    assert er.normalize_person("") == ("", "", "")
    assert er.normalize_person(None) == ("", "", "")


# ─── End-to-end resolve_orgs on a curated mini-set ─────────────────────────────

def test_resolve_orgs_curated_cluster():
    """The 'Artemis Group' family must collapse into one cluster."""
    names = [
        "THE ARTEMIS GROUP, LLC",
        "The Artemis Group, LLC (Oklahoma)",
        "Artemis Group LLC",
        "ARTEMIS GROUP, LLC",
        # distractors:
        "ARTEMIS HEALTH POLICIES",
        "ARTEMIS REAL ESTATE PARTNERS",
        "K&L GATES LLP",
    ]
    out = er.resolve_orgs(names, threshold=92)
    by_raw = {m["raw_name"]: m for m in out}
    artemis_cluster = by_raw["THE ARTEMIS GROUP, LLC"]["cluster_id"]
    assert by_raw["Artemis Group LLC"]["cluster_id"] == artemis_cluster
    assert by_raw["ARTEMIS GROUP, LLC"]["cluster_id"] == artemis_cluster
    # distractor must not merge in
    assert by_raw["ARTEMIS HEALTH POLICIES"]["cluster_id"] != artemis_cluster


def test_resolve_orgs_singleton_marked():
    """A unique name in its own cluster should be marked 'singleton'."""
    out = er.resolve_orgs(["UNIQUE EXAMPLE ENTITY ZZZZ"])
    assert len(out) == 1
    assert out[0]["match_method"] == "singleton"
    assert out[0]["n_variants"] == 1


def test_resolve_people_curated_cluster():
    """Same person under multiple spellings should collapse."""
    names = [
        "Bridenstine, James",
        "Bridenstine, Jim",
        "James Bridenstine",
        "Jim Bridenstine",
        # distractor:
        "Bridenstine, Jane",
        "John Smith",
    ]
    out = er.resolve_people(names)
    by_raw = {m["raw_name"]: m for m in out}
    jim_cluster = by_raw["Bridenstine, Jim"]["cluster_id"]
    # Bridenstine James and Jim should NOT cluster (different first names)
    # but James <-> James should be same cluster
    assert by_raw["James Bridenstine"]["cluster_id"] == by_raw["Bridenstine, James"]["cluster_id"]
    assert by_raw["Jim Bridenstine"]["cluster_id"] == jim_cluster
    # Distractor with different first name must not merge
    assert by_raw["Bridenstine, Jane"]["cluster_id"] != jim_cluster
    assert by_raw["John Smith"]["cluster_id"] != jim_cluster


# ─── F1 eval against DB (harvest positive labels from registrant_id) ───────────

def _harvest_positive_org_pairs(con, max_pairs: int = 200) -> list[tuple[str, str]]:
    """Pairs of (name_a, name_b) sharing a stable id — should resolve to one cluster.

    Pulls from two sources of free labels:
      a) Multi-name registrants (registrant_id stable; registrant_name varies)
      b) Multi-name clients within a registrant (registrant_id + client_id
         stable; client_name varies)

    Enumerates all pairwise combinations (up to max_pairs).
    """
    from itertools import combinations

    pairs = []

    # (a) Registrants with multiple name spellings
    reg_rows = con.execute("""
        SELECT registrant_id, list(DISTINCT registrant_name) AS names
        FROM senate_filings
        WHERE registrant_id IS NOT NULL AND registrant_name IS NOT NULL
        GROUP BY registrant_id HAVING COUNT(DISTINCT registrant_name) > 1
    """).fetchall()
    for _, names in reg_rows:
        for a, b in combinations(list(set(names)), 2):
            pairs.append((a, b))
            if len(pairs) >= max_pairs:
                return pairs

    # (b) Clients with multiple name spellings under the same registrant
    cli_rows = con.execute("""
        SELECT registrant_id, client_id, list(DISTINCT client_name) AS names
        FROM senate_filings
        WHERE registrant_id IS NOT NULL AND client_id IS NOT NULL AND client_name IS NOT NULL
        GROUP BY 1, 2 HAVING COUNT(DISTINCT client_name) > 1
    """).fetchall()
    for _, _, names in cli_rows:
        for a, b in combinations(list(set(names)), 2):
            pairs.append((a, b))
            if len(pairs) >= max_pairs:
                return pairs

    return pairs


def _harvest_negative_org_pairs(con, max_pairs: int = 200, seed: int = 17) -> list[tuple[str, str]]:
    """Pairs of names from disjoint registrant_ids — should NOT resolve to one cluster.

    Picks names with non-trivial overlap (share a first token) to test the
    fuzzy matcher's discrimination on hard negatives.
    """
    rows = con.execute("""
        SELECT DISTINCT registrant_id, registrant_name
        FROM senate_filings
        WHERE registrant_id IS NOT NULL AND registrant_name IS NOT NULL
        LIMIT 5000
    """).fetchall()
    rng = random.Random(seed)
    by_first_tok: dict[str, list[tuple[int, str]]] = {}
    for rid, name in rows:
        tok = name.lower().split(" ", 1)[0]
        by_first_tok.setdefault(tok, []).append((rid, name))
    pairs: list[tuple[str, str]] = []
    for tok, members in by_first_tok.items():
        if len(members) < 2:
            continue
        rng.shuffle(members)
        for i in range(len(members) - 1):
            (id_a, na), (id_b, nb) = members[i], members[i + 1]
            if id_a == id_b:
                continue
            pairs.append((na, nb))
            if len(pairs) >= max_pairs:
                return pairs
    return pairs


@pytest.mark.skipif(not DB_PATH.exists(), reason="DB not built")
def test_f1_on_db():
    """Bootstrap positive labels from registrant_id collisions; assert F1 ≥ 0.92.

    This is the headline metric from skill/entity-resolver/SKILL.md.
    """
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    positives = _harvest_positive_org_pairs(con, max_pairs=200)
    negatives = _harvest_negative_org_pairs(con, max_pairs=200)
    con.close()

    assert len(positives) >= 50, f"too few positive pairs harvested: {len(positives)}"
    assert len(negatives) >= 50, f"too few negative pairs harvested: {len(negatives)}"

    # Resolve all names in one batch so the union-find runs across the whole set
    all_names: list[str] = []
    for a, b in positives + negatives:
        all_names.extend([a, b])
    mappings = er.resolve_orgs(list(set(all_names)), threshold=92)
    cluster_of = {m["raw_name"]: m["cluster_id"] for m in mappings}

    def same_cluster(a, b):
        return cluster_of.get(a) == cluster_of.get(b)

    tp = sum(1 for a, b in positives if same_cluster(a, b))
    fn = len(positives) - tp
    fp = sum(1 for a, b in negatives if same_cluster(a, b))
    tn = len(negatives) - fp

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0

    print(f"\nResolver eval ({len(positives)} pos, {len(negatives)} neg):")
    print(f"  TP={tp}  FN={fn}  FP={fp}  TN={tn}")
    print(f"  Precision = {precision:.3f}")
    print(f"  Recall    = {recall:.3f}")
    print(f"  F1        = {f1:.3f}")

    assert f1 >= 0.92, f"F1={f1:.3f} below 0.92 target"
