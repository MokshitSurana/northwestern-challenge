"""
Diagnostic: verify every entity_fragment in AGENCY_REGISTRY actually matches
rows in senate_gov_entities.entity_name. Any zero-match agency is silently
scoring zero candidates.

Also dumps a sample of distinct entity_name values per fragment so we can
audit whether the substring is the right substring.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Import AGENCY_REGISTRY without running __main__
import importlib.util

spec = importlib.util.spec_from_file_location("ac", Path(__file__).parent / "03_agency_concentration.py")
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)

import duckdb

DB = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"
con = duckdb.connect(str(DB), read_only=True)

print(f"{'short':<10}  {'frag-match-count':>16}  example entity_name (top-1)")
print("-" * 100)
broken = []
for short, fragment, score, patterns in ac.AGENCY_REGISTRY:
    n = con.execute(
        "SELECT COUNT(DISTINCT entity_name) FROM senate_gov_entities WHERE entity_name ILIKE ?",
        [f"%{fragment}%"]
    ).fetchone()[0]
    if n == 0:
        broken.append((short, fragment))
        sample = "  <<< NO MATCH >>>"
    else:
        sample_row = con.execute(
            "SELECT entity_name, COUNT(*) c FROM senate_gov_entities WHERE entity_name ILIKE ? GROUP BY entity_name ORDER BY c DESC LIMIT 1",
            [f"%{fragment}%"]
        ).fetchone()
        sample = f"{sample_row[0]!r} ({sample_row[1]:,} rows)"
    print(f"{short:<10}  {n:>16,}  {sample}")

if broken:
    print("\n*** BROKEN ENTITY FRAGMENTS ***")
    for short, fragment in broken:
        print(f"  {short}: fragment={fragment!r}")
        candidates = con.execute(
            "SELECT entity_name, COUNT(*) c FROM senate_gov_entities WHERE entity_name ILIKE ? GROUP BY entity_name ORDER BY c DESC LIMIT 5",
            [f"%{short}%"]
        ).fetchall()
        if candidates:
            print(f"    suggestions matching '{short}':")
            for e, c in candidates:
                print(f"      {e!r}  ({c:,} rows)")
else:
    print("\nAll fragments matched.")
