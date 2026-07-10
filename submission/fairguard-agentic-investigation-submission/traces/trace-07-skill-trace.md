# Trace — `/fair-guard trace`

**Date:** 2026-06-06
**Skill invoked:** `trace` (federal-award-tracer v1.1.0)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** $1,398,877,777 in USDA grants/direct/contracts verified across 12 USDA-revolving-door clients; trail upserted into `web/public/trails.json`; matching scan-finding rows in `web/public/findings.json` enriched with the inline Money trail panel.

---

## Invocation

User typed `/fair-guard trace` in Claude Code with no case-file argument.

The dispatcher (`.claude/skills/fair-guard/SKILL.md`) recognized that:

1. `trace` is the only mode that does **not** require `output/investigation.duckdb` — it makes live HTTPS calls to api.usaspending.gov. The DuckDB prerequisite check is skipped for this mode.
2. No `--case` argument was supplied. Rather than fail, the dispatcher routed to `skill/federal-award-tracer/SKILL.md` and presented the three bundled case files plus a `--print-template` invocation for authoring new ones.

User followed up: `run the usda cases`.

Dispatcher executed:

```bash
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/usda_cases.json
```

## What the script did

The case file (`skill/federal-award-tracer/cases/usda_cases.json`) declares:

- `agency`: "Department of Agriculture"
- `award_groups`: `["grants", "direct", "contracts"]`
- `time_period`: 2021-01-01 → 2026-06-04
- `match`: four scan-finding keys — Ashlee Johnson, Kevin Bailey, Michael Torrey, Kenneth Barbic (all USDA)
- `clients`: 12 entries, each with a `search` term and `name_tokens` for verification

For each client, the script:

1. POSTs to `https://api.usaspending.gov/api/v2/search/spending_by_award/` **once per award group** (the API rejects mixed-group requests with HTTP 422).
2. Filters results — keeps a row only if `Recipient Name` (uppercased) contains one of the client's `name_tokens`. This guards against the API's fuzzy `recipient_search_text` (`"Cargill"` also returns `"Paseo Cargill Energy"`).
3. De-dupes by `Award ID`.
4. Tags each row as **routine** (sub-agency matches one of AMS / FAS / FSA / CCC / RUS / RHS / FNS) or **discretionary**.
5. Sleeps 250ms between calls (politeness).

## Output (verbatim, abbreviated)

```
## Money trail: USDA cases (Johnson / Bailey / Torrey / Barbic clients) → Department of Agriculture

Federal grants, direct, contracts awarded by Department of Agriculture to USDA cases
(Johnson / Bailey / Torrey / Barbic clients)'s lobbying clients, verified by recipient name
against USAspending.gov. Loans are excluded (conservative).

| Client                          | Verified total | Awards | Recipient name(s) on file       |
|---------------------------------|---------------:|-------:|---------------------------------|
| Cargill (operating entities)    |   $704,948,114 |    298 | CARGILL, INCORPORATED; …        |
| National Rural Water Assn       |   $272,037,205 |     14 | NATIONAL RURAL WATER ASSOCIATION |
| Tri-State Generation            |   $148,254,491 |      6 | TRI-STATE GENERATION AND…       |
| Land O'Lakes (Venture37)        |   $104,549,762 |     19 | LAND O'LAKES VENTURE37 INC      |
| McCain Foods USA                |    $82,604,316 |     11 | MCCAIN FOODS USA INC            |
| Global Clean Energy             |    $32,260,500 |      1 | GLOBAL CLEAN ENERGY HOLDINGS …  |
| Louis Dreyfus                   |    $21,795,624 |     13 | LOUIS DREYFUS COMPANY LLC       |
| Ardent Mills                    |    $16,933,341 |      7 | ARDENT MILLS LLC                |
| California Prune Board          |     $9,201,775 |      8 | CALIFORNIA DRIED PLUM BOARD     |
| Shenandoah Valley Organic       |     $3,648,649 |      1 | SHENANDOAH VALLEY ORGANIC LLC   |
| Illinois Soybean Board          |     $1,891,488 |      6 | ILLINOIS SOYBEAN ASSOCIATION    |
| California Rice Commission      |       $752,512 |      3 | CALIFORNIA RICE COMMISSION      |
| **TOTAL**                       | **$1,398,877,777** |   |                                  |

### Framing

Of the $1,398,877,777 traced, $38,036,488 (about 3%) flows through programs that are
not obviously routine, while $1,360,841,289 flows through sub-agencies that typically
administer formula / commodity / financing programs (e.g. AMS commodity purchases, FAS
food aid, RUS financing).

Report this as conflict-of-interest *structure*, not proven wrongdoing. Discretionary,
competitively-awarded grants from the former official's agency to that official's
clients are the newsworthy core; routine program participation is context. Confirm
each award's program type, the cooling-off status (18 USC §207), and seek comment
before publishing a causal claim.

<details><summary>Routine-program signals detected</summary>
- Cargill (operating entities): $704,948,114 via Agricultural Marketing Service
- National Rural Water Assn: $272,037,205 via Rural Utilities Service
- Tri-State Generation: $148,254,491 via Rural Utilities Service
- Land O'Lakes (Venture37): $104,549,762 via Foreign Agricultural Service
- McCain Foods USA: $82,604,316 via Agricultural Marketing Service
…
</details>

wrote web\public\trails.json (3 trail(s))
embedded trail in 4 finding row(s) of web\public\findings.json
```

