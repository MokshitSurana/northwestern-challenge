"""Rebuild just the senate_lobbyists Parquet + DuckDB table with fixed name parsing."""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path

import duckdb

# Pull in helpers by exec-ing the build script up to the __main__ guard
exec(compile(open("scripts/01_build_index.py", encoding="utf-8").read().split("if __name__")[0],
             "scripts/01_build_index.py", "exec"))

years = [2022, 2023, 2024, 2025, 2026]
for year in years:
    fpath = SENATE_ROOT / str(year) / "filings" / f"filings_{year}.json"
    if not fpath.exists():
        print(f"Missing: {fpath}")
        continue
    _, _, lobbyists, _, _ = parse_senate_filings_file(fpath)
    write_parquet(lobbyists, PARQUET_DIR / f"senate_lobbyists_{year}.parquet", f"senate_lobbyists_{year}")

print("\nRebuilding DuckDB senate_lobbyists table...")
DB_FILE = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"
con = duckdb.connect(str(DB_FILE))
glob_path = str(PARQUET_DIR / "senate_lobbyists_*.parquet").replace("\\", "/")
con.execute("DROP TABLE IF EXISTS senate_lobbyists")
con.execute(f"CREATE TABLE senate_lobbyists AS SELECT * FROM read_parquet('{glob_path}', union_by_name=True)")
count    = con.execute("SELECT COUNT(*) FROM senate_lobbyists").fetchone()[0]
has_name = con.execute("SELECT COUNT(lobbyist_name) FROM senate_lobbyists").fetchone()[0]
print(f"senate_lobbyists: {count:,} rows, {has_name:,} with name ({100*has_name/count:.1f}%)")

con.execute("""
    CREATE OR REPLACE VIEW revolving_door AS
    SELECT sl.filing_uuid, sf.filing_year, sf.filing_period,
           sf.registrant_name, sf.client_name,
           sl.lobbyist_name, sl.covered_position, sf.income, sf.expenses
    FROM senate_lobbyists sl
    JOIN senate_filings sf USING (filing_uuid)
    WHERE sl.covered_position IS NOT NULL AND sl.covered_position != ''
""")
con.close()
print("Done.")
