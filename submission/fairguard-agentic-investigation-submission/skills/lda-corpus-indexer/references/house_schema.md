# House LDA Schema Reference

Source: House Clerk bulk XML export.
Coverage: 2022-Q1 2026. Total: 409,640 XML files (one per filing).

---

## Raw XML structure

Each file is one filing. Files are grouped by quarter directory:
```
data/house/
  2022_1stQuarter_XML/
    301234567.xml
    301234568.xml
    ...
  2022_2ndQuarter_XML/
  ...
  2026_1stQuarter_XML/
  2026_Registrations_XML/
```

### Two document types

**LOBBYINGDISCLOSURE1** — registrations (initial filings)
**LOBBYINGDISCLOSURE2** — quarterly reports (ongoing filings)

Both share the same top-level element and most fields.

### Top-level structure

```xml
<LOBBYINGDISCLOSURE2
    ID="301647981"
    SenateID="401108974-61848"
    reportYear="2024"
    reportType="Q4"
    NoLobbyingIssues="N"
    organizationName="THE ARTEMIS GROUP, LLC"
    clientName="Agile Space Industries"
    clientState=""
    clientCountry="USA"
    effectiveDate="2024-10-01"
    terminationDate=""
    income="60000"
    expenses="">
  <alis>
    <ali_info>...</ali_info>  <!-- modern schema (post-~2024) -->
    <ali_Code>SCI</ali_Code>  <!-- legacy schema (pre-2024), flat -->
  </alis>
</LOBBYINGDISCLOSURE2>
```

### ALI blocks — TWO schemas (see known_quirks.md §3)

**Modern schema** (post-~2024 filings, nested):
```xml
<alis>
  <ali_info>
    <issueAreaCode>SCI</issueAreaCode>
    <description>Support commercial space legislation...</description>
    <lobbyists>
      <lobbyist>
        <lobbyistFirstName>JIM</lobbyistFirstName>
        <lobbyistLastName>BRIDENSTINE</lobbyistLastName>
        <lobbyistSuffix></lobbyistSuffix>
        <officialPosition>Member, United States House of Representatives; Administrator, NASA</officialPosition>
        <inactive>N</inactive>
      </lobbyist>
    </lobbyists>
    <govEntities>
      <govEntity>
        <govEntityName>SENATE</govEntityName>
        <govEntityID>...</govEntityID>
      </govEntity>
    </govEntities>
  </ali_info>
</alis>
```

**Legacy schema** (pre-2024, flat):
```xml
<alis>
  <ali_Code>SCI</ali_Code>
  <Lobbyist name="JIM BRIDENSTINE" covered="..." />
</alis>
```

⚠️ **Critical:** Parse modern first, fall back to legacy. Mixing them breaks
one era or the other.

---

## DuckDB tables

### `house_filings`

| Column | Type | Description |
|--------|------|-------------|
| house_id | VARCHAR | Numeric ID from filename (e.g., "301647981") |
| senate_id | VARCHAR | `{registrant_id}-{engagement_id}` — NOT the Senate filing_uuid |
| org_name | VARCHAR | Registrant/firm name (organizationName attribute) |
| client_name | VARCHAR | Client name |
| filing_year | BIGINT | Report year |
| filing_period | VARCHAR | "Q1", "Q2", "Q3", "Q4", "Registrations" |
| income | DOUBLE | Reported income (dollars) |
| expenses | DOUBLE | Reported expenses (dollars) |
| source_path | VARCHAR | Absolute path to source XML file |

**Key gotcha:** `senate_id` uses format `{registrant_id}-{engagement_id}`.
To match against Senate data, join on `SPLIT_PART(senate_id, '-', 1) = registrant_id`.
See `references/joins.md` for cross-chamber join patterns.

### `house_activities`

One row per activity block within a filing.

| Column | Type | Description |
|--------|------|-------------|
| house_id | VARCHAR | FK → house_filings |
| activity_idx | BIGINT | Position within filing (0-based) |
| ali_code | VARCHAR | Issue area code ("SCI", "DEF", "HCR", etc.) |
| description | VARCHAR | Free-text activity description |
| source_path | VARCHAR | Source file |

### `house_lobbyists`

One row per (filing, activity, lobbyist). Lobbyists are nested inside ALI blocks.

| Column | Type | Description |
|--------|------|-------------|
| house_id | VARCHAR | FK → house_filings |
| activity_idx | BIGINT | FK → house_activities |
| lobbyist_name | VARCHAR | "FIRST LAST" — from `lobbyistFirstName` + `lobbyistLastName` |
| covered_position | VARCHAR | `officialPosition` — prior government role |
| is_new | VARCHAR | "Y"/"N" |
| source_path | VARCHAR | Source file |

⚠️ **Critical:** Names come from `<lobbyistFirstName>` + `<lobbyistLastName>`.
The `<lobbyistName>` element (combined) is a fallback only — it is often empty.
See `known_quirks.md §2`.

---

## ALI issue codes (common)

| Code | Description |
|------|-------------|
| AER | Aerospace |
| AGR | Agriculture |
| BAN | Banking |
| BUD | Budget/Appropriations |
| CAW | Clean Air & Water |
| CHM | Chemicals |
| DEF | Defense |
| EDU | Education |
| ENG | Energy/Nuclear |
| ENV | Environment |
| FIN | Financial Institutions |
| GOV | Government Issues |
| HCR | Health Issues |
| HOU | Housing |
| IMM | Immigration |
| LAW | Law Enforcement & Crime |
| MMM | Medicare & Medicaid |
| NAT | Natural Resources |
| PHA | Pharmacy |
| SCI | Science/Technology |
| TAX | Taxation/Internal Revenue |
| TRD | Trade |
| TRA | Transportation |

Full list: https://lda.senate.gov/alis/

---

## Linking House to Senate

House filings include a `senate_id` field that links to the Senate LDA system,
but the link is at the **registrant-engagement level**, not the filing level.

See `references/joins.md` for the correct join pattern.
