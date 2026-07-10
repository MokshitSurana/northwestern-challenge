---
name: entity-resolver
description: >
  Normalizes and clusters messy organization and person name strings across
  lobbying records so that "MICROSOFT CORP", "Microsoft Corporation", and
  "Microsoft Corp." resolve to a single canonical entity — with original
  strings preserved for audit. Handles FKA/DBA/AKA aliases ("X (FKA Y)"),
  legal-suffix variants (LLC/Inc/Corp), "on behalf of" client wrappers, and
  person-name format variants (Smith, John ↔ John A. Smith). Outputs an
  entity_map table in investigation.duckdb. Use this skill when joining
  records across years, sources, or chambers.
license: MIT
metadata:
  version: "1.0.0"
  author: FairGuard (Mokshit Surana, Archit Rathod)
  tools: [bash, python, file-read, file-write]
  requires_python: ">=3.11"
  depends_on: [lda-corpus-indexer]
---

# entity-resolver

## What this skill does

Resolves messy organization and person name strings to canonical clusters
with provenance. Writes a single `entity_map` table back into
`output/investigation.duckdb` so every downstream skill (`scan`, future
say-vs-pay, etc.) can join through the canonical cluster_id rather than
matching strings directly.

**Why it matters for journalism.** Every government dataset has this problem.
The LDA corpus alone treats "THE FERGUSON GROUP", "THE FERGUSON GROUP, LLC",
and "Ferguson Group LLC" as three distinct entities — joins across them all
return zero rows. Without resolution, every cross-record query is silently
under-counting.

## Inputs

| Column | Source |
|---|---|
| `registrant_name`, `client_name` | `senate_filings`, `house_filings` |
| `org_name`                       | `house_filings` |
| `lobbyist_name`                  | `senate_lobbyists`, `house_lobbyists` |

The skill pulls all DISTINCT strings from those columns (~110K total in the
2022-Q1 2026 corpus).

## Outputs

A new table `entity_map` in `output/investigation.duckdb`:

| Column | Type | Description |
|---|---|---|
| `raw_name`       | VARCHAR | Original string as it appears in source records |
| `entity_type`    | VARCHAR | `organization` or `person` |
| `canonical_name` | VARCHAR | Most-frequent raw spelling within the cluster |
| `cluster_id`     | VARCHAR | Stable hash; shared by all variants of one entity |
| `confidence`     | DOUBLE  | 0.0–1.0 (1.0 = exact-or-normalized match) |
| `match_method`   | VARCHAR | `exact`, `normalized_exact`, `fuzzy_high`, `fuzzy_low`, `singleton` |
| `n_variants`     | INTEGER | Number of distinct raw spellings in the cluster |

Two indexes are built automatically: `idx_entity_raw(raw_name)` and
`idx_entity_cluster(cluster_id)`.

## Invocation

```bash
# Default: orgs + people, threshold 92 (org), 95 (person)
uv run skills/entity-resolver/scripts/02_entity_resolver.py

# Faster runs for iteration
uv run skills/entity-resolver/scripts/02_entity_resolver.py --orgs-only
uv run skills/entity-resolver/scripts/02_entity_resolver.py --people-only
uv run skills/entity-resolver/scripts/02_entity_resolver.py --limit 5000 --dry-run    # quick smoke test

# Tune fuzzy thresholds
uv run skills/entity-resolver/scripts/02_entity_resolver.py --threshold 90              # looser org
uv run skills/entity-resolver/scripts/02_entity_resolver.py --person-threshold 97       # stricter person
```

## Algorithm

### Organizations

1. **Alias extraction (recursive).** For each raw name, extract every form
   it implies. "X (FKA Y)" → `[X, Y]`. "X F/K/A Y D/B/A Z" → `[X, Y, Z]`.
   "X on behalf of Y" → `[X, Y]`. Markers handled: FKA, NKA, FNA, DBA, AKA,
   "formerly", "formerly known as", "formerly reported as", "previously",
   "now known as", "on behalf of", "OBO".
