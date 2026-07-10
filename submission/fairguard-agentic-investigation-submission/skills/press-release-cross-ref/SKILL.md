---
name: press-release-cross-ref
description: >
  Cross-references Congressional press releases against lobbying-clients findings.
  Given a client name, a firm, or a topical phrase, this searches 141K+ House and
  Senate press releases (2022–2026) for verified mentions and returns a journalism-
  ready table of date · member (party-state-chamber) · title · URL · matched snippet,
  plus per-client tallies and a framing note. The press-release half of the FairGuard
  corpus — pairs with revolving-door-detector (scan) and federal-award-tracer (trace)
  to turn a structural pattern into a story with named legislators in it. Use this
  skill any time a reporter wants to know which members of Congress have publicly
  mentioned a company, advocated for a project, or named an industry term tied to a
  lobbying client, and especially when investigating whether a member who praised
  an entity sits on the committee whose former staff now lobby for that entity.
license: MIT
compatibility: Requires Python 3.11+, uv, and duckdb. Run the lda-corpus-indexer skill first (reads output/investigation.duckdb).
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# press-release-cross-ref

## What this skill does

`scan` finds *who* the former agency officials lobbying their old agency are.
`trace` follows the *money* from that agency to their clients. This skill closes
the loop on the third side of the triangle: which **members of Congress** have
been publicly speaking about, advocating for, or otherwise aligning themselves
with those same clients.

Given one or more client / firm / topical names, it queries the
`press_releases` table in `output/investigation.duckdb` (141,332 House and
Senate press releases, 2022–Q1 2026) for verified mentions and emits:

1. A **per-client tally** — mentions, distinct members, first and last date.
2. A **matches table** — date, member (party · state · chamber), title, URL,
   and a snippet showing the matched phrase in context.
3. A **framing note** explaining what the matches mean and what they don't.
4. *(Optional, default-on)* Web writes that attach the result to the scan
   finding card in the Reporter UI and append the report to a global
   `web/public/press_releases.json` feed for a `/pressrel` route.

The journalistic point: when a member's press release praises a project or a
company, and that same company is being lobbied by a former staffer of that
member's committee — or has just received a discretionary grant from the agency
that staffer used to run — the alignment is *the lead*. This skill puts the
press release next to the lobbying record so a reporter can see the chain in
one place.

## Why a dedicated skill (and why DuckDB)

A bare `grep` over 141K free-text press releases will work for one query, but
gets two things wrong that this skill gets right:

1. **Word-boundary discipline.** "Cargill" should not false-match
   "Cargilltechnologies." The skill builds case-insensitive regex with `\b`
   boundaries around every alias.
2. **De-duplication.** The corpus contains re-issued releases and cross-posts
   under the same `(bioguide_id, date, title)` key. The skill de-dups on that
   tuple so a tally of 23 mentions actually means 23 distinct releases.

It also adds the things you'd need to script anyway:

- **Smart-quote tolerance.** "O'Lakes" matches "O'Lakes" too (curly
  apostrophe is rampant in the corpus).
- **Snippet extraction.** 120 chars on either side of the first match,
  whitespace collapsed, matched phrase wrapped in `**bold**` so reporters can
  triage on sight.
- **Member-side filters.** Party, state, chamber, member-domain substring —
  the levers you'd use to ask "did *Energy Committee* members talk about this?"
  by domain pattern.
- **Two integration points** so results don't die in a terminal: a global
  feed for the new `/pressrel` UI route, and inline embedding on matching
  scan-finding rows.

## Inputs

### Ad-hoc search (one term, CLI flags)

```bash
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --mention "critical minerals"
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --mention "Cargill" \
    --party Democrat --chamber Senate --since 2023-01-01
```

### Case file (multiple clients, persistable)

Recommended for any non-trivial query. Mirrors the `trace` skill's case-file
pattern so the same project layout supports both:

```json
{
  "case_id": "steinberg_clients",
  "label": "Steinberg DOE clients — press-release cross-ref",
  "clients": [
    {"name": "Talon Nickel", "aliases": ["Talon Nickel", "Talon Metals"]},
    {"name": "Wabtec",        "aliases": ["Wabtec"]}
  ],
  "filters": {
    "since": "2022-01-01", "until": "2026-04-01",
    "party": null, "state": null, "chamber": null, "domain_contains": null
  },
  "match": [
    {"lobbyist_name": "Benjamin Steinberg", "agency_short": "energy"}
  ]
}
```

Run with:

```bash
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --case skills/press-release-cross-ref/cases/steinberg_clients.json
```

Schema:

| Key | Meaning |
|-----|---------|
| `case_id` | Stable id; used as the upsert key in `web/public/press_releases.json`. |
| `label` | Human-readable title shown in the report header. |
| `clients[].name` | Display name in the per-client tally. |
| `clients[].aliases` | List of phrases tried; each is word-bounded and case-insensitive. Defaults to `[name]`. |
| `filters.since` / `.until` | Inclusive date window. Defaults: 2022-01-01 / 2026-04-01. |
| `filters.party` | `Republican`, `Democrat`, `Independent`. |
| `filters.state` | Postal code (e.g. `CA`). |
| `filters.chamber` | `House` or `Senate`. |
| `filters.domain_contains` | Substring against member's official domain (`.house.gov`, `.senate.gov`, `energy.senate.gov`). |
| `match` (optional) | List of `{lobbyist_name, agency_short}` pairs. When present, the report is embedded into matching `findings.json` rows so a Money/Press-release panel appears inline on the candidate's card on `/`. Case-insensitive on `lobbyist_name`. |

Print the schema:

```bash
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --print-template
```

### Auto-enrich every scan finding

For a one-shot pass that attaches press-release evidence to every top-40 scan
finding using its `top_clients_str` as the alias list:

```bash
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --enrich-findings
```

One batched regex scan handles all findings together, so total runtime is
~constant in the number of findings (≈10s on a warm DB).

## Outputs

| Destination | Content |
|-------------|---------|
| stdout (or `--out FILE`) | Markdown — per-client tally + matches table + framing note. |
| `--json FILE` (optional) | Raw JSON payload (matches and tallies). |
| `web/public/press_releases.json` | Upserted on every run (keyed by `case_id`). Drives the `/pressrel` route. |
| `web/public/findings.json` | If the case file has a `match` block, the matching scan-finding row(s) gain a `press_releases` field — a per-client grouped slice for inline rendering. |

Pass `--no-web` to skip both web writes (useful in CI or for one-off
exploratory queries).

## Invocation examples

```bash
# 1. Ad-hoc: "which members talked about Cargill in 2024?"
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --mention "Cargill" --since 2024-01-01 \
    --out notes/pressrel_cargill_2024.md

# 2. Case file: Steinberg's DOE clients across all members
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py \
    --case skills/press-release-cross-ref/cases/steinberg_clients.json \
    --out notes/pressrel_steinberg.md \
    --json output/pressrel_steinberg.json

# 3. Case file with filter override: Senate Democrats only
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py \
    --case skills/press-release-cross-ref/cases/limbaugh_clients.json \
    --party Democrat --chamber Senate

# 4. Auto-enrich every scan finding card with press-release evidence
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --enrich-findings

# 5. Show the case-file schema
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --print-template
```

## What a match means (and what it doesn't)

A verified mention is **not** an accusation — it's an alignment signal. Members
of Congress name companies for many legitimate reasons: praising a constituent
employer, listing hearing witnesses, citing a Supreme Court case caption, or
adding a co-signer to a coalition letter. The snippet column exists precisely
so a reporter can tell which one is going on at a glance.

The story is in the *intersection*: a member who **(a)** praises a company in a
press release, **(b)** sits on a committee whose jurisdiction covers that
company's federal interests, **(c)** has a current or former staffer now
registered to lobby for that company, and ideally **(d)** issued the praise
near a specific grant award or rulemaking. The skill surfaces (a); `scan` and
`trace` give you the rest of the chain. Cross-check before publishing a causal
claim, and always seek comment (`notes/comment_requests/`).

## Known limitations

- **Substring vs. context.** The skill enforces word boundaries but not
  semantic context. "Cargill" matches both Cargill the company and `Garland v.
  Cargill` (the bump-stock Supreme Court plaintiff). The snippet shows which
  is which; the per-client tally counts both.
- **Encoding noise.** Some press releases in the corpus have cp1252 artefacts
  (replacement characters where the original text had smart quotes or em
  dashes). Snippets preserve the original text as-is.
- **No semantic / embedding search yet.** v1.0 is regex over text. v1.1 will
  add a FTS5 index and an optional embeddings layer for phrase-similarity
  queries ("net-zero ambitions" ≈ "carbon-reduction commitments").

## Reproducibility

Two bundled case files reproduce against the committed DuckDB:

- `skills/press-release-cross-ref/cases/steinberg_clients.json` — 9 clients,
  ~59 verified matches across ~37 members (numbers depend on which version of
  the corpus is loaded; the structure is stable).
- `skills/press-release-cross-ref/cases/limbaugh_clients.json` — 8 clients,
  high-volume on `Bureau of Reclamation` as the thematic anchor.

Both case files have `match` blocks so re-running them refreshes the
press-release panel on the Steinberg / Limbaugh cards in the Reporter UI.

## When NOT to use this skill

- If the question is "how much money did X get from agency Y" — that's
  `trace` (federal-award-tracer), not this. Press releases announce; they
  don't measure.
- If the question is "who's a former agency official lobbying their old
  agency" — that's `scan`. Press releases tell you which members noticed the
  resulting work, not which lobbyists did it.
- For Senate floor speeches, hearings, or bill text — those aren't in the
  press-release corpus. (FairGuard's corpus is `congress_press/` only.)
