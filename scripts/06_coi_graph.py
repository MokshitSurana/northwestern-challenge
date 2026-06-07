#!/usr/bin/env python3
"""
06_coi_graph.py — Build the conflict-of-interest graph.

This is the composition skill — it doesn't add a new data source, it joins the
outputs of every other skill into one investigable graph. Inputs (all already on
disk after a fresh run of scan + trace + pressrel):

  - web/public/findings.json
      Each row has the scan output (lobbyist, firm, agency, top clients) plus
      (when populated) a `trail` block from trace and a `press_releases` block
      from pressrel. We don't re-query the database — we just structure what's
      already there.

Nodes (typed):

  - lobbyist    e.g. "Benjamin Steinberg"
  - firm        e.g. "Venn Strategies"
  - agency      e.g. "ENERGY"
  - client      e.g. "Cirba Solutions"
  - legislator  e.g. "Cory Booker (D-NJ-Senate)"

Edges (typed, directional in the data, undirected for layout):

  - lobbyist  --works_at-->          firm        (firm employment)
  - lobbyist  --former_official_of-->agency      (the revolving-door edge)
  - lobbyist  --lobbies_for-->       client      (LDA filing relationship)
  - agency    --funded_by-->         client      (USAspending; weight = $)
  - legislator-mentions-->           client      (press release; weight = N)

The story shapes that pop out:

  - **Bridges** — clients shared by two lobbyists who lobbied different
    agencies. Says "this firm/issue is the actual nexus."
  - **Triangles** — (legislator, client, agency) cycles where the legislator
    praised a client whose lobbyist used to staff that agency. Says "this
    member's praise of this company tracks the lobbying chain."
  - **Hubs** — clients receiving both discretionary dollars from an agency and
    multiple legislator mentions. Most newsworthy.

This skill emits the graph in three forms so a reporter, a print designer, and
a future skill can each consume it:

  1. JSON adjacency at web/public/coi_graph.json — for the /graph route in the
     Reporter UI (D3-force-directed, interactive).
  2. Static SVG at output/coi_graph.svg — for the findings report PDF and any
     other static rendering. Pure-Python (no Graphviz dependency).
  3. DOT source at output/coi_graph.dot — for users who want to compile with
     Graphviz themselves (dot/neato/sfdp).
  4. Markdown summary on stdout (or --out FILE) listing the bridges, triangles,
     and hubs the reporter should look at first.

Usage:
    uv run scripts/06_coi_graph.py                     # all outputs, top 10
    uv run scripts/06_coi_graph.py --top 5             # narrower
    uv run scripts/06_coi_graph.py --finding-rank 1    # one-finding subgraph
    uv run scripts/06_coi_graph.py --out notes/coi.md  # also write markdown
    uv run scripts/06_coi_graph.py --no-web            # skip web JSON
    uv run scripts/06_coi_graph.py --no-svg            # skip SVG/DOT
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parent.parent
FINDINGS_JSON = REPO_ROOT / "web" / "public" / "findings.json"
WEB_OUT = REPO_ROOT / "web" / "public" / "coi_graph.json"
SVG_OUT = REPO_ROOT / "output" / "coi_graph.svg"
DOT_OUT = REPO_ROOT / "output" / "coi_graph.dot"

# Visual scheme — shared by SVG and (via the JSON) the web UI. The colors are
# chosen to match the Reporter UI's existing palette (indigo for chrome,
# emerald for money, rose for high-concentration warning, slate for neutral).
NODE_COLORS = {
    "lobbyist":   "#4f46e5",   # indigo-600 — the central actor
    "firm":       "#0f172a",   # slate-900 — anchored, structural
    "agency":     "#dc2626",   # rose-600 — the regulator with grant authority
    "client":     "#059669",   # emerald-600 — the money recipient
    "legislator": "#d97706",   # amber-600 — the public voice
}

NODE_RADII = {
    "lobbyist": 14,
    "firm": 10,
    "agency": 16,
    "client": 8,
    "legislator": 6,
}

EDGE_STYLES = {
    "works_at":             {"color": "#94a3b8", "width": 1.5, "dash": None},
    "former_official_of":   {"color": "#dc2626", "width": 2.5, "dash": None},
    "lobbies_for":          {"color": "#4f46e5", "width": 1.2, "dash": None},
    "funded_by":            {"color": "#059669", "width": 2.0, "dash": "4 4"},
    "mentions":             {"color": "#d97706", "width": 1.2, "dash": "2 2"},
}


def _nid(node_type: str, label: str) -> str:
    """Canonical node id — type-prefixed so the same string ('Cargill') used as
    both client and agency name (it can't, but the property is enforced) never
    collides. For client nodes specifically the label is run through
    canonical_client() first so different spellings of the same company
    ('AMSTED INDUSTRIES' from scan vs. 'Amsted Industries' from a pressrel
    case file) merge into one node — this is what makes triangles form."""
    if node_type == "client":
        return f"client:{canonical_client(label)}"
    return f"{node_type}:{label.strip()}"


# Corporate-suffix and stop-words that shouldn't carry identity weight when
# matching client names across sources. We keep this list conservative — adding
# words too aggressively (e.g. "ENERGY", "WATER") risks merging genuinely
# distinct companies. The current list covers entity-form suffixes only.
_CLIENT_NOISE = {
    "LLC", "LTD", "INC", "CORP", "CORPORATION", "COMPANY", "CO",
    "GROUP", "HOLDINGS", "INTERNATIONAL", "ASSOCIATION", "ASSN",
    "COUNCIL", "PARTNERS", "PARTNERSHIP", "ENTERPRISES",
    "AND", "OF", "FOR", "THE",
}


def canonical_client(name: str) -> str:
    """Normalize a client name for cross-source matching. Returns up to 3
    meaningful tokens, uppercased, with corporate suffixes and parenthetical
    qualifiers stripped. Designed to make these all map to the same key:

        'AMSTED INDUSTRIES'                          -> 'AMSTED INDUSTRIES'
        'Amsted Industries'                          -> 'AMSTED INDUSTRIES'
        'TALON NICKEL (USA) LLC'                     -> 'TALON NICKEL'
        'Talon Nickel'                               -> 'TALON NICKEL'
        'BURNS & McDONNELL ENGINEERING COMPANY INC'  -> 'BURNS MCDONNELL ENGINEERING'
        'Burns & McDonnell'                          -> 'BURNS MCDONNELL'

    The Burns example is the limit case: identical first-two tokens, distinct
    third. We accept that as a near-match-via-prefix (downstream we prefer
    canonical-prefix matches, see _merge_aliases). Without this, the graph
    has ~0 triangles because every client appears with two slightly different
    spellings and the node-collapse never happens."""
    if not name:
        return ""
    s = re.sub(r"\([^)]*\)", " ", name).upper()
    s = s.replace("&", " ")
    s = re.sub(r"[^\w\s-]", " ", s)
    tokens = [t.strip("-.") for t in s.split() if t.strip("-.")]
    meaningful = [t for t in tokens if t.upper() not in _CLIENT_NOISE]
    out_tokens = meaningful[:3] if meaningful else tokens[:3]
    return " ".join(out_tokens).strip() or name.strip().upper()


# ── Graph build ───────────────────────────────────────────────────────────────


def build_graph(findings: list[dict]) -> nx.Graph:
    """Walk the findings rows and accumulate one undirected MultiGraph-ish view
    (NetworkX.Graph with edge attributes that include `type` and `weight`).
    Multiple parallel edges between the same node pair (e.g. legislator A
    mentions client X across 4 press releases) collapse to a single edge with
    weight=4."""
    G = nx.Graph()

    for f in findings:
        lobbyist = (f.get("lobbyist_name") or "").strip()
        firm = (f.get("registrant_name") or "").strip()
        agency_short = (f.get("agency_short") or "").strip().upper()
        if not (lobbyist and firm and agency_short):
            continue

        ln = _nid("lobbyist", lobbyist)
        fn = _nid("firm", firm)
        an = _nid("agency", agency_short)

        # Lobbyist node with its scan metadata so the UI tooltip can render it.
        G.add_node(ln, type="lobbyist", label=lobbyist,
                   rank=f.get("rank"), score=f.get("score"),
                   concentration=f.get("concentration"),
                   prior_role=(f.get("covered_position") or "")[:200])
        G.add_node(fn, type="firm", label=firm)
        G.add_node(an, type="agency", label=agency_short)

        G.add_edge(ln, fn, type="works_at", weight=1)
        G.add_edge(ln, an, type="former_official_of",
                   weight=float(f.get("concentration") or 0))

        # Clients (from scan's top_clients_str) — each gets a lobbies_for edge.
        clients = [c.strip() for c in (f.get("top_clients_str") or "").split("|") if c.strip()]
        for c in clients:
            cn = _nid("client", c)
            G.add_node(cn, type="client", label=c)
            _bump_edge(G, ln, cn, etype="lobbies_for", inc=1)

        # Money trail — agency → client edges weighted by total dollars.
        trail = f.get("trail") or {}
        for tc in trail.get("clients", []):
            client_name = (tc.get("label") or "").strip()
            if not client_name:
                continue
            cn = _nid("client", client_name)
            G.add_node(cn, type="client", label=client_name)
            # The trail label is sometimes a friendlier display name than the
            # raw scan top_clients_str spelling. Keep the lobbies_for edge if
            # the lobbyist appears in any sibling alias; otherwise the funded
            # client floats unattached to the lobbyist, which IS the right
            # signal: this is money to a client we haven't tied to a lobbying
            # filing yet.
            G.add_edge(an, cn, type="funded_by",
                       weight=float(tc.get("total") or 0),
                       discretionary=float(tc.get("discretionary_amount") or 0),
                       n_awards=int(tc.get("n_awards") or 0))

        # Press releases — legislator → client mentions.
        pr = f.get("press_releases") or {}
        for group in pr.get("by_client", []):
            client_name = (group.get("client") or "").strip()
            if not client_name:
                continue
            cn = _nid("client", client_name)
            G.add_node(cn, type="client", label=client_name)
            for match in group.get("matches", []):
                mname = (match.get("member_name") or "").strip()
                if not mname:
                    continue
                party = (match.get("party") or "")[:1] or "?"
                state = match.get("state") or "??"
                chamber = (match.get("chamber") or "")[:1] or "?"
                leg_label = f"{mname} ({party}-{state}-{chamber})"
                ln_id = _nid("legislator", leg_label)
                G.add_node(ln_id, type="legislator", label=leg_label,
                           bare_name=mname, party=match.get("party"),
                           state=state, chamber=match.get("chamber"))
                _bump_edge(G, ln_id, cn, etype="mentions", inc=1,
                           extra={"latest_title": match.get("title"),
                                  "latest_url": match.get("url"),
                                  "latest_date": match.get("date")})
    return G


def _bump_edge(G: nx.Graph, u: str, v: str, *, etype: str, inc: int,
               extra: dict | None = None) -> None:
    """Add or increment a typed edge. Edges of different types between the same
    pair don't merge — `(u, v, type=lobbies_for)` and `(u, v, type=mentions)`
    coexist as the *same* underlying edge with combined attributes. NetworkX
    Graph allows only one edge per pair, so we store a list of edge-types on
    that single edge. The web UI splits them back out for rendering."""
    if G.has_edge(u, v):
        types = G[u][v].setdefault("types", [G[u][v].get("type")] if G[u][v].get("type") else [])
        weights = G[u][v].setdefault("weights", {})
        if etype not in types:
            types.append(etype)
        weights[etype] = weights.get(etype, 0) + inc
        # Top-level weight is the sum across types; downstream code (triangle
        # detection, hub scoring) reads this rather than the typed dict.
        G[u][v]["weight"] = G[u][v].get("weight", 0) + inc
        if extra:
            G[u][v].update({k: v for k, v in extra.items() if v is not None})
    else:
        attrs = {"type": etype, "weight": inc, "types": [etype], "weights": {etype: inc}}
        if extra:
            attrs.update({k: v for k, v in extra.items() if v is not None})
        G.add_edge(u, v, **attrs)


# ── Structural patterns: bridges, triangles, hubs ─────────────────────────────


def find_shared_clients(G: nx.Graph) -> list[dict]:
    """Clients that appear in the lobbying portfolio of two or more lobbyists
    in our top-N. Says: this is a focal point of the lobbying ecosystem."""
    out = []
    for n, attrs in G.nodes(data=True):
        if attrs.get("type") != "client":
            continue
        lobbyists = [m for m in G.neighbors(n) if G.nodes[m].get("type") == "lobbyist"]
        if len(lobbyists) >= 2:
            out.append({
                "client": attrs.get("label"),
                "n_lobbyists": len(lobbyists),
                "lobbyists": [G.nodes[m].get("label") for m in lobbyists],
            })
    return sorted(out, key=lambda r: r["n_lobbyists"], reverse=True)


def find_triangles(G: nx.Graph) -> list[dict]:
    """(legislator, client, agency) triangles where the legislator mentions a
    client whose lobbyist used to staff that same agency. This is the headline
    structural finding and it pops out as a 3-cycle in the graph."""
    out = []
    for client_id, attrs in G.nodes(data=True):
        if attrs.get("type") != "client":
            continue
        neighbors = list(G.neighbors(client_id))
        leg_ids = [m for m in neighbors if G.nodes[m].get("type") == "legislator"]
        agency_ids = [m for m in neighbors if G.nodes[m].get("type") == "agency"]
        lobbyist_ids = [m for m in neighbors if G.nodes[m].get("type") == "lobbyist"]
        # Need: client connected to >=1 legislator (mentions) AND >=1 agency
        # (funded_by) AND >=1 lobbyist (lobbies_for) — that's the structural
        # triangle the story rests on.
        if leg_ids and agency_ids and lobbyist_ids:
            for leg in leg_ids:
                for agency in agency_ids:
                    # Lobbyist whose former_official_of edge lands on this agency:
                    matching_lobbyists = [
                        L for L in lobbyist_ids
                        if G.has_edge(L, agency)
                        and G[L][agency].get("type") == "former_official_of"
                    ]
                    if matching_lobbyists:
                        out.append({
                            "legislator": G.nodes[leg].get("label"),
                            "client": attrs.get("label"),
                            "agency": G.nodes[agency].get("label"),
                            "lobbyists": [G.nodes[L].get("label") for L in matching_lobbyists],
                            "n_mentions": G[leg][client_id].get("weight", 1),
                            "agency_to_client_dollars": G[agency][client_id].get("weight", 0),
                        })
    # Sort by mentions then by money — pop the most-evidence triangles first.
    return sorted(out, key=lambda r: (r["n_mentions"], r["agency_to_client_dollars"]),
                  reverse=True)


def find_hubs(G: nx.Graph) -> list[dict]:
    """Clients with both meaningful agency dollars AND meaningful legislator
    mentions — high signal. Score = log(dollars+1) * n_mentions."""
    out = []
    for n, attrs in G.nodes(data=True):
        if attrs.get("type") != "client":
            continue
        dollars = 0.0
        mentions = 0
        agencies = []
        legislators = []
        for m in G.neighbors(n):
            mtype = G.nodes[m].get("type")
            edge_type = G[n][m].get("type")
            if mtype == "agency" and edge_type == "funded_by":
                dollars += float(G[n][m].get("weight", 0))
                agencies.append(G.nodes[m].get("label"))
            elif mtype == "legislator":
                mentions += int(G[n][m].get("weight", 1))
                legislators.append(G.nodes[m].get("label"))
        if dollars > 0 and mentions > 0:
            score = math.log10(dollars + 1) * mentions
            out.append({
                "client": attrs.get("label"),
                "dollars": dollars,
                "n_mentions": mentions,
                "agencies": sorted(set(agencies)),
                "score": round(score, 2),
            })
    return sorted(out, key=lambda r: r["score"], reverse=True)


# ── Layout (spring force, deterministic) ──────────────────────────────────────


def layout(G: nx.Graph, seed: int = 42) -> dict[str, tuple[float, float]]:
    """NetworkX spring layout (Fruchterman-Reingold). Seeded for reproducibility
    — running the script twice with the same input data produces byte-identical
    SVG / JSON, which is critical for the no-surprises diff in `git status`."""
    if G.number_of_nodes() == 0:
        return {}
    return nx.spring_layout(G, seed=seed, k=1.5 / math.sqrt(max(G.number_of_nodes(), 1)))


# ── Output: JSON for the web UI ───────────────────────────────────────────────


def to_web_json(G: nx.Graph, pos: dict, *, included_findings: list[dict],
                bridges: list, triangles: list, hubs: list) -> dict:
    """Shape the JSON the way d3-force wants it (arrays of nodes + arrays of
    links), with our typed metadata preserved per-node and per-edge."""
    nodes = []
    for nid, attrs in G.nodes(data=True):
        x, y = pos.get(nid, (0.0, 0.0))
        nodes.append({
            "id": nid,
            "label": attrs.get("label") or nid,
            "type": attrs.get("type") or "unknown",
            "x": float(x) * 1000.0,           # scale to roughly fit a 1000-wide canvas
            "y": float(y) * 1000.0,
            "color": NODE_COLORS.get(attrs.get("type"), "#64748b"),
            "radius": NODE_RADII.get(attrs.get("type"), 6),
            # Per-type metadata for tooltips:
            "rank": attrs.get("rank"),
            "score": attrs.get("score"),
            "concentration": attrs.get("concentration"),
            "prior_role": attrs.get("prior_role"),
            "party": attrs.get("party"),
            "state": attrs.get("state"),
            "chamber": attrs.get("chamber"),
        })

    links = []
    for u, v, attrs in G.edges(data=True):
        primary = attrs.get("type") or "unknown"
        style = EDGE_STYLES.get(primary, {"color": "#cbd5e1", "width": 1.0})
        links.append({
            "source": u,
            "target": v,
            "type": primary,
            "types": attrs.get("types", [primary]),
            "weight": float(attrs.get("weight") or 1),
            "weights": attrs.get("weights", {}),
            "color": style["color"],
            "width": style["width"],
            "dash": style.get("dash"),
            # Carry mention-edge metadata so the UI can render a clickable
            # "Latest mention" line on the tooltip:
            "latest_title": attrs.get("latest_title"),
            "latest_url": attrs.get("latest_url"),
            "latest_date": attrs.get("latest_date"),
        })

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_findings_included": len(included_findings),
        "stats": _stats(G),
        "bridges": bridges,
        "triangles": triangles,
        "hubs": hubs,
        "legend": [
            {"type": k, "color": NODE_COLORS[k]}
            for k in ("lobbyist", "firm", "agency", "client", "legislator")
        ],
        "nodes": nodes,
        "links": links,
    }


def _stats(G: nx.Graph) -> dict:
    by_type = Counter(attrs.get("type") for _, attrs in G.nodes(data=True))
    edge_types = Counter(attrs.get("type") for _, _, attrs in G.edges(data=True))
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "nodes_by_type": dict(by_type),
        "edges_by_type": dict(edge_types),
    }


# ── Output: static SVG (no Graphviz dep) ──────────────────────────────────────


SVG_WIDTH = 1400
SVG_HEIGHT = 900
SVG_PAD = 60


def to_svg(G: nx.Graph, pos: dict) -> str:
    """Render a static SVG from the NetworkX layout, scaling positions into the
    SVG_WIDTH × SVG_HEIGHT canvas. Pure-Python text emission — no
    cairo/Graphviz/matplotlib dependency, so this runs the same way in CI as it
    does locally."""
    if not pos:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}"/>'

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spread_x = (maxx - minx) or 1.0
    spread_y = (maxy - miny) or 1.0

    def proj(p: tuple[float, float]) -> tuple[float, float]:
        x = SVG_PAD + (p[0] - minx) / spread_x * (SVG_WIDTH - 2 * SVG_PAD)
        y = SVG_PAD + (p[1] - miny) / spread_y * (SVG_HEIGHT - 2 * SVG_PAD)
        return x, y

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="11">'
    )
    parts.append('<rect width="100%" height="100%" fill="#f8fafc"/>')

    # Edges underneath nodes.
    for u, v, attrs in G.edges(data=True):
        x1, y1 = proj(pos[u])
        x2, y2 = proj(pos[v])
        style = EDGE_STYLES.get(attrs.get("type"), {"color": "#cbd5e1", "width": 1.0})
        dash = f' stroke-dasharray="{style["dash"]}"' if style.get("dash") else ""
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{style["color"]}" stroke-width="{style["width"]}"{dash} opacity="0.55"/>'
        )

    # Nodes.
    for nid, attrs in G.nodes(data=True):
        x, y = proj(pos[nid])
        ntype = attrs.get("type") or "unknown"
        color = NODE_COLORS.get(ntype, "#64748b")
        r = NODE_RADII.get(ntype, 6)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" '
            f'stroke="white" stroke-width="1.5">'
            f'<title>{_escape(attrs.get("label") or nid)} ({ntype})</title>'
            f'</circle>'
        )

    # Labels for high-degree / important nodes only (avoid label spaghetti).
    for nid, attrs in G.nodes(data=True):
        ntype = attrs.get("type")
        if ntype not in ("lobbyist", "agency", "firm"):
            continue
        if ntype == "firm" and G.degree(nid) < 2:
            continue
        x, y = proj(pos[nid])
        label = (attrs.get("label") or nid).split(":")[-1]
        parts.append(
            f'<text x="{x:.1f}" y="{y + NODE_RADII.get(ntype, 6) + 12:.1f}" '
            f'text-anchor="middle" fill="#0f172a" font-weight="600">'
            f'{_escape(label[:40])}</text>'
        )

    # Legend.
    legend_x, legend_y = SVG_PAD, SVG_HEIGHT - 30
    for i, (nt, color) in enumerate(NODE_COLORS.items()):
        cx = legend_x + i * 130
        parts.append(
            f'<circle cx="{cx + 8}" cy="{legend_y}" r="6" fill="{color}"/>'
            f'<text x="{cx + 22}" y="{legend_y + 4}" fill="#334155">{nt}</text>'
        )

    parts.append('</svg>')
    return "\n".join(parts)


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# ── Output: DOT for Graphviz ──────────────────────────────────────────────────


def to_dot(G: nx.Graph) -> str:
    """Emit a Graphviz DOT representation so users can `dot -Tpng coi.dot >
    coi.png` or feed it to any DOT-aware viewer. Layout is left to Graphviz."""
    lines = ["graph coi {", "  graph [layout=neato, overlap=false, splines=true];",
             '  node [style=filled, fontname="Inter", fontsize=10];', '  edge [color="#94a3b8"];']
    for nid, attrs in G.nodes(data=True):
        ntype = attrs.get("type") or "unknown"
        color = NODE_COLORS.get(ntype, "#64748b")
        label = (attrs.get("label") or nid).replace('"', "'")
        r = NODE_RADII.get(ntype, 6)
        lines.append(f'  "{nid}" [label="{label}", fillcolor="{color}", '
                     f'fontcolor="white", shape=circle, width={r / 20:.2f}, height={r / 20:.2f}];')
    for u, v, attrs in G.edges(data=True):
        etype = attrs.get("type") or ""
        style = EDGE_STYLES.get(etype, {"color": "#94a3b8", "width": 1.0})
        lines.append(f'  "{u}" -- "{v}" [color="{style["color"]}", '
                     f'penwidth={style["width"]:.1f}, label="{etype}"];')
    lines.append("}")
    return "\n".join(lines)


# ── Output: markdown summary ──────────────────────────────────────────────────


def to_markdown(stats: dict, bridges: list, triangles: list, hubs: list) -> str:
    lines: list[str] = []
    lines.append("## Conflict-of-interest graph")
    lines.append("")
    lines.append(
        f"Composed from {stats['nodes_by_type'].get('lobbyist', 0)} lobbyists, "
        f"{stats['nodes_by_type'].get('firm', 0)} firms, "
        f"{stats['nodes_by_type'].get('agency', 0)} agencies, "
        f"{stats['nodes_by_type'].get('client', 0)} clients, "
        f"{stats['nodes_by_type'].get('legislator', 0)} legislators "
        f"— **{stats['n_nodes']}** nodes, **{stats['n_edges']}** edges."
    )
    lines.append("")

    if triangles:
        lines.append("### Structural triangles (member · client · agency)")
        lines.append("")
        lines.append(
            "Each row is a member of Congress publicly mentioning a client whose "
            "lobbyist used to staff that client's funding agency. Order: mentions "
            "first, then dollars."
        )
        lines.append("")
        lines.append("| Legislator | Client | Agency | Lobbyist(s) | Mentions | Agency $ to client |")
        lines.append("|---|---|---|---|---:|---:|")
        for t in triangles[:25]:
            dollars = f"${t['agency_to_client_dollars']:,.0f}" if t['agency_to_client_dollars'] else "—"
            lines.append(
                f"| {t['legislator']} | {t['client']} | {t['agency']} | "
                f"{', '.join(t['lobbyists'])} | {t['n_mentions']} | {dollars} |"
            )
        lines.append("")
    else:
        lines.append("_No triangles found._")
        lines.append("")

    if hubs:
        lines.append("### Hubs (client × agency $ × legislator mentions)")
        lines.append("")
        lines.append("| Client | Agencies | Dollars | Mentions | Hub score |")
        lines.append("|---|---|---:|---:|---:|")
        for h in hubs[:15]:
            lines.append(
                f"| {h['client']} | {', '.join(h['agencies'])} | "
                f"${h['dollars']:,.0f} | {h['n_mentions']} | {h['score']} |"
            )
        lines.append("")

    if bridges:
        lines.append("### Bridges (clients shared by ≥2 lobbyists in scope)")
        lines.append("")
        lines.append("| Client | # lobbyists | Lobbyists |")
        lines.append("|---|---:|---|")
        for b in bridges[:15]:
            lines.append(
                f"| {b['client']} | {b['n_lobbyists']} | {', '.join(b['lobbyists'])} |"
            )
        lines.append("")

    lines.append("### How to read this")
    lines.append("")
    lines.append(
        "The graph composes the outputs of scan, trace, and pressrel into one "
        "object so the *connections* across them become visible. Triangles are "
        "the headline structure — a member publicly aligns with a company "
        "whose lobbyist used to staff that company's funder. Hubs are clients "
        "where the alignment shows up in both money and public messaging. "
        "Bridges are clients that recur across two or more independent "
        "revolving-door cases — possible focal points for a wider story."
    )
    lines.append("")
    lines.append(
        "**Reporting discipline:** none of this is wrongdoing on its face. "
        "Each triangle is a publishable lead only after (a) confirming the "
        "member's committee jurisdiction covers the agency, (b) checking the "
        "§207 cooling-off status of the lobbyist (notes/09), and (c) "
        "documenting a real request for comment (notes/comment_requests/)."
    )
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────


def load_findings(path: Path, top: int | None, finding_rank: int | None) -> list[dict]:
    if not path.exists():
        sys.exit(f"FATAL: {path} not found. Run /fair-guard scan (and ideally trace + pressrel) first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    findings = data.get("findings", [])
    if finding_rank is not None:
        findings = [f for f in findings if f.get("rank") == finding_rank]
        if not findings:
            sys.exit(f"no finding with rank={finding_rank} in {path}")
    elif top:
        findings = findings[:top]
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--top", type=int, default=10,
                    help="How many top scan findings to include (default 10).")
    ap.add_argument("--finding-rank", type=int,
                    help="Render only the subgraph around a single finding's rank.")
    ap.add_argument("--out", type=Path,
                    help="Write the markdown summary to this file (else stdout).")
    ap.add_argument("--json-out", type=Path, default=WEB_OUT,
                    help=f"Where to write the web JSON (default {WEB_OUT}).")
    ap.add_argument("--svg-out", type=Path, default=SVG_OUT,
                    help=f"Where to write the static SVG (default {SVG_OUT}).")
    ap.add_argument("--dot-out", type=Path, default=DOT_OUT,
                    help=f"Where to write the Graphviz DOT (default {DOT_OUT}).")
    ap.add_argument("--no-web", action="store_true", help="Skip writing the web JSON.")
    ap.add_argument("--no-svg", action="store_true", help="Skip writing the SVG and DOT.")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    findings = load_findings(FINDINGS_JSON, args.top, args.finding_rank)
    sys.stderr.write(f"loaded {len(findings)} finding(s) from {FINDINGS_JSON}\n")

    G = build_graph(findings)
    pos = layout(G)
    bridges = find_shared_clients(G)
    triangles = find_triangles(G)
    hubs = find_hubs(G)

    sys.stderr.write(
        f"graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges; "
        f"{len(triangles)} triangle(s), {len(hubs)} hub(s), {len(bridges)} bridge(s)\n"
    )

    md = to_markdown(_stats(G), bridges, triangles, hubs)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        sys.stderr.write(f"wrote {args.out}\n")
    else:
        print(md)

    if not args.no_web:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        payload = to_web_json(G, pos, included_findings=findings,
                              bridges=bridges, triangles=triangles, hubs=hubs)
        args.json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stderr.write(f"wrote {args.json_out} (n_nodes={payload['stats']['n_nodes']})\n")

    if not args.no_svg:
        args.svg_out.parent.mkdir(parents=True, exist_ok=True)
        args.svg_out.write_text(to_svg(G, pos), encoding="utf-8")
        sys.stderr.write(f"wrote {args.svg_out}\n")
        args.dot_out.parent.mkdir(parents=True, exist_ok=True)
        args.dot_out.write_text(to_dot(G), encoding="utf-8")
        sys.stderr.write(f"wrote {args.dot_out}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
