# Trace — `/fair-guard resolve`

**Date:** 2026-05-30
**Skill invoked:** `resolve` (entity-resolver)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** entity_map table written to investigation.duckdb. F1 = 0.963 against the auto-harvested eval set.

---

## Invocation

User typed `/fair-guard resolve` in Claude Code.

Dispatcher checked the DB prerequisite (`output/investigation.duckdb` exists) and routed to `skill/entity-resolver/SKILL.md`, which instructs the agent to run:

```bash
uv run scripts/02_entity_resolver.py
```

## Output (verbatim)

```
============================================================
FairGuard — entity resolver
============================================================
DB: output\investigation.duckdb

Resolving organizations…
  Pulled 68,914 distinct org strings
  → 28,851 clusters

Resolving people…
  Pulled 41,702 distinct person strings
  → 22,518 clusters

  Total raw rows:           110,598
  Unique clusters:           51,369
  Compression ratio:           2.15x
  Entity types:
    organization        68,914
    person              41,684
  Match methods:
    normalized_exact         95,798
    singleton                 8,002
    fuzzy_low                 6,285
    fuzzy_high                  513

Writing entity_map…
  entity_map row count: 110,598
```

## Interpretation

| Stat | Value | Reading |
|---|---|---|
| Total raw rows | 110,598 | One row per (distinct raw string × entity_type) |
| Clusters | 51,369 | ~half the strings are non-trivial duplicates of another |
| Compression | 2.15× | Average 2.15 spellings per real entity |
| `normalized_exact` | 95,798 | High share — most variation is suffix/case/comma noise |
| `fuzzy_high` / `fuzzy_low` | 513 / 6,285 | The harder cases — token-sort and last-name fuzzy matches |
| `singleton` | 8,002 | Names that appear under only one spelling in the corpus |

The `entity_map` table is now queryable:

```sql
-- Count distinct firms after resolution
SELECT COUNT(DISTINCT cluster_id) AS canonical_firms
FROM entity_map WHERE entity_type = 'organization';
-- → 28,851 (vs. 68,914 raw strings)
```

## Verification — F1 eval

After the resolver wrote the `entity_map` table, the verification step ran
the auto-harvested F1 eval to confirm quality:

```bash
uv run pytest tests/test_entity_resolver.py -v
```

Output (abbreviated):

```
Resolver eval (97 pos, 200 neg):
  TP=90  FN=7  FP=0  TN=200
  Precision = 1.000
  Recall    = 0.928
  F1        = 0.963

============================= 33 passed in 0.35s =============================
```

### Eval set construction

- **Positive labels** are harvested for free from the corpus itself: pairs
  of names sharing a stable identifier. Specifically:
  - 33 multi-name registrants (`senate_filings.registrant_id` with > 1
    distinct `registrant_name`).
  - 64 multi-name clients within a registrant (`(registrant_id, client_id)`
    with > 1 distinct `client_name`).
  - Total: 97 positive pairs.
- **Negative labels** are 200 hard-negative pairs — names from *distinct*
  registrant_ids that share their first token (high lexical overlap, easy
  to false-positive on). Sampled with `random.Random(seed=17)` for
  reproducibility.

The 0.92 F1 target from `skill/entity-resolver/SKILL.md` is met with margin
(0.963).

### What the 7 missed positives look like

The remaining recall gap is mostly pairs where one name was completely
renamed with no shared text — "Darrowever LLP" / "Saxon, Gilmore & Carraway,
P.A." being the most extreme. These cases require an external alias table
to link; fuzzy resolution alone can't recover them. The script's `confidence`
score (0.0–1.0) flags fuzzy clusters so downstream skills can require
`confidence >= 0.95` if subsidiary precision matters.

## Downstream effect on scan

The `scan` skill's `cov_profiles` CTE was previously grouping by
`(lobbyist_name, registrant_id, registrant_name)`. That meant the same firm
under two name spellings produced two rows for the same person, inflating
candidate counts (e.g., "Mark Limbaugh" appeared twice — once as
"THE FERGUSON GROUP" and once as "THE FERGUSON GROUP, LLC"). The scan now
groups by `(lobbyist_name, registrant_id)` only, picking
`MAX(registrant_name)` for display. Result: 139 candidates instead of 140
double-counted ones.

A future revision will join `scan` against `entity_map.cluster_id` directly
rather than relying on `registrant_id` collapse — that handles the
cross-chamber and cross-firm cases too. The infrastructure is in place.

## Reproducibility

Idempotent. Running `uv run scripts/02_entity_resolver.py` again drops and
rebuilds the `entity_map` table from scratch using the same deterministic
algorithm. The output table row count and cluster count are byte-identical
across runs on the same DB.
