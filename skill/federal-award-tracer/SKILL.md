---
name: federal-award-tracer
description: >
  Follows the money behind a revolving-door case. Given a lobbyist, their client
  list, and the federal agency they target, this traces the federal awards each
  client received from that agency on USAspending.gov, verifies every row against
  the recipient's real name, and produces a journalism-ready markdown table plus a
  framing note that separates discretionary grants (newsworthy) from routine program
  participation (commodity purchases, food aid, formula financing). Use this skill
  whenever you need to quantify the dollars flowing from an agency to a lobbyist's
  clients — the "follow the money" companion to revolving-door-detector. Reach for it
  any time someone asks how much an agency awarded a company, mentions USAspending,
  federal grants/contracts, or wants to put a dollar figure on a conflict of interest.
version: 1.0.0
author: FairGuard (Mokshit Surana, Archit Rathod)
license: MIT
tools: [bash, python, file-read, file-write]
requires_python: ">=3.11"
---

# federal-award-tracer

## What this skill does

`revolving-door-detector` finds the *structure* — a former official whose firm
concentrates its lobbying on the agency they used to run. This skill answers the
follow-up every editor asks: **how much money is actually moving?**

Given a lobbyist, their lobbying clients, and a target federal agency, it queries
USAspending.gov for the awards each client received from that agency, then emits:

1. A **per-client table** of recipient-name-verified award totals, sorted high to low.
2. A **framing note** that splits the total into *discretionary* dollars
   (competitively-awarded grants — the newsworthy core) versus *routine* program
   participation (commodity purchases, food aid, formula financing — context).

The framing distinction is the point. A billion dollars in discretionary battery
grants to a lobbyist's clients is a story; a billion dollars in routine commodity
purchases is not. This skill keeps you from conflating the two.

## Why a dedicated skill (the three gotchas)

The USAspending API (`POST /api/v2/search/spending_by_award/`) has three traps that a
fresh agent hits every single time. All three are handled inside the script, which is
the main reason this is worth capturing as a skill rather than re-deriving each run:

1. **One award-type group per request.** `award_type_codes` must come from a single
   group — mixing grants (`02–05`) with loans (`07–08`) returns **HTTP 422**. The
   script queries each requested group separately and combines the results.
2. **Loans can't sort by amount.** Asking USAspending to sort loan awards by
   "Award Amount" returns **HTTP 400**. Loans are sorted by recipient name instead,
   and are **excluded by default** so published totals stay conservative.
3. **`recipient_search_text` is fuzzy.** Searching "Cargill" also returns
   "Paseo Cargill Energy"; searching "Nutrien" matches "4R Nutrient". Every row is
   filtered against caller-supplied **name tokens** that must appear in the real
   `Recipient Name` before it counts toward a total.

## Inputs

A **case file** (JSON) describing the lobbyist, the agency, the award groups, and the
clients. Run `uv run scripts/04_award_tracer.py --print-template` to see the schema.

```json
{
  "lobbyist": "Steinberg (battery / critical-minerals clients)",
  "agency": "Department of Energy",
  "award_groups": ["grants"],
  "time_period": {"start": "2021-01-01", "end": "2026-06-04"},
  "clients": [
    {"label": "Cirba Solutions", "search": "Cirba Solutions", "name_tokens": ["CIRBA SOLUTIONS"]}
  ]
}
```

| Field | Meaning |
|-------|---------|
| `lobbyist` | Display label for the case (appears in the report heading) |
| `agency` | USAspending **toptier** awarding-agency name (e.g. `Department of Energy`, `Department of the Interior`, `Department of Agriculture`) |
| `award_groups` | Any of `grants`, `contracts`, `direct`, `loans`. Grants are the usual choice; add `direct`/`contracts` to capture commodity purchases and food aid |
| `clients[].label` | Display name in the table |
| `clients[].search` | `recipient_search_text` sent to the API (fuzzy) |
| `clients[].name_tokens` | Uppercase fragments; a row counts only if one appears in the real `Recipient Name` |

**Network required** — this makes live HTTPS calls to `api.usaspending.gov`. It does
*not* touch `output/investigation.duckdb`.

## Outputs

| Destination | Description |
|-------------|-------------|
| stdout (or `--out FILE`) | The markdown table + framing note |
| `--json FILE` (optional) | Raw per-client results: totals, award counts, recipient names, per-award sub-agency / type for auditing the split |

