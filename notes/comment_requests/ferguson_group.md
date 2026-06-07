# Request for comment — The Ferguson Group, LLC

**Case:** Mark Limbaugh → Department of the Interior
**Linked findings:** scan rank #2 (UI: `/#finding-mark-limbaugh-interior`); trail case_id `limbaugh_interior` (UI: `/trails#trail-limbaugh-interior`)
**Status:** ⬜ not yet sent

---

## Addressees (fill in before sending)

- **Lobbyist:** Mark Limbaugh — find current email on `tfgnet.com` (The Ferguson Group) team page
- **Firm press / general:** `info@tfgnet.com` (verify on tfgnet.com Contact page)

---

## Send-ready

**Subject:** Request for comment — The Ferguson Group's lobbying of the Department of the Interior on behalf of nineteen Western water districts

```
Dear Mr. Limbaugh,

I'm a reporter working on a story about lobbying of the Department of the
Interior by former Interior officials. Our review of public Lobbying
Disclosure Act filings and USAspending.gov records indicates that:

- You served as Assistant Secretary for Water and Science at the Department
  of the Interior, with direct oversight of the Bureau of Reclamation, until
  approximately 2007;
- You are now a registered lobbyist at The Ferguson Group, where Senate LDA
  filings show 527 of your 726 filings (about 73%) target the Department of
  the Interior, on behalf of a roster of nineteen Western water districts and
  related entities including Sites Project Authority, Glenn-Colusa Irrigation
  District, Friant Water Authority, Reclamation District 108, Turlock
  Irrigation District, and The Freshwater Trust; and
- Those nineteen clients received approximately $161,687,512 in federal
  grants from the Department of the Interior — primarily through the Bureau
  of Reclamation — between 2021-01-01 and 2026-06-04, per USAspending.gov.

Before publishing, I want to give you the chance to respond. Specifically:

1. Is our description of your former Interior role and current lobbying
   accurate?
2. Does The Ferguson Group have any process to screen your Interior work
   against the permanent restriction in 18 USC §207(a)(1) on matters you
   personally and substantially handled in government? Given that your
   portfolio at Interior covered the Bureau of Reclamation directly, did you
   personally and substantially work on any specific water-project, grant
   program, or rulemaking that is now the subject of your representation of
   any of the nineteen Western water clients listed above?
3. How would you characterize the relationship between your prior Interior
   service and The Ferguson Group's current Interior practice?
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

Mirror the timeline into `comment_log.json` under `ferguson_group`.

---

## Internal notes (do not paste into the email)

- **Money figure to confirm:** ~$161,687,512 across 19 water districts. Reproducible via `uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/limbaugh_interior.json`.
- **§207 status:** Clear on timed bans (departure 2007, first observed lobbying 2022 — gap 15 years).
- **Why press §207(a)(1) hard here:** Limbaugh's Asst. Sec. portfolio *was* the Bureau of Reclamation; the current clients are Reclamation grant recipients. Topical overlap is direct in a way it isn't for many cases.
- **Sources:** LDA records for Mark Limbaugh at The Ferguson Group, 2022–2026 (sample UUID captured in `web/public/findings.json` row for rank #2).
