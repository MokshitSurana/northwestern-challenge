# Finding 01 (Anchor Case Study): The Artemis Group

**Working title:** The Pipeline — How a Former NASA Administrator Built a Lobbying Firm Around His Old Team, Now Targeting His Old Agency

**Status:** Draft v2. Replaces v1. All quantitative claims sourced to `output/investigation.duckdb` and the underlying Senate LDA corpus. External biographical claims sourced to public reporting and official sources.

---

## Executive summary

In Q4 2024, former NASA Administrator Jim Bridenstine (April 2018 – January 2021) launched a lobbying firm called The Artemis Group, LLC, named after the lunar exploration program he established during his tenure. Within five quarters of operation, the firm has filed 133 Senate lobbying disclosures, 52 of which name NASA itself as a lobbying target — the highest NASA concentration of any third-party lobbying firm with significant volume in the corpus.

The firm is not simply Bridenstine. Five of the firm's named lobbyists previously held senior positions in government, and four of them worked directly under Bridenstine — three in his congressional office and one (Gabe Sherman) as his NASA Chief of Staff. Five of the top twelve most-active NASA-targeting lobbyists in the entire 2022-2026 Senate LDA corpus work at this single firm. The firm's NASA-targeting work is conducted on behalf of clients whose business overlaps directly with NASA programs Bridenstine personally established or expanded as Administrator: Commercial Lunar Payload Services (CLPS), Commercial LEO Destinations, and the Artemis program itself.

In May 2026, Bridenstine departed the firm to become CEO of Quantum Space — a former Artemis Group client. Sherman, his former NASA Chief of Staff, ascended to managing partner of the firm.

We do not allege any legal violation. The cooling-off period applicable to Bridenstine ran out in January 2022, nearly three years before he registered as a lobbyist. The story is the systematic concentration of former NASA and Bridenstine-affiliated personnel inside a lobbying firm specifically focused on NASA, on behalf of clients with business under programs Bridenstine personally established. SpaceX raised the individual conflict-of-interest concern publicly in October 2025. This analysis documents the structural shape of the pattern using the underlying LDA record.

---

## 1. The career timelines

### Jim Bridenstine

| Date                        | Role                                                  |
| --------------------------- | ----------------------------------------------------- |
| 2013 – Apr 2018             | U.S. Representative (R-OK-1)                          |
| Apr 23, 2018 – Jan 20, 2021 | 13th Administrator, NASA                              |
| Jan 25, 2021                | Senior Advisor, Acorn Growth Companies                |
| Apr 1, 2021                 | Board of Directors, Viasat                            |
| Apr 7, 2021                 | Chair of Advisory Board, Voyager Space Holdings       |
| Jan 2024                    | Board of Directors, Starlab Space (Voyager/Airbus JV) |
| Q4 2024                     | First lobbying filings under The Artemis Group        |
| May 2026                    | CEO, Quantum Space (former Artemis Group client)      |

Sources: NASA biography; Wikipedia (sourced to underlying press releases); Acorn Growth, Viasat, Voyager press releases; Payload Space (May 2026).

### Gabe Sherman

| Date                | Role                                                                |
| ------------------- | ------------------------------------------------------------------- |
| Pre-2013            | Tulsa Air & Space Museum (with Bridenstine, who served as director) |
| 2013 – 2018         | District Director, Office of Rep. Jim Bridenstine, OK-1             |
| 2018 – Jan 2020     | Deputy Chief of Staff, NASA                                         |
| Jan 2020 – Jan 2021 | Chief of Staff, NASA                                                |
| 2024 – May 2026     | Senior Partner, then Managing Partner, The Artemis Group            |

Source: NASA Watch (Jan 2020); Sooner Politics (Nov 2016); Payload Space (May 2026).

Sherman has worked alongside Bridenstine continuously since at least 2013 — first at a museum they both led, then in his congressional office, then as his Chief of Staff at NASA, then at the lobbying firm. The relationship spans 12+ years and crosses three institutional boundaries: civic non-profit, legislative branch, executive branch agency, and private lobbying.

