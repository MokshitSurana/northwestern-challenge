# Finding 02 (Structural Pattern): Former Agency Heads Lobbying Their Former Agency

**Status:** Draft. All quantitative claims sourced to `output/investigation.duckdb`.
Biographical claims require independent verification before any publication.
This finding extends the Artemis Group / Bridenstine case study (Finding 01)
to the full corpus.

---

## Executive Summary

A systematic scan of the 2022-2026 Senate LDA corpus identifies former senior
government officials who now lobby the exact federal agency they previously led,
measuring the share of their firm's filings that target their former agency
(the 'agency concentration ratio').

The scan identified **139 candidates** across 22 agencies
who hold a former senior role at a named agency and whose firm has ≥10 filings
targeting that agency at ≥20% concentration.

The top cases, ranked by Bridenstine-style interestingness score
(concentration × log(filings) × seniority), are:

1. **BENJAMIN STEINBERG** (ENERGY) — 90.2% concentration, 213/236 filings, firm: VENN STRATEGIES
2. **MARK LIMBAUGH** (INTERIOR) — 72.6% concentration, 527/726 filings, firm: THE FERGUSON GROUP, LLC
3. **ASHLEE JOHNSON** (USDA) — 82.7% concentration, 230/278 filings, firm: THE RUSSELL GROUP, INC.
4. **SCOTT PARSONS** (CFTC) — 89.8% concentration, 149/166 filings, firm: DELTA STRATEGY GROUP
5. **KEVIN BAILEY** (USDA) — 87.3% concentration, 144/165 filings, firm: FGS GLOBAL (US) LLC (FKA FGH HOLDINGS LLC)
6. **JIM NEWSOME** (CFTC) — 96.0% concentration, 95/99 filings, firm: DELTA STRATEGY GROUP
7. **MICHAEL TORREY** (USDA) — 79.0% concentration, 180/228 filings, firm: TORREY ADVISORY GROUP (FORMERLY MICHAEL TORREY ASSOCIATES, LLC)
8. **KENNETH BARBIC** (USDA) — 78.8% concentration, 108/137 filings, firm: INVARIANT LLC
9. **ROGER SHERMAN** (FCC) — 100.0% concentration, 45/45 filings, firm: WANETA STRATEGIES, LLC
10. **AURENE MARTIN** (INTERIOR) — 68.2% concentration, 180/264 filings, firm: SPIRIT ROCK CONSULTING

---

## Methodology

1. **Agency detection in covered_position.** For each of 23 named federal agencies,
   regex patterns match senior-role indicators (Administrator, Commissioner, Secretary,
   Deputy Secretary, Chairman, Director, Chief of Staff) combined with the agency name.
   Patterns are documented in `scripts/03_agency_concentration.py` → `AGENCY_REGISTRY`.

2. **Concentration ratio.** For each matched (lobbyist, firm, agency) triple:
   `concentration = agency_filings / total_filings` where agency_filings counts
   filings at that firm where `senate_gov_entities.entity_name` matches the agency.

3. **Score.** `score = concentration × log(total_filings + 1) × seniority_score`
   This rewards high concentration at high volume, penalizes one-filing flukes.

4. **Thresholds.** Default: concentration ≥ 20%, total filings ≥ 10.
   Adjustable via `--min-conc` and `--min-filings` flags.

5. **Senate LDA only.** The concentration is computed on Senate-side records only.
   A combined Senate+House ranking would shift the ordering.

---

## Individual Cases (Top 10)

### 1. BENJAMIN STEINBERG → ENERGY

**Score:** 24.676  |  **Concentration:** 90.2%

**Prior role (per LDA disclosure):** Senior Advisor - Department of Energy (DOE); Office Director - (DOE), Chief of Staff - (DOE), Deputy Chief of Staff - (DOE), Senior Program Manager, Office of the Fed Environmental Exec - Executive office of the President

**Firm:** VENN STRATEGIES
**Filings targeting former agency:** 213 of 236 total (90.2%)
**Clients (agency-targeting):** BURNS & MCDONNELL ENGINEERING COMPANY INC | WABTEC CORPORATION | BATTERY MATERIALS AND TECHNOLOGY COALITION | TALON NICKEL (USA) LLC | AMSTED INDUSTRIES
**Disclosed firm income:** $44.77M across 26 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at ENERGY via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 2. MARK LIMBAUGH → INTERIOR