## Invocation

```bash
# Print the case-file schema
uv run scripts/04_award_tracer.py --print-template

# Trace a case, markdown to stdout
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json

# Write the markdown to a notes file and dump raw JSON alongside
uv run scripts/04_award_tracer.py \
  --case skill/federal-award-tracer/cases/limbaugh_interior.json \
  --out notes/limbaugh_money_trail.md \
  --json output/limbaugh_awards.json
```

## Choosing name tokens (the part that needs judgment)

The whole accuracy of the total rides on the `name_tokens`. Guidance:

- **Start specific, then loosen only if you miss real rows.** `["CIRBA SOLUTIONS"]`
  is safer than `["CIRBA"]`. Run once, read the "Recipient name(s) on file" column,
  and adjust.
- **Watch for spelling drift in the recipient record.** The USAspending recipient for
  Glenn-Colusa is spelled `GLENN COLUSA IRRIGATION DIST` (a space, no hyphen), so the
  token set is `["GLENN COLUSA", "GLENN-COLUSA"]`. If a client returns `--` in the
  output, a token/recipient spelling mismatch is the first thing to check.
- **For corporate families, list each operating entity you mean to include.** Cargill
  files awards under `CARGILL, INCORPORATED`, `CARGILL MEAT SOLUTIONS CORPORATION`, and
  `CARGILL KITCHEN SOLUTIONS, INC` — listing all three captures the real footprint
  while still excluding unrelated "Cargill"-named entities.

## Reading the framing note

The script flags awards whose **awarding sub-agency** matches known routine-program
signals (Agricultural Marketing Service, Foreign Agricultural Service, Farm Service
Agency, Rural Utilities/Housing/Business services, Commodity Credit Corporation, Food
and Nutrition Service) and reports the discretionary-vs-routine split, with a
collapsible breakdown of which sub-agencies drove the "routine" bucket.

These are **heuristics to steer your reporting, not verdicts.** A USDA Climate-Smart
Commodities cooperative agreement is discretionary even though it comes from USDA;
a Rural Utilities Service loan-equivalent is routine even though it's large. Always
open the award on USAspending and confirm the program before you publish a number as
"discretionary."

## Interpreting results responsibly

Frame every figure as conflict-of-interest **structure, not proven wrongdoing**:

1. The dollars show the agency *can* steer money to the lobbyist's clients — not that
   the lobbyist caused any specific award.
2. Discretionary, competitively-awarded grants from the former official's agency to
   that official's clients are the story; routine program participation is context.
3. Before publishing a causal claim, confirm the cooling-off status (18 USC §207),
   the award's program type, and **seek comment** from the lobbyist and firm.

## Reproducible reference cases

Three verified case files ship in `cases/`, reproducing the money trails documented in
`notes/08_external_verification_top_candidates.md`:

| Case file | Trail | Verified total |
|-----------|-------|---------------:|
| `cases/steinberg_doe.json` | Steinberg's battery / critical-minerals clients → DOE grants | $1,080,820,046 |
| `cases/limbaugh_interior.json` | Limbaugh's water-district clients → Interior/Reclamation grants | ≈ $161.7M (Glenn-Colusa Reclamation award counted under Reclamation, see notes/08) |
| `cases/usda_cases.json` | USDA clients → grants + direct + contracts | $1,398,877,777 (≈ 97% routine; Global Clean Energy's NRCS Climate-Smart award is the discretionary exception) |

Run any of them to reproduce the published figures. The Steinberg and USDA totals
match to the dollar; the USDA case is the canonical demonstration of the
discretionary-vs-routine split.

## Data limitations

- **Live API, point-in-time.** USAspending updates continuously; re-running may shift
  totals as awards are amended. Record the run date with any published figure.
- **Loans excluded by default.** Totals are conservative; add `"loans"` to
  `award_groups` only if you handle the sort caveat and disclose it.
- **Toptier agency name must match USAspending's spelling exactly.** Use the agency's
  canonical name (e.g. `Department of the Interior`, not `Interior` or `DOI`).
- **Routine-signal list is sub-agency-based and not exhaustive.** It catches the
  common USDA formula/commodity programs; for other departments, audit the `--json`
  output's per-award `subagency`/`award_type` rather than trusting the auto-split.