### Mark Piland

Vice President of Government Affairs, The Artemis Group (June 2025–). Prior role per his Senate LDA covered_position: "Chief of Staff/Legislative Director/Senior Legislative Assistant/Legislative Correspondent — Rep. Jim Bridenstine." Currently also Chief of Staff to Rep. Ralph Norman. Source: LegiStorm; covered_position records in `senate_lobbyists`.

### Christopher Ingraham

Per his covered_position: "Professional staff — House Space Subcommittee; Senior Policy Advisor — Rep. Jim Bridenstine; LA — Rep. Trey Gowdy."

### Kathryn Wall

Vice President of Federal Affairs, The Artemis Group. Prior role per covered_position: "Chief of Staff, National Space Council; Deputy Director of Scheduling, Office of the Vice President." Source: ZoomInfo public profile. The National Space Council was the White House body chaired by the Vice President that coordinated NASA policy with the executive branch during Bridenstine's tenure as Administrator.

### Shawn Barnes

Per his covered_position: "Deputy Assistant Secretary of the Air Force, Congressional Budget and Appropriations Liaison."

**Cooling-off period analysis.** As a presidentially-appointed Executive Schedule official, Bridenstine was subject to a one-year cooling-off period prohibiting communications-based lobbying of his former agency, plus a permanent ban on "particular matters" he was personally and substantially involved in. He waited 47 months between leaving NASA (January 2021) and his first lobbying registration (Q4 2024). **No cooling-off violation is alleged.** During the interim, he held board, advisory, and consulting positions at multiple companies he would later represent as a registered lobbyist.

---

## 2. The firm

**Name:** The Artemis Group, LLC (Oklahoma)
**Registrant ID:** 401108974 (Senate LDA)
**Founded:** Q4 2024
**Total Senate filings:** 133
**Total disclosed firm income:** ~$4.76M
**Distinct clients:** 27

**Significance of the name.** "Artemis" is the lunar exploration program Bridenstine launched as Administrator. From NASA's biography of Bridenstine: under his leadership, "NASA launched its new human lunar exploration mission, the Artemis program."

**Firm self-description (theartemisgroup.space):** "Led by former NASA Administrator and U.S. Congressman Jim Bridenstine, The Artemis Group provides critical government affairs, business development, and strategic advisory services to space and defense companies."

---

## 3. The firm-level concentration on NASA

Across the entire 2022-2026 Senate LDA corpus, 1,658 distinct filings target NASA as a lobbying activity. The Artemis Group is the registrant on 52 of them, or 3.14% of corpus-wide NASA lobbying.

That share is small in absolute terms — but the firm has only existed for 5 quarters, and the more meaningful metric is the firm's own concentration:

| Metric                                 |     Value |
| -------------------------------------- | --------: |
| Artemis Group total filings            |       133 |
| Artemis Group NASA-targeting filings   |        52 |
| **NASA's share of the firm's filings** | **39.1%** |

Among third-party lobbying firms with 50+ total filings since 2024, this is the highest NASA concentration in the corpus. The next firms in the same volume class are Elizabeth Lavach (66 filings, 27.3% NASA) and Federal Science Partners (110 filings, 21.8% NASA). The next-largest pure NASA-specialist boutique, Policy Navigation Group, has 42 filings at 54.8% NASA — higher concentration but less than a third of Artemis Group's volume.

**Framing:** Among lobbying firms that have built scale rather than operating as solo or boutique practices, The Artemis Group is the most NASA-concentrated in the corpus.

For reference, the largest third-party lobbying firm with significant NASA practice is Actum I, LLC (470 total filings, 80 NASA-targeting, 17.0% NASA share). Actum's top lobbyists (Kelly, Lipin, Thomson, Regan) outrank Artemis Group lobbyists individually by NASA filing count — but Actum is a generalist firm where space is one practice area; Artemis Group is built around it.

---

## 4. The personnel concentration

Five of the top twelve most-active NASA-targeting lobbyists in the entire 2024-2026 Senate LDA corpus are Artemis Group employees:

