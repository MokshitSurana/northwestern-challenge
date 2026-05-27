-- example_query.sql
-- Demonstration queries for the investigation.duckdb analytical store.
-- Run in any DuckDB client or via: uv run python -c "import duckdb; ..."

-- ── 1. Row counts — verify your build ─────────────────────────────────────────
SELECT 'press_releases'    AS tbl, COUNT(*) AS rows FROM press_releases
UNION ALL
SELECT 'senate_filings',          COUNT(*) FROM senate_filings
UNION ALL
SELECT 'senate_activities',       COUNT(*) FROM senate_activities
UNION ALL
SELECT 'senate_lobbyists',        COUNT(*) FROM senate_lobbyists
UNION ALL
SELECT 'senate_gov_entities',     COUNT(*) FROM senate_gov_entities
UNION ALL
SELECT 'house_filings',           COUNT(*) FROM house_filings
UNION ALL
SELECT 'house_activities',        COUNT(*) FROM house_activities
UNION ALL
SELECT 'house_lobbyists',         COUNT(*) FROM house_lobbyists;

-- ── 2. Top 10 lobbying firms by Senate-disclosed income (2025) ─────────────────
SELECT
    registrant_name,
    ROUND(SUM(income) / 1e6, 2)  AS income_M,
    COUNT(*)                     AS filings,
    COUNT(DISTINCT client_name)  AS clients
FROM senate_filings
WHERE filing_year = 2025
  AND income IS NOT NULL
GROUP BY registrant_name
ORDER BY income_M DESC
LIMIT 10;

-- ── 3. Top NASA-targeting lobbyists (Senate, 2024-2026) ───────────────────────
SELECT
    sl.lobbyist_name,
    sf.registrant_name,
    COUNT(DISTINCT sf.filing_uuid)  AS nasa_filings
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
LIMIT 20;

-- ── 4. The Artemis Group — full filing count ───────────────────────────────────
SELECT
    sf.client_name,
    sf.filing_year,
    sf.filing_period,
    sf.income,
    sf.filing_uuid
FROM senate_filings sf
WHERE sf.registrant_name ILIKE '%artemis group%'
ORDER BY sf.filing_year, sf.filing_period, sf.client_name;

-- ── 5. Revolving door — lobbyists with prior agency senior roles ───────────────
SELECT
    sl.lobbyist_name,
    sl.covered_position,
    sf.registrant_name,
    COUNT(DISTINCT sf.filing_uuid) AS filings,
    ROUND(SUM(sf.income) / 1e6, 2) AS income_M
FROM senate_lobbyists sl
JOIN senate_filings sf USING (filing_uuid)
WHERE sl.covered_position ILIKE '%Administrator%'
   OR sl.covered_position ILIKE '%Secretary%'
   OR sl.covered_position ILIKE '%Commissioner%'
   OR sl.covered_position ILIKE '%Director%'
GROUP BY sl.lobbyist_name, sl.covered_position, sf.registrant_name
ORDER BY filings DESC
LIMIT 30;

-- ── 6. Press releases mentioning NASA by quarter ───────────────────────────────
SELECT
    filing_quarter,
    COUNT(*) AS press_count
FROM press_releases
WHERE text ILIKE '%NASA%'
   OR text ILIKE '%Artemis%'
   OR text ILIKE '%lunar%'
GROUP BY filing_quarter
ORDER BY filing_quarter;

-- ── 7. Senate spend by issue code per year ────────────────────────────────────
SELECT * FROM senate_spend_by_issue
ORDER BY filing_year DESC, total_income_M DESC
LIMIT 50;
