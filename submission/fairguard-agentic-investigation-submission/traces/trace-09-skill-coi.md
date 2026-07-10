# Trace — `/fair-guard coi`

**Date:** 2026-06-07
**Skill invoked:** `coi` (coi-graph v1.0.0)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** 174 nodes, 198 edges, **11 structural triangles, 20 hubs, 5 bridges** composed from the top-10 scan findings, their embedded trails, and their embedded press-release matches.

---

## Invocation

```bash
uv run scripts/06_coi_graph.py
```

The dispatcher checked the prerequisite (`web/public/findings.json` exists — coi reads only on-disk JSON, no DB or network needed) and routed to `skill/coi-graph/SKILL.md`. The script loaded `findings.json`, defaulted to the top 10 findings (`--top 10`), and built the graph.

## What the script did

1. **Built a NetworkX graph** from each finding row. Five node types (lobbyist, firm, agency, client, legislator) and five typed edges (works_at, former_official_of, lobbies_for, funded_by, mentions). Edges carry typed weights so the same `(legislator, client)` pair across two press releases collapses to a single edge with `weight=2`.
2. **Canonicalized client names** via `canonical_client()` so scan's `AMSTED INDUSTRIES`, pressrel's `Amsted Industries`, and trace's `Cargill (operating entities)` all collapsed onto the same `client:CARGILL` node. Without this, the triangles never form (every client appears with two slightly different spellings under different sources).
3. **Detected structural patterns:**
   - **Triangles**: `(legislator, client, agency)` cycles where the legislator's press release praises a client whose lobbyist used to staff that client's funding agency.
   - **Hubs**: clients connected to both agency dollars and legislator mentions; score = `log10(dollars+1) × mentions`.
   - **Bridges**: clients shared by ≥2 lobbyists in the top-10 scan.
4. **Rendered four outputs:**
   - `web/public/coi_graph.json` — d3-force shape for the `/graph` route.
   - `output/coi_graph.svg` — pure-Python static SVG (no Graphviz dependency).
   - `output/coi_graph.dot` — Graphviz DOT source for users who want to compile their own layouts.
   - Markdown summary to stdout.

## Output (verbatim, abbreviated)

```
loaded 10 finding(s) from web/public/findings.json
graph: 174 nodes, 198 edges; 11 triangle(s), 20 hub(s), 5 bridge(s)
wrote web/public/coi_graph.json (n_nodes=174)
wrote output/coi_graph.svg
wrote output/coi_graph.dot

## Conflict-of-interest graph

Composed from 10 lobbyists, 9 firms, 5 agencies, 67 clients, 83 legislators —
**174** nodes, **198** edges.

### Structural triangles (member · client · agency)

| Legislator                      | Client                          | Agency  | Lobbyist(s)        | Mentions | Agency $ to client |
|---------------------------------|---------------------------------|---------|--------------------|---------:|-------------------:|
| Cindy Hyde-Smith (R-MS-S)       | Cargill                         | USDA    | ASHLEE JOHNSON     |        1 | $704,852,208       |
| Adrian Smith (R-NE-H)           | Cargill                         | USDA    | ASHLEE JOHNSON     |        1 | $704,852,208       |
| Tammy Duckworth (D-IL-S)        | Cargill                         | USDA    | ASHLEE JOHNSON     |        1 | $704,852,208       |
| Richard J. Durbin (D-IL-S)      | Cargill                         | USDA    | ASHLEE JOHNSON     |        1 | $704,852,208       |
| Jerry Moran (R-KS-S)            | Cargill                         | USDA    | ASHLEE JOHNSON     |        1 | $704,852,208       |
| Kevin Cramer (R-ND-S)           | TALON NICKEL (USA) LLC          | ENERGY  | BENJAMIN STEINBERG |        1 | $114,846,344       |
| ...                             | ...                             | ...     | ...                |      ... | ...                |

### Hubs (client × agency $ × legislator mentions) — top
| Cargill           | USDA      | $704.9M | 5 | 44.27 |
| Talon Nickel      | ENERGY    | $114.8M | 4 | 32.25 |
| Wabtec            | (none)    | —       | 5 |  —    |
| ...

### Bridges (clients shared by ≥2 lobbyists in scope)
| DIGITAL CHAMBER OF COMMERCE          | 2 | SCOTT PARSONS, JIM NEWSOME |
| CITADEL INVESTMENT GROUP             | 2 | SCOTT PARSONS, JIM NEWSOME |
| AMERICAN COTTON SHIPPERS ASSOCIATION | 2 | SCOTT PARSONS, JIM NEWSOME |
| FIA / PTG                            | 2 | SCOTT PARSONS, JIM NEWSOME |
| COMMODITY MARKETS COUNCIL            | 2 | SCOTT PARSONS, JIM NEWSOME |
```

## The story shapes in plain English

**The bipartisan Cargill cluster.** Five U.S. senators across both parties — Hyde-Smith (R-MS), Adrian Smith (R-NE), Duckworth (D-IL), Durbin (D-IL), Moran (R-KS) — publicly mentioned Cargill in press releases during 2022–2026. The same Cargill received ~$705M from USDA. The lobbyist registered to represent Cargill at USDA is Ashlee Johnson, a former senior USDA official now at The Russell Group. That's a five-row triangle the graph collapses onto a single Cargill node.

**The CFTC futures-industry bridge.** Both Jim Newsome (former CFTC Chairman) and Scott Parsons (former senior CFTC) work at Delta Strategy Group, and the five "bridge" clients above — Digital Chamber of Commerce, Citadel, American Cotton Shippers, FIA/PTG, Commodity Markets Council — are represented by both. The graph surfaces this as a 2-lobbyist convergence on each shared client; the story is the dual-coverage of a regulated industry by two former regulators at the same firm.

**The Talon Nickel critical-minerals triangle.** Sen. Kevin Cramer (R-ND) praises Talon Nickel; DOE has paid Talon ~$115M in discretionary battery-supply-chain grants; Benjamin Steinberg, who used to run DOE's EPSA, is the registered lobbyist. The single-mention version is a clean structural triangle; the broader "critical minerals" thematic cluster has 25+ legislator mentions across 20 members.

## The judgment that mattered

The graph would have surfaced **zero** triangles without `canonical_client()`. The first run produced 0 triangles because scan's `AMSTED INDUSTRIES`, pressrel's `Amsted Industries`, and trace's `Cargill (operating entities)` are three distinct strings and ended up as three distinct nodes. The canonical form strips corporate suffixes and parenthetical qualifiers, collapsing them to `AMSTED INDUSTRIES` / `AMSTED INDUSTRIES` / `CARGILL` respectively — same node, edges merge, triangles form. This is the load-bearing piece of the skill and is locked down by `TestCanonicalClient` in `tests/test_coi_graph.py`.

## Reproducibility

The layout is seeded (`spring_layout(seed=42)`), so re-running on identical input produces byte-identical SVG and identical JSON node positions. The 26 tests in `tests/test_coi_graph.py` pin canonicalization, build correctness, all three pattern detectors (triangles / hubs / bridges), output renderers (JSON / SVG / DOT / markdown), and the determinism property itself.

```bash
# Full reproduction pipeline (presupposes scan, trace, pressrel have been run):
uv run scripts/06_coi_graph.py
```

The script reads only on-disk JSON, so it's safe to run offline and is idempotent.
