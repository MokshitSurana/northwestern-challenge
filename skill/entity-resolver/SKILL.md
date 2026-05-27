---
name: entity-resolver
description: >
  Normalizes and clusters messy organization/person name strings across datasets
  so that "MICROSOFT CORP", "Microsoft Corporation", and "Microsoft Corp." resolve
  to a single canonical entity — with original strings preserved for audit.
  Use this skill when you have a corpus with inconsistent name spellings across
  records, years, or data sources and need to join or count across them reliably.
version: 0.1.0-placeholder
author: FairGuard (Mokshit Surana, Archit Rathod)
license: MIT
status: planned
tools: [bash, python, file-read, file-write]
requires_python: ">=3.11"
---

# entity-resolver

> **Status: Planned.** This skill is designed but not yet implemented.
> Implementation target: July 2026. See design notes below.

## What this skill will do

Resolve messy organization and person name strings to canonical forms,
outputting a mapping table with confidence scores and match methods.

**Why it matters:** Every government dataset has this problem. FARA filings,
FEC donor lists, state contractor records, hospital ownership filings — all
have name variants that prevent clean joining. The LDA corpus alone has
"MICROSOFT CORP", "Microsoft Corporation", "Microsoft Corp." as three
distinct strings that should be one entity. Without resolution, any
cross-record or cross-year join is noisy.

**Why it's a prerequisite for Skill 3:** The revolving-door-detector needs
to match `covered_position` agency names (free text) against `senate_gov_entities`
entity names (controlled vocabulary). Exact string matching fails; entity
resolution is required.

## Planned inputs

- A DuckDB/Parquet table with a `raw_name` column and an `entity_type`
  column ("organization" or "person")
- Optionally: a known-positives seed file for threshold tuning

## Planned outputs

An `entity_map` table:

| Column | Type | Description |
|--------|------|-------------|
| raw_name | VARCHAR | Original string as it appears in the data |
| canonical_name | VARCHAR | Resolved canonical form |
| cluster_id | VARCHAR | ID shared by all variants of the same entity |
| confidence | FLOAT | 0.0–1.0 match confidence |
| match_method | VARCHAR | "exact", "normalized_exact", "fuzzy_high", "fuzzy_low", "manual" |

## Planned algorithm

### Organization names

1. Lowercase, replace `&` → "and", strip punctuation
2. Remove legal suffixes from end: LLC, Inc, Corp, Corporation, LP, LLP,
   Ltd, Limited, PLC, PLLC, PC, Co, Company. Also strip leading "The"/"the".
3. Collapse whitespace
4. Block by first token (avoids O(n²) comparisons across 50K names)
5. Within each block: `rapidfuzz.token_sort_ratio`, threshold ~92
6. Cluster with union-find; pick most frequent variant as canonical
7. Output `match_method`: exact → normalized_exact → fuzzy_high → fuzzy_low

### Person names

1. Detect format: "Smith, John" vs "John Smith"
2. Normalize to (last, first, middle_initial) tuple
3. Exact match on (last, first) after lowercase
4. Fuzzy on last name only (threshold 95+) with exact first initial match
5. Output the same match_method field for human review

## Evaluation target

Build an eval set first:
- Positive pairs: any `registrant_id` with 2+ distinct `registrant_name`
  spellings in senate_filings (free labeled positives from the data itself)
- Sample 500 positive + 500 random negative pairs
- Target F1 ≥ 0.92 on held-out eval set before any production use

**Time-box to 2-3 days.** Resolvers are a black hole. Stop at F1 = 0.92.

## Dependencies

- `rapidfuzz >= 3.0` (already in pyproject.toml)
- `output/investigation.duckdb` (built by lda-corpus-indexer skill)

## Implementation notes

The current `scripts/02_revolving_door_scan.py` handles the entity-resolution
problem crudely (ILIKE substring matches). This skill will replace those
heuristics with a principled, auditable resolution pipeline.
