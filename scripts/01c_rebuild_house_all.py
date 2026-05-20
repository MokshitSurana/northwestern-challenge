#!/usr/bin/env python3
"""
01c_rebuild_house_all.py — combined rebuild of house_lobbyists + house_activities
+ house_filings Parquets, with the corrected XML parsing.

Use this after patching parse_house_xml in 01_build_index.py.
Rebuilds all three House Parquet tables in one XML pass (~2 hours).

Then run:
    uv run scripts/01_build_index.py --duckdb-only
"""

import os
import sys
import time
from pathlib import Path

import polars as pl
from tqdm import tqdm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Import the fixed parser from the main indexer
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
_indexer = import_module("01_build_index")
parse_house_xml      = _indexer.parse_house_xml
parse_house_dir_name = _indexer.parse_house_dir_name

DATA_ROOT   = Path(os.environ.get("DATA_ROOT",   "data/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))
PARQUET_DIR = OUTPUT_ROOT / "parquet"
HOUSE_ROOT  = DATA_ROOT / "house"

FILINGS_SCHEMA = {
    "house_id":              pl.Utf8,
    "senate_id":             pl.Utf8,
    "filing_year":           pl.Int64,
    "filing_period":         pl.Utf8,
    "org_name":              pl.Utf8,
    "client_name":           pl.Utf8,
    "client_is_govt_entity": pl.Utf8,
    "income":                pl.Float64,
    "expenses":              pl.Float64,
    "no_lobbying":           pl.Utf8,
    "termination_date":      pl.Utf8,
    "signed_date":           pl.Utf8,
    "report_year":           pl.Utf8,
    "report_type":           pl.Utf8,
    "source_path":           pl.Utf8,
}

ACTIVITIES_SCHEMA = {
    "house_id":     pl.Utf8,
    "activity_idx": pl.Int64,
    "ali_code":     pl.Utf8,
    "description":  pl.Utf8,
    "source_path":  pl.Utf8,
}

LOBBYISTS_SCHEMA = {
    "house_id":         pl.Utf8,
    "activity_idx":     pl.Int64,
    "lobbyist_name":    pl.Utf8,
    "covered_position": pl.Utf8,
    "is_new":           pl.Utf8,
    "source_path":      pl.Utf8,
}


def write_parquet(records, path, label, schema):
    if not records:
        df = pl.DataFrame(schema=schema)
        df.write_parquet(path, compression="zstd")
        print(f"    [ok]   {label}: 0 rows (empty, schema preserved)")
        return 0
    df = pl.DataFrame(records, schema_overrides=schema, infer_schema_length=min(len(records), 500))
    df.write_parquet(path, compression="zstd")
    size_kb = path.stat().st_size // 1024
    print(f"    [ok]   {label}: {len(df):,} rows  ({size_kb:,} KB)")
    return len(df)


def main():
    if not HOUSE_ROOT.exists():
        print(f"ERROR: HOUSE_ROOT not found: {HOUSE_ROOT}", file=sys.stderr)
        return 1

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    for pattern in ("house_filings_*.parquet", "house_activities_*.parquet",
                    "house_lobbyists_*.parquet"):
        stale = sorted(PARQUET_DIR.glob(pattern))
        print(f"[CLEAN] removing {len(stale)} stale {pattern} files")
        for p in stale:
            p.unlink()

    xml_dirs = sorted(HOUSE_ROOT.glob("*_XML"))
    print(f"[PARSE] {len(xml_dirs)} House XML directories")

    t_start = time.time()
    total_f = total_a = total_l = 0
    errors = 0

    for xml_dir in xml_dirs:
        year, period = parse_house_dir_name(xml_dir.name)
        xml_files = sorted(xml_dir.glob("*.xml"))
        print(f"\n  {xml_dir.name}: {len(xml_files):,} files")

        filings, activities, lobbyists = [], [], []
        for xml_path in tqdm(xml_files, desc=f"  {xml_dir.name}", leave=False, unit="file"):
            f, acts, lobs = parse_house_xml(xml_path, year, period)
            if f is None:
                errors += 1
                continue
            filings.append(f)
            activities.extend(acts)
            lobbyists.extend(lobs)

        tag = f"{year}_{period}"
        total_f += write_parquet(filings,    PARQUET_DIR / f"house_filings_{tag}.parquet",    f"house_filings_{tag}",    FILINGS_SCHEMA)
        total_a += write_parquet(activities, PARQUET_DIR / f"house_activities_{tag}.parquet", f"house_activities_{tag}", ACTIVITIES_SCHEMA)
        total_l += write_parquet(lobbyists,  PARQUET_DIR / f"house_lobbyists_{tag}.parquet",  f"house_lobbyists_{tag}",  LOBBYISTS_SCHEMA)

    if errors:
        print(f"\n[WARN] {errors} XML parse errors")

    elapsed = (time.time() - t_start) / 60
    print(f"\n[DONE] in {elapsed:.1f} minutes")
    print(f"   house_filings:    {total_f:,} rows")
    print(f"   house_activities: {total_a:,} rows")
    print(f"   house_lobbyists:  {total_l:,} rows")
    print(f"\nNext: uv run scripts/01_build_index.py --duckdb-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())