# Cross-Dataset Join Reference

How to link Senate LDA ↔ House LDA ↔ congressional press releases.

---

## Senate ↔ House LDA

### The key fact: `senate_id` is NOT `filing_uuid`

House filings have a `senate_id` field. It looks like: `401108974-61848`.
This is NOT the Senate `filing_uuid` (which is a UUID like `3f2d5c12-...`).

`senate_id` format: `{senate_registrant_id}-{engagement_id}`

- `401108974` = Senate registrant ID (stable per firm)
- `61848` = Senate engagement ID (stable per firm-client relationship)

### Correct cross-chamber join patterns

**Find all House filings for an Artemis Group (registrant 401108974) client:**
```sql
SELECT * FROM house_filings
WHERE senate_id LIKE '401108974-%'
ORDER BY filing_year, client_name
```

**Join House filings to Senate filings at the registrant level:**
```sql
SELECT hf.house_id, hf.client_name, sf.filing_uuid, sf.income
FROM house_filings hf
JOIN senate_filings sf
  ON SPLIT_PART(hf.senate_id, '-', 1) = sf.registrant_id
  AND hf.client_name = sf.client_name      -- narrow to same client
  AND hf.filing_year = sf.filing_year
  AND hf.filing_period = sf.filing_period
```

**Count filings per registrant across both chambers:**
```sql
SELECT
    COALESCE(sf.registrant_name, hf.org_name) AS firm,
    COUNT(DISTINCT sf.filing_uuid) AS senate_filings,
    COUNT(DISTINCT hf.house_id)    AS house_filings
FROM senate_filings sf
FULL OUTER JOIN house_filings hf
  ON SPLIT_PART(hf.senate_id, '-', 1) = sf.registrant_id
GROUP BY 1
ORDER BY senate_filings DESC
```

---

## Senate LDA ↔ Press Releases

There is no direct ID link. Join by member identity + time window.

### The mismatch

- Press releases identify members by `bioguide_id` (e.g., "B000574")
- LDA records identify targets by government entity name ("SENATE", "House Science Committee")
- LDA records don't identify individual members

### Practical join patterns

**Find press releases from members on a committee that lobbied a bill:**
```sql
-- Step 1: find press releases mentioning the bill
SELECT bioguide_id, date, title, text
FROM press_releases
WHERE text ILIKE '%NASA Reauthorization%'

-- Step 2: find Senate filings targeting NASA from the same quarter
SELECT registrant_name, client_name, filing_period
FROM senate_filings sf
JOIN senate_gov_entities sge USING (filing_uuid)
WHERE sge.entity_name ILIKE '%Aeronautics%'
  AND sf.filing_year = 2025
```

**"Say-vs-pay" analysis: member rhetoric vs. lobbying spend on same issue:**
```sql
-- Press releases mentioning a topic per member per quarter
WITH press_by_quarter AS (
    SELECT
        bioguide_id,
        CONCAT(YEAR(CAST(date AS DATE)), '-Q', QUARTER(CAST(date AS DATE))) AS quarter,
        COUNT(*) AS press_count
    FROM press_releases
    WHERE text ILIKE '%pharmaceutical%' OR text ILIKE '%drug pricing%'
    GROUP BY 1, 2
),
-- Lobbying spend on health/pharma per quarter
spend_by_quarter AS (
    SELECT
        filing_period AS quarter,
        SUM(income) / 1e6 AS income_m
    FROM senate_filings sf
    JOIN senate_activities sa USING (filing_uuid)
    WHERE sa.general_issue_code IN ('HCR', 'PHA', 'MMM')
    GROUP BY 1
)
SELECT pbq.*, sbq.income_m
FROM press_by_quarter pbq
JOIN spend_by_quarter sbq USING (quarter)
ORDER BY pbq.quarter
```

---

## Within Senate LDA: activity ↔ lobbyist ↔ entity

Activities, lobbyists, and government entities all share `(filing_uuid, activity_idx)`:

```sql
-- All lobbyists who lobbied NASA on a given filing
SELECT DISTINCT sl.lobbyist_name, sl.covered_position
FROM senate_lobbyists sl
JOIN senate_gov_entities sge
  ON sl.filing_uuid = sge.filing_uuid
  AND sl.activity_idx = sge.activity_idx
WHERE sge.entity_name ILIKE '%Aeronautics%'
  AND sl.lobbyist_name IS NOT NULL
```

### Deduplication note

`senate_lobbyists` has one row per (filing, activity, lobbyist). For most
"how many filings" questions, deduplicate on `filing_uuid`:

```sql
-- WRONG: counts activities, not filings
SELECT lobbyist_name, COUNT(*) FROM senate_lobbyists GROUP BY lobbyist_name

-- CORRECT: counts distinct filings
SELECT lobbyist_name, COUNT(DISTINCT filing_uuid) AS n_filings
FROM senate_lobbyists
GROUP BY lobbyist_name
ORDER BY n_filings DESC
```

---

## Common query templates

### Top NASA-targeting lobbyists (Senate, 2024-2026)
```sql
SELECT
    sl.lobbyist_name,
    sf.registrant_name,
    COUNT(DISTINCT sf.filing_uuid) AS nasa_filings
FROM senate_lobbyists sl
JOIN senate_filings sf USING (filing_uuid)
WHERE sf.filing_uuid IN (
    SELECT DISTINCT filing_uuid FROM senate_gov_entities
    WHERE entity_name ILIKE '%Aeronautics%'
)
  AND sf.filing_year >= 2024
  AND sl.lobbyist_name IS NOT NULL
GROUP BY sl.lobbyist_name, sf.registrant_name
ORDER BY nasa_filings DESC
LIMIT 20
```

### Revolving-door candidates (lobbyists with prior agency roles)
```sql
SELECT
    sl.lobbyist_name,
    sl.covered_position,
    sf.registrant_name,
    COUNT(DISTINCT sf.filing_uuid) AS filings
FROM senate_lobbyists sl
JOIN senate_filings sf USING (filing_uuid)
WHERE sl.covered_position IS NOT NULL
  AND LENGTH(sl.covered_position) > 20
  AND sl.lobbyist_name IS NOT NULL
GROUP BY sl.lobbyist_name, sl.covered_position, sf.registrant_name
ORDER BY filings DESC
```

Or use the pre-built view:
```sql
SELECT * FROM revolving_door LIMIT 100
```

### Firm-level income by quarter
```sql
SELECT
    registrant_name,
    filing_year,
    filing_period,
    SUM(income) / 1e6 AS income_m,
    COUNT(*) AS filings
FROM senate_filings
WHERE income IS NOT NULL
GROUP BY registrant_name, filing_year, filing_period
ORDER BY income_m DESC
LIMIT 50
```