|   Rank | Lobbyist                 | Firm                  | NASA filings (2024-2026) |
| -----: | ------------------------ | --------------------- | -----------------------: |
|      1 | Kevin Kelly              | Actum I               |                       80 |
|      2 | Lauren Lipin             | Actum I               |                       62 |
|  **3** | **Christopher Ingraham** | **The Artemis Group** |                   **40** |
|      4 | Jasper Thomson           | Actum I               |                       39 |
|  **5** | **Mark Piland**          | **The Artemis Group** |                   **36** |
|      6 | Jeffrey Regan            | Actum I               |                       34 |
|  **7** | **Gabe Sherman**         | **The Artemis Group** |                   **32** |
|      8 | Matt Trant               | National Group        |                       29 |
|      9 | Vincent Versage          | National Group        |                       29 |
|     10 | Alexander Rauda          | Actum I               |                       25 |
| **11** | **Kathryn Wall**         | **The Artemis Group** |                   **24** |
| **12** | **Jim Bridenstine**      | **The Artemis Group** |                   **24** |

Of these five Artemis Group lobbyists:

- **Bridenstine** was the NASA Administrator who created the Artemis program.
- **Sherman** was the NASA Chief of Staff under Bridenstine.
- **Piland** was Bridenstine's Chief of Staff in Congress.
- **Ingraham** was Bridenstine's Senior Policy Advisor in Congress and prior House Space Subcommittee staff.
- **Wall** was Chief of Staff of the National Space Council — the White House body coordinating NASA policy during Bridenstine's tenure as Administrator.

Three of these five (Bridenstine, Sherman, Ingraham) have direct NASA work history. The remaining two (Piland, Wall) have NASA-adjacent policy roles. All five now target NASA together at the same firm.

---

## 5. The program overlap

Filing-level activity descriptions in the Senate LDA corpus show The Artemis Group's lobbying directly references NASA programs Bridenstine personally established or expanded:

**Voyager Space Holdings → Commercial LEO Destinations.** Voyager's Starlab project was selected as a successor to the International Space Station under NASA's Commercial LEO Destinations initiative, expanded under Bridenstine. Bridenstine chaired Voyager's advisory board from April 2021. The Artemis Group registered as Voyager's lobbyist beginning Q4 2024.

**Redwire → Gateway Program.** Multiple Redwire filings explicitly state: _"Monitor NASA Authorization Act; Support Gateway Program"_ and _"Monitor NASA Authorization Act; support H.R. 1, One Big Beautiful Bill Act; Support Gateway Program."_ The Gateway lunar orbital station was a flagship initiative of Bridenstine's Artemis program. (Filing UUIDs: ed029cc5-dffa-4185-ad09-9fa9ba29bced; 6a45f115-c799-4b75-b10c-4d00daf92161.)

**Lunar Outpost → Commercial Lunar Payload Services.** Lunar Outpost holds a NASA contract for lunar rover services. The CLPS program was established by Bridenstine: "Bridenstine established the Commercial Lunar Payload Services Program to partner with private enterprise in landing rovers on the lunar surface." Lunar Outpost's Artemis Group filing description: _"Enabling lunar surface mobility"_ — directly within CLPS scope.

**Impulse Space → NASA Authorization.** Filing description: _"Monitor space issues generally; NASA Authorization."_

**United Launch Alliance → NASA Authorization Act, NDAA, Defense Appropriations.** ULA filings consistently name: _"Monitor NASA Authorization Act; Defense Appropriations; NDAA."_ ULA's NASA Launch Services contracts predate Bridenstine's tenure but were ongoing during it.

**University of Arizona → OSIRIS-APEX.** Multiple filings name _"Support OSIRIS-APEX mission"_ — a NASA mission with the University of Arizona as principal investigator.

---

## 6. Government entities targeted

Bridenstine's filings personally (24 NASA-targeting filings on behalf of 9 clients):

