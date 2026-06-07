---
name: coi
description: >
  Builds the conflict-of-interest graph that composes every other FairGuard
  skill's output into one investigable network. Joins scan (lobbyist → firm →
  agency), trace (agency → client money flows), and pressrel (legislator →
  client mentions) into a single graph and surfaces three story shapes:
  triangles (a member publicly mentions a client whose lobbyist used to staff
  that client's funding agency — the headline structural finding), hubs
  (clients receiving both agency dollars and legislator attention), and bridges
  (clients shared by two or more independent revolving-door cases). Emits the
  graph as JSON for the Reporter UI's /graph route, a static SVG for the report
  PDF, a Graphviz DOT, and a markdown summary. Use whenever you want to see
  cross-source connections rather than read three separate reports.
license: MIT
compatibility: Requires Python 3.11+, uv, and networkx (in default deps). Reads web/public/findings.json — no DB or network access needed.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  part-of: fair-guard
  companion-to: revolving-door-detector, federal-award-tracer, press-release-cross-ref
  tools: bash, python, file-read, file-write
---

# coi-graph

Short-name `coi`. Submission-facing full skill file at `skill/coi-graph/SKILL.md`;
this modes copy mirrors the same guidance with frontmatter cleaned up for
agentskills.io.

## What this skill does

`scan`, `trace`, and `pressrel` each produce a list. This skill turns the
three lists into a *graph* so the **connections across them** become visible.
It doesn't add a new data source — every input is already on disk after the
other three skills have run.

The five node types are color-coded (lobbyist=indigo, firm=slate,
agency=rose, client=emerald, legislator=amber). Five edge types: `works_at`,
`former_official_of`, `lobbies_for`, `funded_by` (weighted by USAspending
dollars), `mentions` (weighted by press-release count).

## The three structural patterns

The skill detects each programmatically and tops the markdown output with them:

1. **Triangles** — `(legislator, client, agency)` cycles where the
   legislator's press release praises a client whose lobbyist used to staff
   that client's funding agency. The headline structural finding.
2. **Hubs** — clients connected to both agency dollars AND legislator
   mentions. Score = `log10(dollars + 1) × mentions`.
3. **Bridges** — clients connected to two or more lobbyists in the top-N
   scan. Focal points of the revolving-door ecosystem.

## CLI surface

```bash
uv run scripts/06_coi_graph.py                # all outputs, top 10
uv run scripts/06_coi_graph.py --top 5        # narrower
uv run scripts/06_coi_graph.py --finding-rank 1   # single-finding subgraph
uv run scripts/06_coi_graph.py --out notes/coi.md
uv run scripts/06_coi_graph.py --no-web --no-svg  # CI mode
```

## Outputs

| Destination | Content |
|-------------|---------|
| stdout / `--out FILE` | Markdown summary with triangles, hubs, bridges |
| `web/public/coi_graph.json` | d3-force JSON (nodes + links arrays) for `/graph` |
| `output/coi_graph.svg` | Static SVG (pure-Python, no Graphviz dependency) |
| `output/coi_graph.dot` | Graphviz DOT for power users |

## Why client-name canonicalization matters

Without it, scan's `AMSTED INDUSTRIES`, pressrel's `Amsted Industries`, and
trace's `Cargill (operating entities)` would each be different nodes and no
triangles would form. `canonical_client()` strips corporate suffixes,
parenthetical qualifiers, and ampersands, then keeps the first three
meaningful tokens uppercased. Conservative — no industry-noun stripping —
to avoid merging genuinely distinct companies.

## Reproducibility

`spring_layout(seed=42)` — re-running on identical input produces
byte-identical SVG and identical JSON node positions.

## Editorial discipline

A triangle is a lead, not a story. Before publishing: confirm the
legislator's committee jurisdiction covers the agency, check the §207
cooling-off status of the lobbyist (`notes/09`), and document a real
request for comment (`notes/comment_requests/`).