## What the agent did with the result

After the script returned, the agent:

1. Summarized the table back to the user, calling out the **97% routine / 3% discretionary** split as the editorially important framing.
2. Singled out **Global Clean Energy's $32.3M NRCS Climate-Smart grant** as the one discretionary award worth chasing — competitively awarded, not formula.
3. Offered the `--out notes/usda_trail.md --json output/usda_awards.json` invocation to persist the result.

User followed up: `write the results`.

Dispatcher re-executed with `--out` and `--json` flags, writing:

- `notes/usda_trail.md` — journalism-ready markdown table + framing note
- `output/usda_awards.json` — raw per-client data for auditing

## The judgment that mattered

This skill's load-bearing decision is **wide-net entity discovery** (the v1.0→v1.1 fix documented in `skill/federal-award-tracer/SKILL.md`). For each client, the `search` token is the *shortest distinctive core term* (`Cargill`, not `Cargill, Incorporated`), and the script reads every returned recipient name before filtering by `name_tokens`. That's what caught Cargill's three operating entities (`CARGILL, INCORPORATED`, `CARGILL MEAT SOLUTIONS`, `CARGILL KITCHEN SOLUTIONS`) instead of just one. A too-narrow search would have undercounted the Cargill total by ~$500M with no visible warning.

The eval `evals/evals.json #4` covers this exact failure mode — it ships **without** a case file, so the agent must author one from scratch and must apply the wide-net discipline to reproduce the recorded total.

## Web integration

This run wrote two things into the Reporter UI:

1. **`web/public/trails.json`** — upserted by `case_id` (so re-running the same case overwrites in place rather than accumulating duplicates). Drives the `/trails` route.
2. **`web/public/findings.json`** — the four matching scan-finding rows (Johnson / Bailey / Torrey / Barbic at USDA) gained a `trail` field, which surfaces an inline "Money trail" panel on the candidate's card on `/`.

The reporter then clicks **↻ Refresh data** in the UI (no page reload needed) and the trail appears.

## Reproducibility

Re-running the same case file against api.usaspending.gov produces the same per-client totals, modulo any USAspending data corrections between runs. The eval suite (`evals/evals.json`) records the dollar-precise totals for the Steinberg DOE ($1,080,820,046) and USDA ($1,398,877,777) cases — both reproduce exactly as of this trace's date.

```bash
# Reproduce this trace verbatim:
uv run scripts/04_award_tracer.py \
  --case skill/federal-award-tracer/cases/usda_cases.json \
  --out notes/usda_trail.md \
  --json output/usda_awards.json
```

To skip the web writes (useful in CI or offline): add `--no-web`.
