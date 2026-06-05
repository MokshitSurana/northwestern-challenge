---
name: trace
description: >
  Follows the money behind a revolving-door case. Given a lobbyist, their client
  list, and the federal agency they target, this traces the federal awards each
  client received from that agency on USAspending.gov, verifies every row against
  the recipient's real name, and produces a journalism-ready markdown table plus a
  framing note that separates discretionary grants (newsworthy) from routine program
  participation (commodity purchases, food aid, formula financing). The "follow the
  money" companion to scan (revolving-door-detector). Use whenever you need to
  quantify the dollars flowing from an agency to a lobbyist's clients, or anyone
  mentions USAspending, federal grants/contracts, or putting a dollar figure on a
  conflict of interest.
license: MIT
compatibility: Requires Python 3.11+ and uv. Needs network access to api.usaspending.gov. Does not require the DuckDB.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.1.0"
  part-of: fair-guard
  companion-to: revolving-door-detector
  tools: bash, python, file-read, file-write
---

# federal-award-tracer

## What this skill does

`scan` (revolving-door-detector) finds the *structure* — a former official whose
firm concentrates its lobbying on the agency they used to run. This skill answers the
follow-up every editor asks: **how much money is actually moving?**

Given a lobbyist, their lobbying clients, and a target federal agency, it queries
USAspending.gov for the awards each client received from that agency, then emits:

1. A **per-client table** of recipient-name-verified award totals, sorted high to low.
2. A **framing note** that splits the total into *discretionary* dollars
   (competitively-awarded grants — the newsworthy core) versus *routine* program
   participation (commodity purchases, food aid, formula financing — context).

## Why a dedicated skill (the three gotchas)

The USAspending API (`POST /api/v2/search/spending_by_award/`) has three traps that a
fresh agent hits every time; all three are handled inside the script:

1. **One award-type group per request.** `award_type_codes` must come from a single
   group — mixing grants (`02–05`) with loans (`07–08`) returns **HTTP 422**. The
   script queries each group separately and combines.
2. **Loans can't sort by amount.** Sorting loan awards by "Award Amount" returns
   **HTTP 400**. Loans are sorted by recipient name and **excluded by default** so
   totals stay conservative.
3. **`recipient_search_text` is fuzzy.** Searching "Cargill" also returns
   "Paseo Cargill Energy". Every row is filtered against caller-supplied **name
   tokens** that must appear in the real `Recipient Name`. Cast a **wide net first**
   — search the shortest distinctive core term (`Group14`, not the full legal name),
   read every recipient name that comes back, then set tokens to keep same-company
   project SPVs (e.g. `GROUP14 BAM-2, INC.`) while excluding coincidental collisions.
   A too-narrow token silently undercounts a client's biggest awards.

## Inputs

A **case file** (JSON). Run `uv run scripts/04_award_tracer.py --print-template` for
the schema.

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

**Network required** — live HTTPS to `api.usaspending.gov`. Does *not* touch
`output/investigation.duckdb`.

## Invocation

```bash
uv run scripts/04_award_tracer.py --print-template
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json
uv run scripts/04_award_tracer.py \
  --case skill/federal-award-tracer/cases/limbaugh_interior.json \
  --out notes/limbaugh_money_trail.md --json output/limbaugh_awards.json
```

## Reproducible reference cases

| Case file | Trail | Verified total |
|-----------|-------|---------------:|
| `cases/steinberg_doe.json` | Steinberg battery/minerals clients → DOE grants | $1,080,820,046 |
| `cases/limbaugh_interior.json` | Limbaugh water-district clients → Interior grants | ≈ $136M grants-only |
| `cases/usda_cases.json` | USDA clients → grants + direct + contracts | $1,398,877,777 (~97% routine) |

## Interpreting results responsibly

Frame every figure as conflict-of-interest **structure, not proven wrongdoing**:
the dollars show the agency *can* steer money to the lobbyist's clients, not that the
lobbyist caused any award. Discretionary grants are the story; routine program
participation is context. Confirm cooling-off status (18 USC §207) and seek comment
before any causal claim.

The full skill documentation, the name-token guidance, and the data limitations live
in the canonical artifact at `skill/federal-award-tracer/SKILL.md`.