| Entity                            | Filings | Clients |
| --------------------------------- | ------: | ------: |
| Senate                            |      40 |      10 |
| House of Representatives          |      40 |      11 |
| **NASA**                          |  **24** |   **9** |
| Executive Office of the President |      16 |       6 |
| Department of Defense             |      16 |       5 |
| Federal Aviation Administration   |       4 |       2 |
| Air Force, Dept of                |       3 |       1 |
| Department of Transportation      |       3 |       1 |
| Office of Management & Budget     |       2 |       2 |
| Office of the Vice President      |       1 |       1 |
| Department of Interior            |       1 |       1 |
| Department of Energy              |       1 |       1 |

The NASA-targeting filings are distributed across nine of his 24 clients, with University of Arizona (5 filings) and All Points LLC (5 filings) most frequent.

Sherman's filings show a parallel pattern: 32 NASA-targeting filings on behalf of 9 clients, with substantial overlap in the client roster. He targets NASA more frequently than Bridenstine in absolute terms.

---

## 7. The Quantum Space transition (May 2026)

In May 2026, Bridenstine departed The Artemis Group to become CEO of Quantum Space — a company that was, until that point, an Artemis Group lobbying client. Quantum Space appears in the Senate LDA corpus with one Artemis Group filing dated Q1 2025.

Per Payload Space (May 2026): "Gabe Sherman, a senior partner at the Artemis Group and former NASA chief of staff, will take over as managing partner."

The transition extends the revolving-door pattern by one additional step. Bridenstine moved from regulator (NASA Administrator) → board director and advisor at multiple aerospace companies → lobbyist representing those same companies → CEO of one of those companies. The arc is now: regulator → lobbyist → executive at a regulated entity.

This development is too recent to appear in the corpus directly, but it provides essential framing for the firm's current state.

The pattern is consistent across both chambers of Congress's LDA disclosure regimes. The Artemis Group's 115 House filings parallel its 133 Senate filings, with the same client roster and the same five-lobbyist personnel core (Bridenstine, Sherman, Piland, Ingraham, Wall) named consistently in both chambers' records.

---

## 8. Procurement specificity (negative finding)

The Artemis Group's filings name no specific federal contract solicitations, RFPs, task orders, awards, or procurement decisions in their activity descriptions. The firm operates at the level of general appropriations and authorization legislation, not contract-specific advocacy.

This is itself a finding: it tells us how the firm operates. Lobbying at the appropriations level shapes the funding envelope for NASA programs without requiring case-by-case procurement intervention.

---

## 9. Press release corpus scan (largely negative)

No member of Congress has named The Artemis Group in any press release in the 2024-2026 corpus. Three press releases mention "Bridenstine" by name, none in any political context related to his current lobbying work. The pattern has not entered congressional political discourse.

The members of Congress most likely to be lobbied by the firm — those on the Senate Commerce Committee and House Science Committee with jurisdiction over NASA appropriations and authorization — issued press releases throughout 2024-2026 advocating for NASA programs that overlap with Artemis Group client work (notably Sen. Jerry Moran on NASA Reauthorization, Rep. Valerie Foushee on the Artemis program, Rep. Dale Strong on Marshall Space Flight Center funding). None named the firm or its lobbyists. We do not allege coordinated messaging.

**One narrow alignment worth noting:** Rep. Brittany Pettersen (D-CO) issued a March 2024 press release naming Lunar Outpost as a beneficiary of "Colorado Space Innovation" funding. Lunar Outpost did not register with The Artemis Group until Q4 2025, so this predates the lobbying relationship by over 18 months and is not evidence of say-vs-pay alignment.

---

## 10. What this finding does and does not establish

**Establishes:**

- The Artemis Group is the most NASA-concentrated third-party lobbying firm of significant volume in the corpus (39.1% of filings target NASA).
- Five of the top twelve most-active NASA-targeting lobbyists in the corpus work at this single firm.
- Four of the firm's named lobbyists (Sherman, Piland, Ingraham, Bridenstine) worked directly under Bridenstine in his government roles. A fifth (Wall) ran the National Space Council that coordinated with NASA during his tenure.
- The firm's clients have business under specific NASA programs Bridenstine established or expanded (CLPS, Commercial LEO Destinations, Gateway).
- Bridenstine departed in May 2026 to become CEO of Quantum Space, a former Artemis Group client.

