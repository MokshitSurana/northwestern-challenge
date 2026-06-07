# Request for comment — [FIRM] (template)

**Case:** [LOBBYIST] → [AGENCY]
**Linked findings:** scan rank #[N] (UI: `/#finding-[slug]`); trail case_id `[case_id]` (UI: `/trails#trail-[slug]`)
**Status:** ⬜ not yet sent

---

## Addressees (fill in before sending)

- **Lobbyist:** [Name] — `[email]` (source: [firm-site URL])
- **Firm press / general:** `[press@firm]`, `[info@firm]` (source: [firm-site URL])

---

## Send-ready

**Subject:** Request for comment — [FIRM]'s lobbying of [AGENCY] on behalf of [CLIENT(S)]

```
Dear [Name],

I'm a reporter working on a story about lobbying of the [AGENCY] by former
[AGENCY] officials. Our review of public Lobbying Disclosure Act filings and
USAspending.gov records indicates that:

- [Name] served as [role] at [AGENCY] until approximately [date];
- [Name] is now a registered lobbyist at [FIRM], where filings show [him/her]
  lobbying [AGENCY] on behalf of [CLIENT(S)] ([N] filings, [period]); and
- [CLIENT(S)] received approximately [$ amount] in [grants/cooperative
  agreements] from [AGENCY] during [period], per USAspending.gov.

Before publishing, I want to give you the chance to respond. Specifically:

1. Is our description of [Name]'s former [AGENCY] role and current lobbying
   accurate?
2. Does [FIRM] have any process to screen [Name]'s [AGENCY] work against the
   permanent restriction in 18 USC §207(a)(1) on matters [he/she] personally
   and substantially handled in government? Did [Name] work on any matter in
   office that overlaps with the current [CLIENT] representation?
3. How would you characterize the relationship between [Name]'s prior [AGENCY]
   service and [FIRM]'s current [AGENCY] practice?
4. Anything else you'd like on the record?

I'd be grateful for a reply by [DEADLINE, 5 business days out]. I'm happy to
take a written statement or talk by phone.

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

Mirror the timeline into `comment_log.json` under this firm's entry.

---

## Internal notes (do not paste into the email)

- Money figure to confirm if asked: `[$ amount]`
- §207 cooling-off status (from notes/09): `[Clear | Pending pin]`
- Per-case substance / framing to weave into the request: `[from notes/09 §"Per-case specifics"]`
- Sources backing the claims: `[LDA UUIDs, USAspending award IDs, notes/08 anchor]`