**Score:** 23.914  |  **Concentration:** 72.6%

**Prior role (per LDA disclosure):** Deputy Commissioner for Bureau of Reclamation, DOI 2002 - 2005; Assistant Secretary - Water and Science, Department of the Interior 2005-2007

**Firm:** THE FERGUSON GROUP, LLC
**Filings targeting former agency:** 527 of 726 total (72.6%)
**Clients (agency-targeting):** SUTTER MUTUAL WATER COMPANY AND RECLAMATION DISTRICT 1500 | GLENN-COLUSA IRRIGATION DISTRICT-CA | TURLOCK IRRIGATION DISTRICT | IDAHO WATER RESOURCE BOARD | MARICOPA STANFIELD IRRIGATION & DRAINAGE DISTRICT
**Disclosed firm income:** $30.21M across 50 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at INTERIOR via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 3. ASHLEE JOHNSON → USDA

**Score:** 23.295  |  **Concentration:** 82.7%

**Prior role (per LDA disclosure):** Staff Assistant, Rep. Mike Ross; Executive assistant, Senate Committee on Agriculture, Nutrition, and Forestry; Legislative Analyst, White House Liaison, Chief of Staff to Deputy Secretary, USDA; Policy Assistant, Domestic Policy Council

**Firm:** THE RUSSELL GROUP, INC.
**Filings targeting former agency:** 230 of 278 total (82.7%)
**Clients (agency-targeting):** CARGILL INC | GROWTH ENERGY | WHOLESTONE PRESTAGE LLC (FORMERLY KNOW AS WHOLESTONE FARMS) | MUSKET CORPORATION | BAYER CORPORATION
**Disclosed firm income:** $17.37M across 33 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at USDA via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 4. SCOTT PARSONS → CFTC

**Score:** 22.969  |  **Concentration:** 89.8%

**Prior role (per LDA disclosure):** Chief of staff CFTC; LA Rep Pickering

**Firm:** DELTA STRATEGY GROUP
**Filings targeting former agency:** 149 of 166 total (89.8%)
**Clients (agency-targeting):** CITADEL INVESTMENT GROUP | DIGITAL CHAMBER OF COMMERCE | FIA / PTG | AMERICAN COTTON SHIPPERS ASSOCIATION | COMMODITY MARKETS COUNCIL
**Disclosed firm income:** $4.75M across 13 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at CFTC via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 5. KEVIN BAILEY → USDA

**Score:** 22.307  |  **Concentration:** 87.3%

**Prior role (per LDA disclosure):** Policy Assistant to the Secretary, USDA; Staff Assistant, USDA; Intern, Sen. Tom Harkin.

**Firm:** FGS GLOBAL (US) LLC (FKA FGH HOLDINGS LLC)
**Filings targeting former agency:** 144 of 165 total (87.3%)
**Clients (agency-targeting):** SUSTAINABLE FOOD POLICY ALLIANCE | MICHIGAN SUGAR COMPANY | TRI-STATE GENERATION AND TRANSMISSION ASSOCIATION, INC. | S2G VENTURES, LLC | UPSIDE FOODS (FKA MEMPHIS MEATS, INC.)
**Disclosed firm income:** $15.59M across 18 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at USDA via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 6. JIM NEWSOME → CFTC

**Score:** 22.096  |  **Concentration:** 96.0%

**Prior role (per LDA disclosure):** Chairman, CFTC

**Firm:** DELTA STRATEGY GROUP
**Filings targeting former agency:** 95 of 99 total (96.0%)
**Clients (agency-targeting):** DIGITAL CHAMBER OF COMMERCE | CITADEL INVESTMENT GROUP | AMERICAN COTTON SHIPPERS ASSOCIATION | FIA / PTG | COMMODITY MARKETS COUNCIL
**Disclosed firm income:** $0.94M across 10 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at CFTC via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 7. MICHAEL TORREY → USDA

**Score:** 21.449  |  **Concentration:** 79.0%

**Prior role (per LDA disclosure):** LA for Senators Kassebaum, Dole and Frahm, Asst to CFTC Commissioner David Spears, USDA Dpty. Asst Secretary Congressional Affairs, USDA Dpty. Chief of Staff for Secs. Veneman and Johanns

