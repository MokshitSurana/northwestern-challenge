# Senate LDA Schema Reference

Source: Secretary of the Senate LDA API bulk export (JSON).
Coverage: 2022-Q1 2026. Total: 418,170 filings.

---

## Raw JSON structure

Each year file is a JSON array of filing objects:
```
data/senate/{year}/filings/filings_{year}.json
```

Each filing object has this top-level shape:
```json
{
  "filing_uuid": "3f2d5c12-5fc3-4b29-8974-...",
  "filing_type": "Q4",
  "filing_type_display": "Fourth Quarter Report",
  "filing_year": 2025,
  "filing_period_display": "October 1 - December 31, 2025",
  "income": 82730000.00,
  "expenses": null,
  "dt_posted": "2026-01-20",
  "registrant": {
    "id": "400123456",
    "name": "HARBINGER STRATEGIES, LLC",
    "description": "...",
    "country": "USA",
    "state": "DC"
  },
  "client": {
    "id": "500789",
    "name": "ACME CORPORATION",
    "description": "...",
  },
  "lobbying_activities": [...],
  "conviction_disclosure": false,
  "termination_date": null
}
```

### `lobbying_activities[]`

Each activity represents one issue area code:
```json
{
  "general_issue_code": "HCR",
  "general_issue_code_display": "Health Issues",
  "description": "Monitor H.R. 1234; support insulin cap legislation...",
  "lobbyists": [...],
  "government_entities": [...],
  "foreign_entity_issues": "..."
}
```

### ⚠️ `lobbying_activities[].lobbyists[]` — NESTED NAME (see known_quirks.md §1)

```json
{
  "lobbyist": {             ← names are nested INSIDE this key
    "id": "9876",
    "prefix": "",
    "first_name": "JOHN",
    "last_name": "SMITH",
    "suffix": ""
  },
  "covered_position": "Deputy Chief of Staff, Senate Finance Committee",
  "is_new_lobbyist": false
}
```

### `lobbying_activities[].government_entities[]`

```json
[
  "SENATE",
  "HOUSE OF REPRESENTATIVES",
  "Health & Human Services, Dept of (HHS)",
  "Food & Drug Administration (FDA)"
]
```

These strings are the canonical entity names. They map to `senate_gov_entities.entity_name`.

---

## DuckDB tables

### `senate_filings`

| Column | Type | Description |
|--------|------|-------------|
| filing_uuid | VARCHAR | Primary key — stable UUID from Senate API |
| filing_type | VARCHAR | "Q1", "Q2", "Q3", "Q4", "MYR", "RA", "RR" |
| filing_type_display | VARCHAR | Human-readable type |
| filing_year | BIGINT | Calendar year |
| filing_period | VARCHAR | Same as filing_type |
| filing_period_display | VARCHAR | "First Quarter Report" etc. |
| income | DOUBLE | Reported income (dollars), often null |
| expenses | DOUBLE | Reported expenses (dollars), often null |
| dt_posted | VARCHAR | Date posted (string, not parsed) |
| registrant_id | VARCHAR | Stable registrant ID across filings |
| registrant_name | VARCHAR | Firm name (NOT normalized — see entity-resolver skill) |
| registrant_description | VARCHAR | Firm description |
| registrant_country | VARCHAR | Country code |
| registrant_state | VARCHAR | State code |
| client_id | VARCHAR | Stable client ID |
| client_name | VARCHAR | Client name |
| source_path | VARCHAR | Absolute path to source JSON file |

### `senate_activities`

One row per (filing, issue-code) pair.

| Column | Type | Description |
|--------|------|-------------|
| filing_uuid | VARCHAR | FK → senate_filings |
| activity_idx | BIGINT | Position within filing (0-based) |
| general_issue_code | VARCHAR | 2-3 letter ALI code ("HCR", "DEF", etc.) |
| description | VARCHAR | Free-text description of lobbying activity |
| source_path | VARCHAR | Source file |

### `senate_lobbyists`

One row per (filing, activity, lobbyist). Deduplication needed — see known_quirks.md §6.

| Column | Type | Description |
|--------|------|-------------|
| filing_uuid | VARCHAR | FK → senate_filings |
| activity_idx | BIGINT | FK → senate_activities |
| lobbyist_name | VARCHAR | "FIRST LAST" (uppercased by LDA) |
| covered_position | VARCHAR | Free-text prior government role description |
| is_new | BOOLEAN | Whether this is a new lobbyist on this filing |
| source_path | VARCHAR | Source file |

### `senate_gov_entities`

One row per (filing, activity, entity). Use `DISTINCT filing_uuid` to avoid double-counting.

| Column | Type | Description |
|--------|------|-------------|
| filing_uuid | VARCHAR | FK → senate_filings |
| activity_idx | BIGINT | FK → senate_activities |
| entity_name | VARCHAR | Canonical agency/body name (see entity list below) |
| source_path | VARCHAR | Source file |

### `senate_contributions`

Semiannual contribution reports (PACS, bundling).

| Column | Type | Description |
|--------|------|-------------|
| filing_uuid | VARCHAR | FK → senate_filings |
| amount | DOUBLE | Contribution amount |
| payee | VARCHAR | Name of contribution payee |
| ... | | Additional fields |

---

## Common `entity_name` values (top 30 by frequency)

```
HOUSE OF REPRESENTATIVES          687,164
SENATE                            679,438
White House Office                 43,057
Health & Human Services, Dept of (HHS)  35,108
Commerce, Dept of (DOC)            30,715
Agriculture, Dept of (USDA)        30,478
Energy, Dept of                    28,271
Treasury, Dept of                  28,110
Transportation, Dept of (DOT)      28,070
Defense, Dept of (DOD)             26,054
Environmental Protection Agency (EPA)  25,335
Executive Office of the President (EOP)  23,941
Centers For Medicare and Medicaid Services (CMS)  22,537
State, Dept of (DOS)               18,101
Interior, Dept of (DOI)            16,474
U.S. Trade Representative (USTR)   15,519
Homeland Security, Dept of (DHS)   14,286
Office of Management & Budget (OMB)  14,044
Labor, Dept of (DOL)               12,820
Food & Drug Administration (FDA)    9,324
Justice, Dept of (DOJ)              6,956
Federal Aviation Administration (FAA)  6,333
Federal Communications Commission (FCC)  5,577
Securities & Exchange Commission (SEC)  4,802
Federal Trade Commission (FTC)      4,557
Natl Aeronautics & Space Administration (NASA)  2,605
```

---

## Convenience views

### `revolving_door`
Senate lobbyists with non-empty `covered_position`, joined to their filing context.
Use for revolving-door analysis without writing the join manually.

### `senate_spend_by_issue`
Aggregate disclosed income by ALI issue code per quarter.
Use for "what issues had the most lobbying spend in Q3 2025?" type queries.
