# Request for comment — Venn Strategies

**Case:** Benjamin Steinberg → Department of Energy
**Linked findings:** scan rank #1 (UI: `/#finding-benjamin-steinberg-energy`); trail case_id `steinberg_doe` (UI: `/trails#trail-steinberg-doe`)
**Status:** ⬜ not yet sent

---

## Addressees (fill in before sending)

- **Lobbyist:** Benjamin Steinberg — find current email on `vennstrategies.com` team page
- **Firm press / general:** `info@vennstrategies.com` (verify on vennstrategies.com Contact page)

---

## Send-ready

**Subject:** Request for comment — Venn Strategies' lobbying of the Department of Energy on behalf of nine battery and critical-minerals clients

```
Dear Mr. Steinberg,

I'm a reporter working on a story about lobbying of the Department of Energy by
former DOE officials. Our review of public Lobbying Disclosure Act filings and
USAspending.gov records indicates that:

- You served in senior roles at the Department of Energy, including in the
  Office of Energy Policy and Systems Analysis (EPSA), until approximately
  2017;
- You are now a registered lobbyist at Venn Strategies, where Senate LDA
  filings show 213 of your 236 filings (about 90%) target the Department of
  Energy, on behalf of a roster of battery and critical-minerals clients
  including Cirba Solutions, EnerSys, South32 Hermosa, Sila Nanotechnologies,
  Anovion, Talon Nickel, Forge Battery, Cabot Corp, and Nanoramic; and
- Those nine clients received approximately $1,080,820,047 in 16 federal
  grants from the Department of Energy between 2021-01-01 and 2026-06-04, per
  USAspending.gov, the bulk of which appear to be discretionary
  Bipartisan-Infrastructure-Law battery-supply-chain awards rather than
  routine program participation.

Before publishing, I want to give you the chance to respond. Specifically:

1. Is our description of your former DOE role and current lobbying accurate?
   We have characterized your former position as a senior EPSA role; please
   correct us if a different characterization is more accurate.
2. Does Venn Strategies have any process to screen your DOE work against the
   permanent restriction in 18 USC §207(a)(1) on matters you personally and
   substantially handled in government? Did you work on any matter in office
   that overlaps with the current representation of any of the nine clients
   listed above — for example, on battery-supply-chain policy, critical-
   minerals strategy, or any specific grant program under which these awards
   were made?
3. How would you characterize the relationship between your prior DOE service
   and Venn Strategies' current DOE practice?
4. Anything else you'd like on the record?

I'd be grateful for a reply by [DEADLINE — 5 business days from send]. I'm
happy to take a written statement or talk by phone.

Thank you,
[Reporter signature]
```

---

## Response log

- ⬜ Sent: `[ISO-8601 datetime]` to `[addresses]`
- ⬜ Acknowledged: `[datetime]` by `[name]` — `[brief]`
- ⬜ Substantive reply received: `[datetime]` — see `[pointer]`
- ⬜ Follow-up sent: `[datetime]`
- ⬜ Closed: `[response | no_response]` at `[datetime]`

Mirror the timeline into `comment_log.json` under `venn_strategies`.

---

## Internal notes (do not paste into the email)

- **Money figure to confirm:** $1,080,820,046.02 across 9 clients, 16 awards. Reproducible via `uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json`.
- **§207 status:** Clear on timed bans (departure ≤ 2017, first observed lobbying 2022 — gap > 4 years; see `notes/09` table). Press §207(a)(1) particular-matter question.
- **Role caveat:** Steinberg's covered-position disclosure cites EPSA office Chief of Staff, *not* agency-wide CoS. Be precise — overstating the seniority is the easiest error here (see `notes/08` #1).
- **Sources:** LDA UUID `fedf1282-ee62-4cd4-a04e-61501a367ed7` (filings_2025.json); USAspending recipient names captured in `output/steinberg_awards.json` (run with `--json` to refresh).