**Does not establish:**

- Any violation of the cooling-off period or other legal restriction. The cooling-off period expired in January 2022.
- Any violation of permanent post-employment restrictions on "particular matters." Establishing this would require records of Bridenstine's specific NASA activities, outside this corpus.
- That any client received favorable treatment as a result of lobbying.
- That any member of Congress publicly aligned with positions Bridenstine has advocated as a lobbyist.

**Income figures.** Firm-disclosed income on filings is firm-level revenue, not personal compensation for the named lobbyist. The disclosed total across all Artemis Group filings is approximately $4.76M; the figures above reflect filing-level disclosures, many of which are blank.

---

## 11. Why this is reportable

Prior public coverage (SpaceX's October 2025 statement, follow-on trade press at SpaceNews and Teslarati) raised the individual conflict-of-interest concern about Bridenstine personally. This analysis documents the structural shape of the pattern:

- It is not one former Administrator. It is a firm with concentrated former-NASA-and-Bridenstine personnel.
- The firm's name openly references a program its founder created.
- The pattern is quantifiable as a firm-level concentration metric, not just an individual observation.
- The Quantum Space transition (May 2026) extends the pattern to a third stage.

The systematic, filing-level documentation is the original contribution. The conflict-of-interest claim itself is not novel; the _structural form_ of the pattern is.

---

## 12. Open items and next investigation

- [x] House LDA cross-validation complete. The Artemis Group registered 115 House filings; Bridenstine is named on 125 House lobbyist rows across these filings. Senate↔House reconciliation confirmed via senate_id field. The firm files on both chambers consistently with no material discrepancies.
- [ ] Andrew Hevener — fifth Artemis Group lobbyist with no disclosed covered_position. Background unknown.
- [ ] Whether any Artemis Group filing references the National Space Council itself as a target (Wall's prior post).
- [ ] Whether Lunar Outpost's NASA CLPS contract date can be pinned more precisely than "post-2020."
- [ ] Sherman's full activity descriptions (parallel to the Bridenstine breakdown in §5).

**This case study motivates a structural query: how many other former agency heads in the corpus run lobbying firms with similar concentration on their former agency, populated by former colleagues?** That query is the next finding — see `notes/06_structural_pattern.md` (forthcoming).

---

## Appendix A: Complete Artemis Group lobbyist roster

| Lobbyist             | Filings | Clients | Prior government role                                                |
| -------------------- | ------: | ------: | -------------------------------------------------------------------- |
| Gabe Sherman         |      80 |      24 | NASA Chief of Staff; District Director, Rep. Bridenstine             |
| Jim Bridenstine      |      73 |      24 | NASA Administrator; U.S. Representative                              |
| Mark Piland          |      70 |      21 | Chief of Staff, Rep. Ralph Norman; Chief of Staff, Rep. Bridenstine  |
| Christopher Ingraham |      69 |      22 | House Space Subcommittee staff; Sr. Policy Advisor, Rep. Bridenstine |
| Kathryn Wall         |      46 |      16 | Chief of Staff, National Space Council; Office of the Vice President |
| Andrew Hevener       |      14 |       9 | (no covered_position disclosed)                                      |
| Shawn Barnes         |       7 |       4 | Deputy Asst. Secretary of the Air Force                              |

## Appendix B: Source records

Senate LDA corpus, `output/investigation.duckdb`, queries Q7–Q22 (see `notes/05c_verification_round_2.txt`). External sources: NASA biography of Jim Bridenstine; Wikipedia entry for Jim Bridenstine; Acorn Growth Companies, Viasat, Voyager Space press releases (2021); Starlab Space announcement (January 2024); SpaceX public statement (October 31, 2025); Teslarati (Oct 31, 2025); SpaceNews (Nov 13, 2025); Payload Space (May 2026); NASA Watch (January 16, 2020); LegiStorm; ZoomInfo public profile (Kathryn Wall); Sooner Politics (November 2016).
