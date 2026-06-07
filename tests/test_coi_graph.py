"""Tests for the coi-graph skill (scripts/06_coi_graph.py).

Unit tests exercise the canonicalization, graph build, and structural-pattern
detectors against synthetic in-memory findings. Integration tests run against
the real web/public/findings.json when present and skip otherwise (matches the
pattern in test_pressrel.py)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "06_coi_graph.py"
FINDINGS_JSON = REPO_ROOT / "web" / "public" / "findings.json"


def _load():
    spec = importlib.util.spec_from_file_location("coi_graph", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["coi_graph"] = mod
    spec.loader.exec_module(mod)
    return mod


CG = _load()


# ── canonical_client: the cross-source merge key ─────────────────────────────


class TestCanonicalClient:
    """canonical_client() is what makes scan's 'AMSTED INDUSTRIES' and pressrel's
    'Amsted Industries' collapse onto the same node. If this regresses, the
    graph silently loses triangles. These tests pin the behavior."""

    def test_case_insensitive_merge(self):
        assert CG.canonical_client("AMSTED INDUSTRIES") == CG.canonical_client("Amsted Industries")
        assert CG.canonical_client("WABTEC") == CG.canonical_client("Wabtec")

    def test_strips_parenthetical(self):
        assert CG.canonical_client("Cargill (operating entities)") == "CARGILL"
        assert CG.canonical_client("TALON NICKEL (USA) LLC") == "TALON NICKEL"

    def test_strips_corporate_suffixes(self):
        for variant in ("Cargill Inc", "CARGILL INC", "Cargill, Inc.", "CARGILL CORPORATION", "Cargill LLC"):
            assert CG.canonical_client(variant) == "CARGILL", f"failed on {variant!r}"

    def test_amp_normalization(self):
        # Ampersand should be ignored — "Burns & McDonnell" and "Burns McDonnell" merge.
        assert CG.canonical_client("Burns & McDonnell") == CG.canonical_client("Burns McDonnell")

    def test_truncates_to_three_tokens(self):
        """Long corporate names get folded down to the leading distinctive
        tokens. Burns & McDonnell Engineering Company Inc → BURNS MCDONNELL
        ENGINEERING (3 tokens after stripping & + COMPANY + INC)."""
        long = "Burns & McDonnell Engineering Company Inc"
        result = CG.canonical_client(long)
        assert result.startswith("BURNS"), result
        assert len(result.split()) <= 3, result

    def test_empty_input(self):
        assert CG.canonical_client("") == ""
        assert CG.canonical_client("   ") == ""

    def test_all_noise_falls_back_to_first_tokens(self):
        # 'The Group' is entirely noise words; falls back to the original tokens
        # so we don't lose the node entirely.
        result = CG.canonical_client("The Group")
        assert result != ""


# ── build_graph: shapes + edge merging ────────────────────────────────────────


class TestBuildGraph:
    def _stub_findings(self):
        """Two findings sharing one client across two agencies — should
        produce a 'bridge' (the shared client) plus typed edges."""
        return [
            {
                "rank": 1,
                "lobbyist_name": "Alice Lobbyist",
                "registrant_name": "Big Firm LLC",
                "agency_short": "energy",
                "concentration": 0.9,
                "covered_position": "Former DOE official",
                "top_clients_str": "Cirba Solutions | Talon Nickel (USA) LLC",
                "trail": {
                    "clients": [
                        {"label": "Cirba Solutions", "total": 1000000, "discretionary_amount": 1000000, "n_awards": 2},
                    ]
                },
                "press_releases": {
                    "by_client": [
                        {
                            "client": "Cirba Solutions",
                            "matches": [
                                {"member_name": "Sen X", "party": "Democrat", "state": "WV",
                                 "chamber": "Senate", "title": "X praises Cirba",
                                 "url": "http://x", "date": "2024-01-01"},
                            ],
                        }
                    ]
                },
            },
            {
                "rank": 2,
                "lobbyist_name": "Bob Lobbyist",
                "registrant_name": "Other Firm",
                "agency_short": "interior",
                "concentration": 0.7,
                "covered_position": "Former Interior official",
                "top_clients_str": "Cirba Solutions | Friant Water",
            },
        ]

    def test_node_types_present(self):
        G = CG.build_graph(self._stub_findings())
        types = {attrs.get("type") for _, attrs in G.nodes(data=True)}
        # legislator may or may not show up depending on pressrel data, but the
        # core types must all appear:
        assert {"lobbyist", "firm", "agency", "client"} <= types

    def test_two_lobbyists_one_shared_client(self):
        G = CG.build_graph(self._stub_findings())
        # Cirba canonicalizes to "CIRBA SOLUTIONS" — one client node.
        cirba_id = CG._nid("client", "Cirba Solutions")
        assert cirba_id in G
        lobbyists = [n for n in G.neighbors(cirba_id)
                     if G.nodes[n].get("type") == "lobbyist"]
        assert len(lobbyists) == 2

    def test_former_official_edge_carries_concentration(self):
        G = CG.build_graph(self._stub_findings())
        ln = CG._nid("lobbyist", "Alice Lobbyist")
        an = CG._nid("agency", "ENERGY")
        edge = G[ln][an]
        assert edge["type"] == "former_official_of"
        assert edge["weight"] == pytest.approx(0.9)

    def test_funded_by_edge_carries_dollars(self):
        G = CG.build_graph(self._stub_findings())
        an = CG._nid("agency", "ENERGY")
        cirba = CG._nid("client", "Cirba Solutions")
        assert G.has_edge(an, cirba)
        assert G[an][cirba]["type"] == "funded_by"
        assert G[an][cirba]["weight"] == 1000000

    def test_legislator_mentions_aggregate_weight(self):
        """Two press-release matches from the same member on the same client
        should collapse to ONE edge with weight=2."""
        findings = self._stub_findings()
        findings[0]["press_releases"]["by_client"][0]["matches"].append({
            "member_name": "Sen X", "party": "Democrat", "state": "WV",
            "chamber": "Senate", "title": "X praises Cirba AGAIN",
            "url": "http://x2", "date": "2024-02-01",
        })
        G = CG.build_graph(findings)
        leg_id = CG._nid("legislator", "Sen X (D-WV-S)")
        cirba = CG._nid("client", "Cirba Solutions")
        assert G[leg_id][cirba]["weight"] == 2


# ── Triangle / hub / bridge detection ─────────────────────────────────────────


class TestPatterns:
    def _triangle_findings(self):
        """One scan finding where the trail funds the client AND the press
        release mentions it — the textbook triangle case."""
        return [{
            "rank": 1,
            "lobbyist_name": "Ash Test",
            "registrant_name": "Test Firm",
            "agency_short": "usda",
            "concentration": 0.85,
            "covered_position": "Former USDA official",
            "top_clients_str": "Cargill",
            "trail": {
                "clients": [
                    {"label": "Cargill", "total": 700_000_000,
                     "discretionary_amount": 5_000_000, "n_awards": 100},
                ]
            },
            "press_releases": {
                "by_client": [
                    {"client": "Cargill", "matches": [
                        {"member_name": "Tammy Test", "party": "Democrat", "state": "WI",
                         "chamber": "Senate", "title": "Test praises Cargill",
                         "url": "http://t", "date": "2024-01-01"},
                    ]}
                ]
            },
        }]

    def test_triangle_is_detected(self):
        G = CG.build_graph(self._triangle_findings())
        triangles = CG.find_triangles(G)
        assert len(triangles) == 1
        t = triangles[0]
        assert t["legislator"] == "Tammy Test (D-WI-S)"
        assert t["client"] == "Cargill"
        assert t["agency"] == "USDA"
        assert t["agency_to_client_dollars"] == 700_000_000

    def test_no_triangle_without_money(self):
        findings = self._triangle_findings()
        del findings[0]["trail"]
        G = CG.build_graph(findings)
        assert CG.find_triangles(G) == []

    def test_no_triangle_without_press_release(self):
        findings = self._triangle_findings()
        del findings[0]["press_releases"]
        G = CG.build_graph(findings)
        assert CG.find_triangles(G) == []

    def test_hub_scoring(self):
        G = CG.build_graph(self._triangle_findings())
        hubs = CG.find_hubs(G)
        assert len(hubs) == 1
        h = hubs[0]
        assert h["client"] == "Cargill"
        assert h["dollars"] == 700_000_000
        assert h["n_mentions"] == 1
        assert h["score"] > 0

    def test_bridge_detected(self):
        # Two lobbyists, one shared client → bridge.
        G = CG.build_graph(TestBuildGraph()._stub_findings())
        bridges = CG.find_shared_clients(G)
        assert any(b["client"] == "Cirba Solutions" for b in bridges)


# ── Output renderers ──────────────────────────────────────────────────────────


class TestOutputs:
    def _make_outputs(self):
        findings = TestPatterns()._triangle_findings()
        G = CG.build_graph(findings)
        pos = CG.layout(G, seed=1)
        return G, pos, findings

    def test_to_web_json_has_required_fields(self):
        G, pos, findings = self._make_outputs()
        payload = CG.to_web_json(G, pos, included_findings=findings,
                                 bridges=[], triangles=[], hubs=[])
        # d3-force expects nodes + links arrays:
        assert isinstance(payload["nodes"], list)
        assert isinstance(payload["links"], list)
        # Every node has id, label, type, x, y, color:
        for node in payload["nodes"]:
            for key in ("id", "label", "type", "x", "y", "color"):
                assert key in node, f"node missing {key}: {node}"

    def test_to_web_json_legend_present(self):
        G, pos, findings = self._make_outputs()
        payload = CG.to_web_json(G, pos, included_findings=findings,
                                 bridges=[], triangles=[], hubs=[])
        legend_types = {item["type"] for item in payload["legend"]}
        assert legend_types == {"lobbyist", "firm", "agency", "client", "legislator"}

    def test_to_svg_well_formed(self):
        G, pos, _ = self._make_outputs()
        svg = CG.to_svg(G, pos)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert "<circle" in svg
        assert "<line" in svg

    def test_to_dot_well_formed(self):
        G, _, _ = self._make_outputs()
        dot = CG.to_dot(G)
        assert dot.startswith("graph coi {")
        assert dot.endswith("}")
        assert "[layout=neato" in dot

    def test_to_markdown_renders_triangles(self):
        triangles = [{
            "legislator": "L", "client": "C", "agency": "A",
            "lobbyists": ["X"], "n_mentions": 2,
            "agency_to_client_dollars": 1000,
        }]
        md = CG.to_markdown({"n_nodes": 1, "n_edges": 1,
                             "nodes_by_type": {"lobbyist": 1, "firm": 0, "agency": 0, "client": 0, "legislator": 0}},
                            bridges=[], triangles=triangles, hubs=[])
        assert "Structural triangles" in md
        assert "L | C | A" in md


# ── Determinism ──────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_layout_seed_reproducible(self):
        G = CG.build_graph(TestPatterns()._triangle_findings())
        p1 = CG.layout(G, seed=42)
        p2 = CG.layout(G, seed=42)
        for node_id, pos1 in p1.items():
            pos2 = p2[node_id]
            assert pos1[0] == pytest.approx(pos2[0])
            assert pos1[1] == pytest.approx(pos2[1])


# ── Integration: real findings.json ──────────────────────────────────────────


@pytest.mark.skipif(not FINDINGS_JSON.exists(), reason="web/public/findings.json not present")
class TestIntegration:
    def test_real_graph_has_all_node_types(self):
        data = json.loads(FINDINGS_JSON.read_text(encoding="utf-8"))
        findings = data.get("findings", [])[:10]
        G = CG.build_graph(findings)
        types = {attrs.get("type") for _, attrs in G.nodes(data=True)}
        # At least lobbyist + firm + agency + client must be present from scan
        # alone. legislator depends on pressrel data.
        assert {"lobbyist", "firm", "agency", "client"} <= types

    def test_real_graph_finds_at_least_one_bridge(self):
        """Newsome and Parsons are both at Delta Strategy Group and both
        appear in the top 10 — that's our anchor bridge."""
        data = json.loads(FINDINGS_JSON.read_text(encoding="utf-8"))
        findings = data.get("findings", [])[:10]
        G = CG.build_graph(findings)
        bridges = CG.find_shared_clients(G)
        assert len(bridges) >= 1

    def test_real_top10_graph_emits_valid_json(self):
        """End-to-end: the JSON payload validates against the d3-force shape
        (nodes + links arrays, every link source/target present in nodes)."""
        data = json.loads(FINDINGS_JSON.read_text(encoding="utf-8"))
        findings = data.get("findings", [])[:10]
        G = CG.build_graph(findings)
        pos = CG.layout(G)
        payload = CG.to_web_json(G, pos, included_findings=findings,
                                 bridges=[], triangles=[], hubs=[])
        node_ids = {n["id"] for n in payload["nodes"]}
        for link in payload["links"]:
            assert link["source"] in node_ids
            assert link["target"] in node_ids
