---
name: coi-graph
description: >
  Builds the conflict-of-interest graph that composes every other FairGuard
  skill's output into one investigable network. Joins scan (lobbyist → firm →
  agency), trace (agency → client money flows), and pressrel (legislator →
  client mentions) into a single graph and surfaces three story shapes a
  reporter looks for: triangles (a member publicly mentions a client whose
  lobbyist used to staff that client's funding agency — the headline structural
  finding), hubs (clients receiving both agency dollars and legislator
  attention), and bridges (clients shared by two or more independent
  revolving-door cases). Emits the graph as JSON adjacency for the Reporter
  UI's /graph route, a static SVG for the findings PDF, a Graphviz DOT, and a
  markdown summary of the most newsworthy triangles, hubs, and bridges. Use
  whenever you want to see cross-source connections rather than read three
  separate reports.
license: MIT
metadata:
  version: "1.0.0"
  author: FairGuard (Mokshit Surana, Archit Rathod)
  tools: [bash, python, file-read, file-write]
  requires_python: ">=3.11"
---

# coi-graph

## What this skill does

`scan`, `trace`, and `pressrel` each produce a list. This skill turns the
three lists into a *graph* so the **connections across them** become visible.
It doesn't add a new data source — every input is already on disk after
running the other three skills (`web/public/findings.json` carries the scan
output plus the embedded `trail` and `press_releases` blocks).

The graph has five node types, color-coded for visual scanning:

| Type | Color (indigo/rose/emerald palette) | Comes from |
|------|------|------|
| `lobbyist` | indigo | scan — the former agency official |
| `firm` | slate | scan — their lobbying firm |
| `agency` | rose | scan — the former employer (also the grant authority) |
| `client` | emerald | scan + trace + pressrel — the company being represented |
| `legislator` | amber | pressrel — the member of Congress publicly mentioning the client |

And five typed edges:

| Edge | What it means |
|------|---------------|
| `works_at` | lobbyist → firm — current employment |
| `former_official_of` | lobbyist → agency — the revolving-door edge |
| `lobbies_for` | lobbyist → client — LDA filing relationship |
| `funded_by` | agency → client — USAspending award (weight = dollars) |
| `mentions` | legislator → client — press release (weight = number of mentions) |

## The three structural patterns it surfaces

These are what a working reporter would look for in this graph. The skill
detects each one programmatically and tops the markdown summary with them.

1. **Triangles** — `(legislator, client, agency)` cycles where the
   legislator's press release praises a client whose lobbyist used to staff
   that client's funding agency. This is the headline structural finding.
   Order: number of mentions (high → low), then dollars.

2. **Hubs** — clients connected to both agency dollars (`funded_by`) AND
   legislator mentions. Score = `log10(dollars + 1) × mentions`. The
   highest-score hubs are where money meets messaging in the public record.

3. **Bridges** — clients connected to two or more lobbyists in the top-N
   scan. Says "this client is a focal point of the revolving-door
   ecosystem." (Both Newsome and Parsons at Delta Strategy Group, for
   instance, lobby for the same five futures-industry trade groups — every
   one is a bridge.)

## Why client-name canonicalization matters

scan emits client names in their raw LDA form (`AMSTED INDUSTRIES`,
`TALON NICKEL (USA) LLC`). pressrel matches against shorter forms
(`Anovion`, `Talon Nickel`). trace uses case-file labels (`Cargill
(operating entities)`). Without normalization, the same company shows up as
three different nodes and the triangles disappear.

`canonical_client()` strips corporate suffixes (LLC, INC, CORP, COMPANY,
ASSOCIATION, etc.), parenthetical qualifiers, and ampersands, then keeps the
first three meaningful tokens uppercased. So:

- `AMSTED INDUSTRIES` → `AMSTED INDUSTRIES`
- `Amsted Industries` → `AMSTED INDUSTRIES`
- `TALON NICKEL (USA) LLC` → `TALON NICKEL`
- `Talon Nickel` → `TALON NICKEL`
- `Cargill (operating entities)` → `CARGILL`
- `CARGILL INC` → `CARGILL`

All collapse onto the same `client:CARGILL` node. The canonicalization is
deliberately conservative (no industry-noun stripping like `ENERGY` or
`WATER`) to avoid merging genuinely distinct companies. The tradeoff is
that some near-misses still won't merge — e.g., `Burns & McDonnell` vs
`Burns & McDonnell Engineering Company Inc` collapse to `BURNS MCDONNELL`
and `BURNS MCDONNELL ENGINEERING` respectively, which is acceptable
because the third token preserves a real distinction.

## Inputs

