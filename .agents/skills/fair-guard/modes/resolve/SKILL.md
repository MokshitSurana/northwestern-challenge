---
name: resolve
description: >
  Normalizes and clusters messy organization/person name strings across
  lobbying records so "MICROSOFT CORP", "Microsoft Corporation", and
  "Microsoft Corp." resolve to one entity — with originals preserved for
  audit. Handles FKA/DBA/AKA aliases, legal-suffix variants, "on behalf of"
  client wrappers, and person-name format variants. Writes entity_map table
  to investigation.duckdb. F1 = 0.963 on the auto-harvested eval set.
license: MIT
compatibility: Requires Python 3.11+, uv, rapidfuzz. Depends on lda-corpus-indexer output.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  status: shipped
  part-of: fair-guard
  tools: bash, python, file-read, file-write
---

# entity-resolver

## Instructions for the agent

Run the resolver and confirm the resulting `entity_map` table is in the
DuckDB store. The resolver is idempotent — re-running drops and rebuilds the
table.

```bash
uv run scripts/02_entity_resolver.py
```

Expect ~110K raw input rows → ~51K clusters (≈2.15x compression on the
2022-Q1 2026 corpus). The script prints a summary of cluster counts and
match-method breakdowns; surface that to the user.

For faster iteration (subset only):

```bash
uv run scripts/02_entity_resolver.py --orgs-only
uv run scripts/02_entity_resolver.py --people-only
uv run scripts/02_entity_resolver.py --limit 5000 --dry-run
```

To validate the resolver's F1 against the auto-harvested eval set:

```bash
uv run pytest tests/test_entity_resolver.py::test_f1_on_db -s
```

## What this skill does

Resolves organization and person name strings to canonical clusters with
provenance. Writes a single `entity_map` table back into
`output/investigation.duckdb` so downstream skills (`scan`, etc.) can join
through `cluster_id` rather than matching strings directly.

## Outputs

A new table `entity_map` in `output/investigation.duckdb`:

| Column | Type | Description |
|---|---|---|
| `raw_name`       | VARCHAR | Original string |
| `entity_type`    | VARCHAR | `organization` or `person` |
| `canonical_name` | VARCHAR | Most-frequent raw spelling in cluster |
| `cluster_id`     | VARCHAR | Stable hash shared by variants |
| `confidence`     | DOUBLE  | 0.0–1.0 |
| `match_method`   | VARCHAR | `exact` / `normalized_exact` / `fuzzy_high` / `fuzzy_low` / `singleton` |
| `n_variants`     | INTEGER | # of distinct raw spellings in the cluster |

Plus indexes `idx_entity_raw(raw_name)` and `idx_entity_cluster(cluster_id)`.

## Algorithm summary

**Organizations:** recursive alias extraction (FKA/DBA/AKA/"on behalf of") →
normalization (strip honorifics, legal suffixes, "the", normalize "&") →
first-token blocking → fuzzy match at threshold 92 → union-find clustering.

**Persons:** parse "Last, First" vs "First Last" → strip honorifics + suffixes
→ exact match on (last, first) → fuzzy last-name pass within first-initial
group at threshold 95.

Full details in `skill/entity-resolver/SKILL.md` (this skill's submission
artifact) and in the source: `scripts/02_entity_resolver.py`.

## Evaluation

F1 = 0.963 (precision 1.000, recall 0.928) on auto-harvested positives
(name pairs sharing a stable id like registrant_id or (registrant_id,
client_id)) and hard negatives (disjoint ids sharing a first token).

Target was ≥ 0.92. Reproduce with `uv run pytest tests/test_entity_resolver.py`.