**Firm:** TORREY ADVISORY GROUP (FORMERLY MICHAEL TORREY ASSOCIATES, LLC)
**Filings targeting former agency:** 180 of 228 total (79.0%)
**Clients (agency-targeting):** CROP INSURANCE AND REINSURANCE BUREAU | EDGE DAIRY FARMER COOPERATIVE (FORMERLY EDGE) | ANIMAL HEALTH INSTITUTE | AMERICAN BEVERAGE ASSOCIATION | AMERICAN SOC. OF AGRONOMY, CROP SCI. SOC. OF AMERICA & SOIL SCI. SOC. OF AMERICA
**Disclosed firm income:** $30.43M across 16 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at USDA via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 8. KENNETH BARBIC → USDA

**Score:** 19.421  |  **Concentration:** 78.8%

**Prior role (per LDA disclosure):** Asst Secretary for Congressional Relations, USDA (18-21); Dep Asst U.S.Trade Representative for Congressional Affairs, USTR (07-09); HouseWays and Means Comm., Subcommittee on Trade: Leg. Asst (06-07); SrStaff Asst (05-06); Staff Asst (05-06)

**Firm:** INVARIANT LLC
**Filings targeting former agency:** 108 of 137 total (78.8%)
**Clients (agency-targeting):** COALITION FOR CLIMATE SMART AGRICULTURE FKA SUSTAINABLE SUPPLY CHAIN COALITION | INTERNATIONAL FRESH PRODUCE ASSOCIATION | PEPSICO, INC. | MCCAIN FOODS USA, INC. | CALIFORNIA DATE COMMISSION
**Disclosed firm income:** $12.13M across 28 clients, 2024–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at USDA via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 9. ROGER SHERMAN → FCC

**Score:** 19.143  |  **Concentration:** 100.0%

**Prior role (per LDA disclosure):** Bureau Chief, Wireless Telecommunications Bureau, FCC, 2013-2016; Chief Counsel, House Energy & Commerce Committee, 2009-2013; Deputy Chief Counsel, House Oversight & Government Reform Committee, 2007-2008

**Firm:** WANETA STRATEGIES, LLC
**Filings targeting former agency:** 45 of 45 total (100.0%)
**Clients (agency-targeting):** CTIA - THE WIRELESS ASSOCIATION | CROWN CASTLE | LYNK
**Disclosed firm income:** $0.85M across 3 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at FCC via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

### 10. AURENE MARTIN → INTERIOR

**Score:** 19.022  |  **Concentration:** 68.2%

**Prior role (per LDA disclosure):** Senior Counsel, Senate Committee on Indian Affairs Acting Assistant Secretary - Indian Affairs, Department of Interior

**Firm:** SPIRIT ROCK CONSULTING
**Filings targeting former agency:** 180 of 264 total (68.2%)
**Clients (agency-targeting):** VIDEO GAMING TECHNOLOGIES | SAGINAW CHIPPEWA INDIAN TRIBE OF MICHIGAN | PIT RIVER TRIBE | COW CREEK BAND OF UMPQUA TRIBE OF INDIANS | MASHANTUCKET PEQUOT TRIBAL NATION
**Disclosed firm income:** $24.12M across 22 clients, 2022–2026

**Verification status:** LDA figures are sourced directly from the corpus.
Prior role characterization is verbatim from covered_position field — not independently
verified against agency staff directories. See §2.5 of Finding 01 for precedent.

**⚠️ Open items before this claim is reportable:**
- [ ] Confirm prior role at INTERIOR via agency records / news archives
- [ ] Verify cooling-off period status (18 USC §207)
- [ ] Identify clients with active contracts at the targeted agency (USAspending.gov)
- [ ] Request comment from lobbyist and firm

---

## Next Steps

- [ ] Run combined Senate+House concentration analysis (currently Senate-only)
- [ ] Cross-reference top cases against press release corpus for say-vs-pay alignment
- [ ] External verification of top 5 cases (agency records, news, LinkedIn)
- [ ] Identify cases where clients hold active contracts at the former agency (USAspending)
- [ ] Request comment from top-ranked lobbyists and their firms