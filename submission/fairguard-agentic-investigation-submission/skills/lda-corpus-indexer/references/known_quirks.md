# Known Parser Quirks — LDA Corpus Indexer

These are bugs discovered the hard way during development of the ETL pipeline.
Each one causes silent data loss — the parser runs without error, but produces
wrong results. Read this before modifying any parsing code.

---

## 1. Senate JSON: lobbyist names are nested two levels deep

**Bug:** The Senate JSON schema nests lobbyist names under
`lobbying_activities[].lobbyists[].lobbyist.first_name` and `.last_name`,
NOT at `lobbying_activities[].lobbyists[].first_name`.

**Symptom:** `lobbyist_name = None` for the entire Senate corpus (2.1M rows).
The parser runs without error, the table looks complete, but every name is null.

**Fix:**
```python
# WRONG — produces None for every row
name = f"{lob.get('first_name', '')} {lob.get('last_name', '')}".strip()

# CORRECT
inner = lob.get("lobbyist", {})
name  = f"{inner.get('first_name', '')} {inner.get('last_name', '')}".strip()
```

**Where:** `scripts/01_build_index.py` → `parse_senate_file()` → lobbyist loop.

---

## 2. House XML: lobbyist names use `<lobbyistFirstName>` + `<lobbyistLastName>`

**Bug:** House XML uses separate first/last name elements, NOT a single
`<lobbyistName>` element (which exists but may be empty or missing).

**Symptom:** All House lobbyist names are None or empty strings.
The Bridenstine revolving-door analysis produces zero results.

**Fix:**
```python
# WRONG — often empty
name = el.findtext("lobbyistName", "").strip()

# CORRECT — prefer split fields, fall back to combined
first = el.findtext("lobbyistFirstName", "").strip()
last  = el.findtext("lobbyistLastName",  "").strip()
name  = f"{first} {last}".strip() or el.findtext("lobbyistName", "").strip()
```

**Where:** `scripts/01_build_index.py` → `parse_house_xml()` → lobbyist loop.

---

## 3. House XML has TWO ALI code schemas (modern vs. legacy)

**Bug:** Post-~2024 House XML uses a nested modern schema for ALI codes;
pre-2024 uses a flat legacy schema. Using only one breaks the other.

**Modern schema** (post-2024):
```xml
<alis>
  <ali_info>
    <issueAreaCode>SCI</issueAreaCode>
    <description>...</description>
    <lobbyists>
      <lobbyist>...</lobbyist>
    </lobbyists>
  </ali_info>
</alis>
```

**Legacy schema** (pre-2024):
```xml
<alis>
  <ali_Code>SCI</ali_Code>
</alis>
```

**Symptom:** Using only the modern schema misses 94% of ALI codes from
2022-2023 filings. The `house_activities` table looks populated but
`ali_code` is null for the majority of rows.

**Fix:** Parse modern schema first, fall back to legacy:
```python
ali_code = None
for ali_info in alis.findall("ali_info"):
    ali_code = ali_info.findtext("issueAreaCode")
    # ... parse lobbyists from ali_info
if ali_code is None:
    ali_code = alis.findtext("ali_Code")
```

**Where:** `scripts/01_build_index.py` → `parse_house_xml()` → ALI loop.

---

## 4. Polars schema inference breaks on all-null columns

**Bug:** If a particular Parquet chunk (e.g., one quarter of House filings)
has all-null values in a column, Polars infers a numeric type (Int32 or
Float64) instead of Utf8. When DuckDB union-reads multiple Parquet files
with `union_by_name=True`, it sees a type mismatch and raises an error —
or silently coerces values incorrectly.

**Symptom:** DuckDB `union_by_name` error on House tables, or numeric values
appearing where string values are expected.

**Fix:** Always pass explicit `schema_overrides` on House Parquet writes:
```python
schema_overrides = {
    "house_id":     pl.Utf8,
    "senate_id":    pl.Utf8,
    "org_name":     pl.Utf8,
    "client_name":  pl.Utf8,
    "lobbyist_name":pl.Utf8,
    "covered_position": pl.Utf8,
    "ali_code":     pl.Utf8,
    "description":  pl.Utf8,
    # ... all string columns
}
df = pl.DataFrame(records, schema_overrides=schema_overrides)
```

**Where:** All `write_parquet()` calls for House tables in `01_build_index.py`.

---

## 5. House `senate_id` is engagement-level, not filing-level

**Bug:** The `senate_id` field in House filings does NOT match the Senate
`filing_uuid`. It matches the Senate `{registrant_id}-{engagement_id}` pair.

**Symptom:** Cross-chamber joins on `senate_id = filing_uuid` return zero rows
or wrong results.

**Correct join pattern:**
```sql
-- WRONG
SELECT * FROM house_filings hf
JOIN senate_filings sf ON hf.senate_id = sf.filing_uuid

-- CORRECT: senate_id is registrant-engagement level
-- Match on registrant_id prefix
SELECT *
FROM house_filings hf
JOIN senate_filings sf
  ON sf.registrant_id = SPLIT_PART(hf.senate_id, '-', 1)
```

Or, for the Artemis Group specifically:
```sql
SELECT * FROM house_filings
WHERE senate_id LIKE '401108974-%'  -- matches all Artemis Group engagements
```

**Where:** Any cross-chamber join in analysis scripts.

---

## 6. Senate `senate_lobbyists` has 2.1M rows — deduplicate for counts

**Bug (conceptual):** Each lobbyist appears once per *activity* in a filing,
not once per filing. A filing with 5 activities and 3 lobbyists = 15 rows.

**Symptom:** `SELECT COUNT(*) FROM senate_lobbyists WHERE lobbyist_name = 'X'`
overcounts by the average number of activities per filing (~5×).

**Fix:** Always deduplicate on `(filing_uuid, lobbyist_name)` for counting:
```sql
-- WRONG: overcounts 5x
SELECT lobbyist_name, COUNT(*) FROM senate_lobbyists GROUP BY lobbyist_name

-- CORRECT
SELECT lobbyist_name, COUNT(DISTINCT filing_uuid) AS filings
FROM senate_lobbyists
GROUP BY lobbyist_name
```

**Where:** Any aggregate query on `senate_lobbyists`.

---

## 7. `data/data/` double-nesting from zip extraction

**Symptom:** `data/senate/...` paths not found. Parser reports `[miss]` for
all Senate files.

**Fix:** Set the env var before running:
```bash
DATA_ROOT=data/data uv run scripts/01_build_index.py
```

Or, the current default in `01_build_index.py` is `DATA_ROOT=data` — the
actual root needs to point to the directory containing `senate/`, `house/`,
and `congress_press/`.
