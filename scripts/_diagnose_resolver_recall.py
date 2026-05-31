"""Show resolver positive pairs that fail to cluster."""
import sys
from itertools import combinations
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location("er", Path(__file__).parent / "02_entity_resolver.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)

con = duckdb.connect("output/investigation.duckdb", read_only=True)
pairs: list[tuple[str, str]] = []
for _, names in con.execute("""
    SELECT registrant_id, list(DISTINCT registrant_name) AS names FROM senate_filings
    WHERE registrant_id IS NOT NULL AND registrant_name IS NOT NULL
    GROUP BY registrant_id HAVING COUNT(DISTINCT registrant_name) > 1
""").fetchall():
    for a, b in combinations(list(set(names)), 2):
        pairs.append((a, b))

for _, _, names in con.execute("""
    SELECT registrant_id, client_id, list(DISTINCT client_name) AS names FROM senate_filings
    WHERE registrant_id IS NOT NULL AND client_id IS NOT NULL AND client_name IS NOT NULL
    GROUP BY 1, 2 HAVING COUNT(DISTINCT client_name) > 1
""").fetchall():
    for a, b in combinations(list(set(names)), 2):
        pairs.append((a, b))

names_set = sorted({n for p in pairs for n in p})
mapping = {m["raw_name"]: m for m in er.resolve_orgs(names_set, threshold=92)}

print(f"Total positive pairs: {len(pairs)}")
print()
print("=== MISSED (positive pairs that didn't cluster) ===")
n_missed = 0
for a, b in pairs:
    if mapping.get(a, {}).get("cluster_id") != mapping.get(b, {}).get("cluster_id"):
        n_missed += 1
        na = er.normalize_org(a)
        nb = er.normalize_org(b)
        print(f"  a={a!r}\n  b={b!r}\n  na={na!r}\n  nb={nb!r}")
        from rapidfuzz import fuzz
        print(f"  token_sort={fuzz.token_sort_ratio(na, nb)}  ratio={fuzz.ratio(na, nb)}  partial={fuzz.partial_ratio(na, nb)}")
        print()
        if n_missed >= 20:
            break
print(f"Showed first 20 of {sum(1 for a,b in pairs if mapping.get(a,{}).get('cluster_id') != mapping.get(b,{}).get('cluster_id'))} misses")
