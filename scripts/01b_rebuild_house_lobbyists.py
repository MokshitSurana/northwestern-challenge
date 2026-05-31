#!/usr/bin/env python3
"""
01b_rebuild_house_lobbyists.py — targeted rebuild of house_lobbyists Parquets.

After patching 01_build_index.py with schema_overrides for House writes,
the existing house_lobbyists_*.parquet files are still typed wrong on disk.
This script regenerates ONLY those files by re-parsing the House XML.

After running this, do:
    uv run scripts/01_build_index.py --duckdb-only

to rebuild the DuckDB from the corrected Parquet files.

Usage:
    uv run scripts/01b_rebuild_house_lobbyists.py

Environment variables:
    DATA_ROOT    path to data root (default: data, override if nested e.g. data/data)
    OUTPUT_ROOT  path for output files (default: output)
"""

import os
import sys
import time
from pathlib import Path

import polars as pl
from lxml import etree
from tqdm import tqdm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────

DATA_ROOT   = Path(os.environ.get("DATA_ROOT",   "data/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))
PARQUET_DIR = OUTPUT_ROOT / "parquet"
HOUSE_ROOT  = DATA_ROOT / "house"

PERIOD_MAP = {
    "Registrations": "Registrations",
    "1stQuarter":    "Q1",
    "2ndQuarter":    "Q2",
    "3rdQuarter":    "Q3",
    "4thQuarter":    "Q4",
}

LOBBYISTS_SCHEMA = {
    "house_id":         pl.Utf8,
    "lobbyist_name":    pl.Utf8,
    "covered_position": pl.Utf8,
    "is_new":           pl.Utf8,
    "source_path":      pl.Utf8,
}


def safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_house_dir_name(dirname: str) -> tuple[int, str]:
    parts = dirname.replace("_XML", "").split("_", 1)
    year   = int(parts[0])
    period = PERIOD_MAP.get(parts[1], parts[1]) if len(parts) > 1 else "Unknown"
    return year, period


def extract_lobbyists(path: Path) -> list[dict]:
    """Re-extract just the lobbyists from a House XML file."""
    source_path = str(path)
    try:
        tree = etree.parse(str(path))
        root = tree.getroot()
    except Exception:
        return []

    house_id = safe_str(path.stem)
    lobbyists = []
    for lob_el in root.findall(".//lobbyists/lobbyist"):
        # House XML uses first/last name fields, not a single lobbyistName tag
        first  = safe_str(lob_el.findtext("lobbyistFirstName"))
        last   = safe_str(lob_el.findtext("lobbyistLastName"))
        suffix = safe_str(lob_el.findtext("lobbyistSuffix"))
        name   = " ".join(filter(None, [first, last, suffix])) or None
        # Legacy fallback for older filings that used the combined tag
        if not name:
            name = safe_str(lob_el.findtext("lobbyistName"))
        cov  = safe_str(lob_el.findtext("coveredPosition"))
        if name or cov:
            lobbyists.append({
                "house_id":         house_id,
                "lobbyist_name":    name,
                "covered_position": cov,
                "is_new":           safe_str(lob_el.findtext("lobbyistNew")),
                "source_path":      source_path,
            })
    return lobbyists


def write_house_lobbyists_parquet(records: list[dict], tag: str) -> int:
    """Write house_lobbyists_<tag>.parquet with explicit schema."""
    path = PARQUET_DIR / f"house_lobbyists_{tag}.parquet"
    if not records:
        # Write an empty file with the right schema so the DuckDB glob still picks it up
        df = pl.DataFrame(schema=LOBBYISTS_SCHEMA)
        df.write_parquet(path, compression="zstd")
        print(f"    [ok]   house_lobbyists_{tag}: 0 rows  (empty, schema preserved)")
        return 0
    df = pl.DataFrame(
        records,
        schema_overrides=LOBBYISTS_SCHEMA,
        infer_schema_length=min(len(records), 500),
    )
    df.write_parquet(path, compression="zstd")
    size_kb = path.stat().st_size // 1024
    print(f"    [ok]   house_lobbyists_{tag}: {len(df):,} rows  ({size_kb:,} KB)")
    return len(df)


def main() -> int:
    if not HOUSE_ROOT.exists():
        print(f"ERROR: HOUSE_ROOT not found: {HOUSE_ROOT}", file=sys.stderr)
        print("Set DATA_ROOT if your data lives elsewhere.", file=sys.stderr)
        return 1

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    # ── Delete only the affected Parquets ───────────────────────────────────
    stale = sorted(PARQUET_DIR.glob("house_lobbyists_*.parquet"))
    print(f"[CLEAN] removing {len(stale)} stale house_lobbyists_*.parquet files")
    for p in stale:
        p.unlink()

    # ── Re-parse XML, write fresh Parquets ──────────────────────────────────
    xml_dirs = sorted(HOUSE_ROOT.glob("*_XML"))
    print(f"[PARSE] {len(xml_dirs)} House XML directories")

    t_start = time.time()
    total = 0
    parse_errors = 0

    for xml_dir in xml_dirs:
        year, period = parse_house_dir_name(xml_dir.name)
        xml_files = sorted(xml_dir.glob("*.xml"))
        print(f"\n  {xml_dir.name}: {len(xml_files):,} files")

        lobbyists: list[dict] = []
        for xml_path in tqdm(xml_files, desc=f"  {xml_dir.name}", leave=False, unit="file"):
            try:
                lobbyists.extend(extract_lobbyists(xml_path))
            except Exception:
                parse_errors += 1

        tag = f"{year}_{period}"
        total += write_house_lobbyists_parquet(lobbyists, tag)

    if parse_errors:
        print(f"\n[WARN] {parse_errors} XML parse errors")

    elapsed = (time.time() - t_start) / 60
    print(f"\n[DONE] {total:,} lobbyist rows in {elapsed:.1f} minutes")
    print("\nNext step:")
    print("    uv run scripts/01_build_index.py --duckdb-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