```bash
# All outputs, top-10 scan findings (default)
uv run skills/coi-graph/scripts/06_coi_graph.py

# Narrower scope
uv run skills/coi-graph/scripts/06_coi_graph.py --top 5

# A single finding's subgraph (rank N from findings.json)
uv run skills/coi-graph/scripts/06_coi_graph.py --finding-rank 1

# Persist outputs
uv run skills/coi-graph/scripts/06_coi_graph.py --out notes/coi_summary.md

# CI / offline mode
uv run skills/coi-graph/scripts/06_coi_graph.py --no-web --no-svg
```

## Outputs (four parallel forms)

| Destination | Content | Consumer |
|-------------|---------|----------|
| stdout (or `--out FILE`) | Markdown — triangles + hubs + bridges + how-to-read | Reporter at the terminal; findings report PDF |
| `web/public/coi_graph.json` | d3-force shape (nodes + links arrays) with typed metadata | Reporter UI `/graph` route (interactive D3 force-directed graph) |
| `output/coi_graph.svg` | Static SVG, pure-Python rendered (no Graphviz dep) | Findings report PDF, screenshots, print |
| `output/coi_graph.dot` | Graphviz DOT source | Power users compiling their own layouts (`dot -Tpng coi.dot > coi.png`) |

Pass `--no-web` to skip the JSON, `--no-svg` to skip the SVG and DOT.

## Reading the markdown output

```
## Conflict-of-interest graph

Composed from 10 lobbyists, 9 firms, 5 agencies, 61 clients, 42 legislators —
**127** nodes, **140** edges.

### Structural triangles (member · client · agency)

| Legislator | Client | Agency | Lobbyist(s) | Mentions | Agency $ to client |
|---|---|---|---|---:|---:|
| Cindy Hyde-Smith (R-MS-S) | Cargill | USDA | ASHLEE JOHNSON | 1 | $704,852,208 |
| Adrian Smith (R-NE-H) | Cargill | USDA | ASHLEE JOHNSON | 1 | $704,852,208 |
...
```

Each triangle row is one publishable lead — *after* (a) confirming the
member's committee jurisdiction covers the agency, (b) checking the §207
cooling-off status of the lobbyist (`notes/09`), and (c) documenting a
real request for comment (`notes/comment_requests/`).

## Reproducibility

The layout is seeded (`spring_layout(seed=42)`), so re-running on the same
input data produces byte-identical SVG and identical JSON node positions.
That's important for the `git status` diff — a deterministic graph means
the only changes are real data changes, not jitter.

To reproduce the shipped artifacts end-to-end:

```bash
uv run skills/revolving-door-detector/scripts/03_agency_concentration.py            # scan
uv run skills/federal-award-tracer/scripts/04_award_tracer.py --case skills/federal-award-tracer/cases/steinberg_doe.json
uv run skills/federal-award-tracer/scripts/04_award_tracer.py --case skills/federal-award-tracer/cases/limbaugh_interior.json
uv run skills/federal-award-tracer/scripts/04_award_tracer.py --case skills/federal-award-tracer/cases/usda_cases.json
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --enrich-findings
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --case skills/press-release-cross-ref/cases/steinberg_clients.json
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --case skills/press-release-cross-ref/cases/limbaugh_clients.json
uv run skills/press-release-cross-ref/scripts/05_pressrel_search.py --case skills/press-release-cross-ref/cases/usda_clients.json
uv run skills/coi-graph/scripts/06_coi_graph.py
```

## When NOT to use this skill

- If you want raw numbers — use `trace` (dollars) or `pressrel` (mentions)
  directly. The graph is for *connections*, not aggregates.
- If you're investigating a single candidate — use `--finding-rank N` to
  get just that candidate's subgraph rather than the full top-N.
- If you need real-time updates — the graph is generated from on-disk JSON,
  not the live DB. Re-run the script after each scan/trace/pressrel refresh.

## Editorial discipline

A triangle is not a story; it's a lead. Before publishing:

- **Committee jurisdiction.** Does the legislator actually sit on a
  committee with oversight of the agency? If yes, the alignment is much
  sharper. The skill doesn't have committee data — that's a manual check.
- **Timing.** When is the press release dated relative to the grant award?
  Mentions years apart are weaker than mentions in the same quarter as a
  funding announcement.
- **§207 cooling-off.** Has the lobbyist's timed §207 ban expired? See
  `notes/09_reportability_gates_207_and_comment.md`.
- **Request for comment.** Has the firm been given a real opportunity to
  respond? See `notes/comment_requests/`.

The graph surfaces structure. The story is built from the structure.