2. **Normalization.** Strip honorifics ("Mr.", "Dr.", …) and the leading
   "The". Lowercase. Normalize `&` to " & " with spaces. Strip legal suffixes
   from the end iteratively (LLC, Inc, Corp, LP, LLP, PLLC, PLC, Ltd, Co,
   GmbH, AG, SA, NV) including dotted and spaced variants (`L.L.C.`, `L L C`).
   Collapse non-alphanumeric to single spaces.
3. **Blocking.** Group by first token of the normalized form. This caps the
   O(n²) fuzzy comparison to within-block only — a single firm's
   variations always share their first token.
4. **Fuzzy match.** Within each block, compare with `rapidfuzz.token_sort_ratio`.
   Default threshold 92. Skip pairs whose lengths differ by > 50% (cheap prune).
5. **Cluster.** Union-find over normalized forms. Aliases extracted from the
   same raw name are unioned immediately.
6. **Canonical pick.** Most frequent raw spelling within each cluster wins
   as `canonical_name`.

### Persons

1. **Parse format.** Detect "Smith, John A." vs "John A. Smith" formats.
   Strip honorifics (Mr./Mrs./Dr./Hon./…) and suffixes (Jr./Sr./II/III/Esq).
2. **Build key.** `(last_name, first_name, middle_initial)`, all lowercased.
3. **Exact-match clustering.** Same `(last, first)` always unions, regardless
   of middle-initial differences ("Smith, John A." = "John Q. Smith" if
   middle initials match too; otherwise the union still happens).
4. **Fuzzy last-name pass.** Within a first-initial group, two distinct last
   names with `rapidfuzz.ratio ≥ 95` AND identical first names get unioned
   ("Smith" / "Smyth" with both "John" → same person). Distinct first names
   under the same last name are never merged.

## Evaluation

The skill is tested against a hand-curated unit set AND an automatically
harvested in-corpus eval set:

- **Positive labels (free).** Pairs of names that share a stable identifier
  (same `registrant_id` with two `registrant_name` spellings, or same
  `(registrant_id, client_id)` with two `client_name` spellings). 97 pairs
  harvested from the 2022-Q1 2026 corpus.
- **Hard negatives.** Pairs of names from disjoint registrant_ids that share
  a first token (high lexical overlap but different entities). 200 pairs.

**Current F1: 0.963** (precision 1.000, recall 0.928) on the auto-harvested
eval set. Target was ≥ 0.92. Tests are in
`tests/test_entity_resolver.py::test_f1_on_db`.

Remaining recall gap is mostly cases where one entity was renamed to a
completely unrelated string with no shared text (e.g., "Darrowever LLP" was
formerly "Saxon, Gilmore & Carraway, P.A."). Those require an external alias
table — out of scope for fuzzy resolution.

## Reproducing the eval

```bash
uv run pytest tests/test_entity_resolver.py -v
uv run pytest tests/test_entity_resolver.py::test_f1_on_db -s
```

## Use from other skills

After `entity_map` is in the DB, downstream queries can join through
`cluster_id` for canonical aggregations:

```sql
-- All filings under "The Ferguson Group" regardless of spelling
SELECT sf.*
FROM senate_filings sf
JOIN entity_map em ON em.raw_name = sf.registrant_name
WHERE em.cluster_id = (
    SELECT cluster_id FROM entity_map
    WHERE canonical_name ILIKE '%Ferguson Group%' LIMIT 1
)
```

## Limitations

- **No external alias source.** Two completely-different name strings sharing
  an id can't be linked without external data.
- **Subsidiaries collapse with parents** when their names overlap heavily
  (e.g., "ACME, INC." and "ACME HEALTH" share first token "ACME" — a deep-rename
  inspection can't distinguish "same firm" from "subsidiary"). Confidence
  scores are exposed so downstream skills can require `confidence >= 0.95`
  if subsidiary precision matters.
- **People share a name.** Two distinct individuals named "John Smith" cluster
  into one. Downstream skills should disambiguate with firm context (e.g.,
  cluster_id × registrant_id) before counting.
- **Senate + House.** The resolver pulls names from both chambers, but
  cluster_ids are entirely based on string similarity — a firm appearing in
  only one chamber under one spelling won't have its other-chamber spelling
  joined unless the strings happen to match.
