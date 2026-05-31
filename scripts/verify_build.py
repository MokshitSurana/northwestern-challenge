#!/usr/bin/env python3
"""
verify_build.py — Post-build invariants for the index (lda-corpus-indexer).

Asserts the DuckDB file at OUTPUT_ROOT/investigation.duckdb has:

  1.  All required tables and views.
  2.  Row counts in expected order-of-magnitude (catches "House lobbyists
      parsed but all-null" type regressions).
  3.  Required columns are non-null at population thresholds (catches
      silently-broken parsers where one field becomes None for every row).
  4.  Sentinel records present (the Bridenstine/Artemis Group anchor must
      always be findable — if it isn't, the parser broke).
  5.  Schema column types match expectations on critical fields.

Exit codes:
  0   all checks passed
  1   one or more checks failed (details printed)

Usage:
    uv run scripts/verify_build.py                # check the standard DB
    OUTPUT_ROOT=output_test uv run scripts/verify_build.py   # check alt DB
    uv run scripts/verify_build.py --strict       # warnings become errors
    uv run scripts/verify_build.py --sample       # use sample-build thresholds
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb

# Force UTF-8 stdout on Windows (the default cp1252 codec chokes on ≤ etc.)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"


# ─── Expected schema ───────────────────────────────────────────────────────────

REQUIRED_TABLES = {
    "press_releases":         (100_000, 200_000),
    "senate_filings":         (300_000, 600_000),
    "senate_activities":      (500_000, 1_200_000),
    "senate_lobbyists":     (1_500_000, 3_000_000),
    "senate_gov_entities":  (1_500_000, 3_000_000),
    "senate_contributions":   (400_000, 1_000_000),
    "senate_foreign_entities":   (1_000,    20_000),
    "house_filings":          (300_000, 600_000),
    "house_activities":       (500_000, 1_200_000),
    "house_lobbyists":      (1_500_000, 3_000_000),
}

REQUIRED_VIEWS = {"revolving_door", "senate_spend_by_issue"}

# (table, column, max_null_fraction) — column must be ≤ this fraction null
NON_NULL_INVARIANTS = [
    ("senate_filings", "filing_uuid", 0.001),
    ("senate_filings", "registrant_name", 0.001),
    ("senate_filings", "filing_year", 0.001),
    ("senate_lobbyists", "filing_uuid", 0.001),
    ("senate_lobbyists", "lobbyist_name", 0.30),  # ~30% null is observed/normal
    ("senate_gov_entities", "filing_uuid", 0.001),
    ("senate_gov_entities", "entity_name", 0.001),
    ("house_filings", "house_id", 0.001),
    ("house_filings", "org_name", 0.05),
    ("house_filings", "filing_year", 0.001),
    ("house_lobbyists", "house_id", 0.001),
    ("house_lobbyists", "lobbyist_name", 0.30),
    ("press_releases", "bioguide_id", 0.30),
    ("press_releases", "text", 0.05),
]

# Sample-mode thresholds are 1/16 of the full build (one quarter per source)
SAMPLE_DIVISOR = 16

# Anchor finding: the Artemis Group must always be queryable, otherwise the
# parser broke a key path.
ANCHOR_QUERIES = [
    (
        "Bridenstine — Artemis Group exists in Senate filings",
        """
        SELECT COUNT(*) FROM senate_filings
        WHERE UPPER(registrant_name) LIKE '%ARTEMIS GROUP%'
        """,
        1,
        None,
    ),
    (
        "Bridenstine — appears as a Senate lobbyist",
        """
        SELECT COUNT(*) FROM senate_lobbyists
        WHERE UPPER(lobbyist_name) LIKE '%BRIDENSTINE%'
        """,
        1,
        None,
    ),
    (
        "House lobbyist names are populated (not all-null)",
        """
        SELECT COUNT(*) FROM house_lobbyists WHERE lobbyist_name IS NOT NULL
        """,
        100_000,
        None,
    ),
    (
        "NASA appears as a Senate gov entity",
        """
        SELECT COUNT(*) FROM senate_gov_entities WHERE entity_name ILIKE '%Aeronautics%'
        """,
        100,
        None,
    ),
]


# ─── Check helpers ─────────────────────────────────────────────────────────────

class Checker:
    def __init__(self, sample: bool):
        self.sample = sample
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.passes: list[str] = []

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def ok(self, msg: str) -> None:
        self.passes.append(msg)

    def thresh(self, lo: int, hi: int) -> tuple[int, int]:
        if self.sample:
            return (max(10, lo // SAMPLE_DIVISOR), hi)
        return (lo, hi)


def check_tables(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    present = {r[0] for r in rows}

    missing = set(REQUIRED_TABLES) - present
    for t in missing:
        ck.err(f"missing required table: {t}")

    for t, (lo, hi) in REQUIRED_TABLES.items():
        if t in missing:
            continue
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        lo_s, hi_s = ck.thresh(lo, hi)
        if n < lo_s:
            ck.err(f"{t}: {n:,} rows — below expected min {lo_s:,}")
        elif n > hi_s and not ck.sample:
            ck.warn(f"{t}: {n:,} rows — above expected max {hi_s:,} (corpus may have grown — investigate)")
        else:
            ck.ok(f"{t}: {n:,} rows in expected range")


def check_views(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW' AND table_schema='main'"
    ).fetchall()
    present = {r[0] for r in rows}
    for v in REQUIRED_VIEWS:
        if v not in present:
            ck.err(f"missing convenience view: {v}")
        else:
            n = con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
            ck.ok(f"view {v}: {n:,} rows")


def check_non_null(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    """For each (table, column, max_null_fraction), assert null fraction is below threshold."""
    for table, col, max_null in NON_NULL_INVARIANTS:
        try:
            n_total, n_null = con.execute(f"""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS nulls
                FROM {table}
            """).fetchone()
        except duckdb.CatalogException:
            ck.err(f"non-null check skipped — table {table} missing")
            continue
        if n_total == 0:
            ck.err(f"{table}.{col}: 0 rows (table is empty)")
            continue
        frac = (n_null or 0) / n_total
        if frac > max_null:
            ck.err(
                f"{table}.{col}: {frac:.1%} null — above threshold {max_null:.1%} "
                f"(parser likely broken)"
            )
        else:
            ck.ok(f"{table}.{col}: {frac:.1%} null (≤ {max_null:.1%})")


def check_anchors(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    """Sentinel queries — if these return zero, something parser-level broke."""
    for label, query, min_count, max_count in ANCHOR_QUERIES:
        # Anchors are full-corpus invariants; skip in sample mode where
        # specific named entities may not appear.
        if ck.sample:
            continue
        n = con.execute(query).fetchone()[0]
        if n < min_count:
            ck.err(f"anchor failed: {label} → {n} rows (expected ≥ {min_count})")
        elif max_count is not None and n > max_count:
            ck.err(f"anchor failed: {label} → {n} rows (expected ≤ {max_count})")
        else:
            ck.ok(f"anchor: {label} → {n} rows")


def check_critical_types(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    """Type sanity — filing_year must be integer-castable, income must be numeric."""
    try:
        bad = con.execute("""
            SELECT COUNT(*) FROM senate_filings
            WHERE filing_year IS NOT NULL AND TRY_CAST(filing_year AS INTEGER) IS NULL
        """).fetchone()[0]
        if bad:
            ck.err(f"senate_filings.filing_year: {bad} rows fail integer cast")
        else:
            ck.ok("senate_filings.filing_year: all integer-castable")
    except duckdb.CatalogException:
        pass

    try:
        bad_income = con.execute("""
            SELECT COUNT(*) FROM senate_filings
            WHERE income IS NOT NULL AND TRY_CAST(income AS DOUBLE) IS NULL
        """).fetchone()[0]
        if bad_income:
            ck.err(f"senate_filings.income: {bad_income} rows fail numeric cast")
        else:
            ck.ok("senate_filings.income: all numeric-castable")
    except duckdb.CatalogException:
        pass


def check_join_keys(con: duckdb.DuckDBPyConnection, ck: Checker) -> None:
    """Foreign-key style invariants — every senate_lobbyists.filing_uuid must
    refer to a filing in senate_filings."""
    orphan = con.execute("""
        SELECT COUNT(*) FROM senate_lobbyists sl
        WHERE NOT EXISTS (
            SELECT 1 FROM senate_filings sf WHERE sf.filing_uuid = sl.filing_uuid
        )
    """).fetchone()[0]
    if orphan > 0:
        ck.err(f"senate_lobbyists: {orphan:,} rows reference unknown filing_uuid")
    else:
        ck.ok("senate_lobbyists: every filing_uuid joins to senate_filings")

    orphan_h = con.execute("""
        SELECT COUNT(*) FROM house_lobbyists hl
        WHERE NOT EXISTS (
            SELECT 1 FROM house_filings hf WHERE hf.house_id = hl.house_id
        )
    """).fetchone()[0]
    if orphan_h > 0:
        ck.err(f"house_lobbyists: {orphan_h:,} rows reference unknown house_id")
    else:
        ck.ok("house_lobbyists: every house_id joins to house_filings")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--strict", action="store_true", help="Promote warnings to errors")
    p.add_argument("--sample", action="store_true", help="Use sample-build thresholds")
    p.add_argument("--quiet", action="store_true", help="Print only failures and summary")
    args = p.parse_args()

    if not DB_PATH.exists():
        print(f"FAIL: DB not found: {DB_PATH}")
        print("      Build it first: uv run scripts/01_build_index.py")
        print("      Or download pre-built output/ from the Drive link in README.md.")
        return 1

    print(f"Verifying {DB_PATH}  (mode: {'sample' if args.sample else 'full'})")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ck = Checker(sample=args.sample)

    check_tables(con, ck)
    check_views(con, ck)
    check_non_null(con, ck)
    check_critical_types(con, ck)
    check_join_keys(con, ck)
    check_anchors(con, ck)
    con.close()

    if not args.quiet:
        for line in ck.passes:
            print(f"  PASS  {line}")
    for line in ck.warnings:
        print(f"  WARN  {line}")
    for line in ck.errors:
        print(f"  FAIL  {line}")

    n_fail = len(ck.errors) + (len(ck.warnings) if args.strict else 0)
    n_pass = len(ck.passes)

    print()
    print(f"  Summary: {n_pass} passed, {len(ck.warnings)} warning(s), {len(ck.errors)} failure(s)")
    if n_fail:
        return 1
    print("  Build verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
