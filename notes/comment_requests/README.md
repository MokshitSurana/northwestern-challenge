# Comment requests — send packet

**Purpose.** No conflict-of-interest story ships without a real, documented attempt to let the subject respond. This directory holds ready-to-paste request-for-comment drafts for every named firm in the structural finding, plus a tracking log so responses (or non-responses) are recorded with timestamps a fact-checker can audit.

**Source of substance.** Drafts and per-case specifics come from `notes/09_reportability_gates_207_and_comment.md`. This directory turns those into copy-paste-ready packets and a machine-readable log.

---

## Files

| File | Purpose |
|------|---------|
| `_template.md` | The reusable template from `notes/09` — start here if drafting a new request. |
| `venn_strategies.md` | Steinberg → DOE. Strongest financial case (~$1.08B in discretionary BIL grants). |
| `ferguson_group.md` | Limbaugh → Interior. Direct topical overlap with prior agency role; press §207(a)(1) hard. |
| `delta_strategy_group.md` | Newsome + Parsons → CFTC. Two former senior officials at one firm; regulatory access story. |
| `torrey_advisory_group.md` | Torrey → USDA. Mostly routine program dollars; weaker conflict signal — say so. |
| `invariant_llc.md` | Barbic → USDA. The discretionary standout (Global Clean Energy $32.26M NRCS grant). Also asks about the 2021 USDA-contact timing question. |
| `waneta_strategies.md` | Sherman → FCC. Wireless Telecom Bureau Chief now lobbying FCC for telecom clients. |
| `spirit_rock_consulting.md` | Martin → Interior. Tribal-affairs lobbying; money trail inconclusive — frame as access/optics, not dollars. |
| `comment_log.json` | Machine-readable log of every send attempt and response. Update after every action. |

The four †-flagged USDA cases (Johnson / Bailey / Torrey / Barbic) share an aggregated USAspending money trail; the Torrey and Barbic packets cover the discretionary-vs-routine split at the firm level. **Before publication, send individual requests to The Russell Group (Ashlee Johnson) and FGS Global (Kevin Bailey) too** — drafts not yet prepared because their cases turn on the same USDA aggregate.

---

## Workflow

1. **Find the addressees.** For each firm, look up:
   - The named lobbyist's professional contact on the firm's website team / leadership page.
   - The firm's press / general / info inbox.
   The starting URLs are in `notes/08_external_verification_top_candidates.md` under "Source URLs."
2. **Set the deadline.** 5 business days from send is the working standard. Use a Tuesday or Wednesday send so the deadline doesn't fall on a Monday holiday.
3. **Send to both addresses** (lobbyist + firm press), in writing. Email is fine; CC counsel if the outlet's policy requires it.
4. **Log the send immediately** in `comment_log.json` with the exact ISO-8601 datetime and the addresses used.
5. **If acknowledged but no substantive reply**, log the acknowledgment, then follow up once at the deadline + 24 hr. After that, treat as non-response.
6. **If no reply at all by deadline + 24 hr**, log as `no_response` with the deadline date. The findings report can then say `"{Firm} did not respond to multiple requests for comment by {date}."` — defensible and standard.
7. **On any substantive reply**, log the reply verbatim (or a paraphrase plus a link to the saved email), and update the corresponding finding's verification status in `web/public/findings.json` (or wait for the next scan run to refresh).

---

## What to do with responses

- **Affirmation** of facts → no edit needed; quote or paraphrase per the response.
- **Correction** of a specific fact → fix in `findings/findings_report.md` and the underlying skill output; note the correction with attribution in the report.
- **§207(a)(1) particular-matter answer** ("[Name] did/did not work on this matter in government") → if a clean denial, include the denial verbatim; if a partial answer, flag for further reporting before publishing.
- **Legal threat** → stop, escalate to counsel, document the threat in `comment_log.json` under that firm's entry. Do not delete or modify any committed material.

---

## Privacy note

`comment_log.json` is committed to the repo so a fact-checker can audit the outreach record. Do **not** paste private email contents into the log — store the substance plus a pointer to where the full text lives (a shared drive, an email thread reference, etc.). Same for personal phone numbers: log the date/time of the call and a one-line outcome, not the number.
