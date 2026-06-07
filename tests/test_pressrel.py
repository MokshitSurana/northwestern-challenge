"""Tests for the press-release cross-ref skill (scripts/05_pressrel_search.py).

Unit tests cover the matching discipline (word boundaries, smart quotes, snippet
extraction, de-dup) deterministically — no DuckDB required.

Integration tests run against the real output/investigation.duckdb when present
and are skipped automatically when it isn't (matches the pattern used by
tests/test_entity_resolver.py::test_f1_on_db).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "05_pressrel_search.py"
DB_PATH = REPO_ROOT / "output" / "investigation.duckdb"


def _load_module():
    """Load the script as a module despite the leading-digit filename."""
    spec = importlib.util.spec_from_file_location("pressrel_search", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pressrel_search"] = mod
    spec.loader.exec_module(mod)
    return mod


PR = _load_module()


# ── build_term_regex: matching discipline ─────────────────────────────────────


class TestRegexMatching:
    """The regex is what stops 'Cargill' from false-matching 'Cargilltech' and
    what makes 'O'Lakes' match both straight and curly apostrophes. These tests
    pin those behaviors down so a refactor of build_term_regex can't silently
    break them."""

    def test_word_boundary_no_substring_match(self):
        """The headline guarantee: a literal alias does NOT match inside a
        longer word. This is the single property a journalist relies on most."""
        regex = PR.build_term_regex(["Cargill"])
        assert re.search(regex, "Cargill announced", re.IGNORECASE)
        assert re.search(regex, "lawsuit against Cargill.", re.IGNORECASE)
        assert re.search(regex, "Garland v. Cargill ruling", re.IGNORECASE)
        # The negative cases:
        assert not re.search(regex, "Cargilltechnologies hired", re.IGNORECASE)
        assert not re.search(regex, "ProcessCargillation", re.IGNORECASE)

    def test_case_insensitive(self):
        regex = PR.build_term_regex(["Cirba Solutions"])
        for variant in ("Cirba Solutions", "CIRBA SOLUTIONS", "cirba solutions", "Cirba SOLUTIONS"):
            assert re.search(regex, f"as {variant} announced", re.IGNORECASE)

    def test_smart_quote_tolerance(self):
        """Press releases overwhelmingly use curly quotes (U+2019). An alias
        with a straight apostrophe must still match the curly variant."""
        regex = PR.build_term_regex(["Land O'Lakes"])
        assert re.search(regex, "Land O'Lakes won the award", re.IGNORECASE)
        assert re.search(regex, "Land O’Lakes won the award", re.IGNORECASE)
        assert re.search(regex, "Land O‘Lakes won the award", re.IGNORECASE)

    def test_smart_double_quote_tolerance(self):
        regex = PR.build_term_regex(['Big "Bank" Inc'])
        assert re.search(regex, 'Big "Bank" Inc reported', re.IGNORECASE)
        assert re.search(regex, "Big “Bank” Inc reported", re.IGNORECASE)

    def test_multiple_aliases_orred(self):
        regex = PR.build_term_regex(["Cirba Solutions", "Anovion", "Talon Nickel"])
        assert re.search(regex, "Cirba Solutions plant", re.IGNORECASE)
        assert re.search(regex, "and Anovion received", re.IGNORECASE)
        assert re.search(regex, "Talon Nickel mine", re.IGNORECASE)
        assert not re.search(regex, "Unrelated Industries", re.IGNORECASE)

    def test_special_characters_escaped(self):
        """Regex meta-characters in aliases must not break the regex compile."""
        regex = PR.build_term_regex(["A&M (Texas)", "S.P.C. Co."])
        # Should compile without error and match literal forms:
        assert re.search(regex, "A&M (Texas) received", re.IGNORECASE)
        assert re.search(regex, "S.P.C. Co. announced", re.IGNORECASE)
        # And NOT match the regex-pattern interpretation:
        assert not re.search(regex, "AXM AnyTexas received", re.IGNORECASE)

    def test_empty_alias_list_does_not_match(self):
        """Build a guaranteed-no-match pattern when no real aliases supplied."""
        regex = PR.build_term_regex([])
        assert not re.search(regex, "any text at all", re.IGNORECASE)
        regex2 = PR.build_term_regex(["", "  "])
        assert not re.search(regex2, "any text at all", re.IGNORECASE)


# ── first_snippet: context window + bolding ────────────────────────────────────


class TestSnippet:
    def test_basic_snippet_bolds_match(self):
        text = "Senator XYZ today announced that Cirba Solutions will build a new battery recycling plant in Ohio."
        snip = PR.first_snippet(text, PR.build_term_regex(["Cirba Solutions"]))
        assert "**Cirba Solutions**" in snip
        assert "battery recycling" in snip

    def test_snippet_collapses_whitespace(self):
        text = "Praise\n\nfor   Cirba Solutions   today\nin\nremarks"
        snip = PR.first_snippet(text, PR.build_term_regex(["Cirba Solutions"]))
        assert "  " not in snip
        assert "\n" not in snip

    def test_snippet_truncation_ellipsis(self):
        before = "A" * 500
        after = "Z" * 500
        text = before + " Cirba Solutions " + after
        snip = PR.first_snippet(text, PR.build_term_regex(["Cirba Solutions"]), radius=80)
        assert snip.startswith("…")
        assert snip.endswith("…")
        assert "**Cirba Solutions**" in snip

    def test_snippet_no_match_returns_empty(self):
        snip = PR.first_snippet("Nothing in here", PR.build_term_regex(["Cirba Solutions"]))
        assert snip == ""

    def test_snippet_only_first_match(self):
        """Two mentions of the same alias — snippet anchors on the first one."""
        text = "Cirba Solutions plant one. ... Cirba Solutions plant two."
        snip = PR.first_snippet(text, PR.build_term_regex(["Cirba Solutions"]))
        # First occurrence should be bolded; second appears in plain text.
        assert snip.count("**Cirba Solutions**") == 1
        assert snip.count("Cirba Solutions") >= 1


# ── load_case: schema validation ──────────────────────────────────────────────


class TestCaseFile:
    def _write(self, tmp_path, payload):
        p = tmp_path / "case.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_missing_label_exits(self, tmp_path):
        path = self._write(tmp_path, {"clients": [{"name": "X"}]})
        with pytest.raises(SystemExit):
            PR.load_case(path)

    def test_missing_clients_exits(self, tmp_path):
        path = self._write(tmp_path, {"label": "L"})
        with pytest.raises(SystemExit):
            PR.load_case(path)

    def test_empty_clients_exits(self, tmp_path):
        path = self._write(tmp_path, {"label": "L", "clients": []})
        with pytest.raises(SystemExit):
            PR.load_case(path)

    def test_client_missing_name_exits(self, tmp_path):
        path = self._write(tmp_path, {"label": "L", "clients": [{"aliases": ["a"]}]})
        with pytest.raises(SystemExit):
            PR.load_case(path)

    def test_aliases_default_to_name(self, tmp_path):
        path = self._write(tmp_path, {"label": "L", "clients": [{"name": "Foo"}]})
        case = PR.load_case(path)
        assert case["clients"][0]["aliases"] == ["Foo"]

    def test_filters_get_defaults(self, tmp_path):
        path = self._write(tmp_path, {"label": "L", "clients": [{"name": "Foo"}]})
        case = PR.load_case(path)
        assert case["filters"]["since"] == PR.DEFAULT_SINCE
        assert case["filters"]["until"] == PR.DEFAULT_UNTIL

    def test_existing_filters_preserved(self, tmp_path):
        path = self._write(tmp_path, {
            "label": "L",
            "clients": [{"name": "Foo"}],
            "filters": {"since": "2024-01-01", "party": "Democrat"},
        })
        case = PR.load_case(path)
        assert case["filters"]["since"] == "2024-01-01"
        assert case["filters"]["party"] == "Democrat"
        # Defaulted fields still get filled in:
        assert case["filters"]["until"] == PR.DEFAULT_UNTIL


# ── render_markdown: shape checks ──────────────────────────────────────────────


class TestRender:
    def _stub_report(self):
        return {
            "case_id": "test",
            "label": "Test report",
            "generated_at": "2026-06-06T00:00:00+00:00",
            "filters": {"since": "2024-01-01", "until": "2026-01-01"},
            "match": [],
            "n_clients": 1,
            "n_matches": 1,
            "n_distinct_members": 1,
            "per_client": [{
                "client": "Cirba Solutions",
                "aliases": ["Cirba Solutions"],
                "n_matches": 1,
                "n_distinct_members": 1,
                "first_date": "2024-06-01",
                "last_date": "2024-06-01",
            }],
            "matches": [{
                "client": "Cirba Solutions",
                "date": "2024-06-01",
                "bioguide_id": "A000000",
                "member_name": "Jane Doe",
                "party": "Democrat",
                "state": "OH",
                "chamber": "House",
                "title": "Doe Announces Battery Plant",
                "url": "https://doe.house.gov/news/example",
                "snippet": "…announced that **Cirba Solutions** will build…",
            }],
        }

    def test_markdown_includes_required_sections(self):
        md = PR.render_markdown(self._stub_report())
        assert "## Press-release cross-ref: Test report" in md
        assert "### Per-client tallies" in md
        assert "### Matches" in md
        assert "### Framing" in md

    def test_markdown_member_compact_format(self):
        """Member column should be 'Name (Party · State · Chamber)' with single-
        letter codes for compact rendering."""
        md = PR.render_markdown(self._stub_report())
        assert "Jane Doe (D·OH·H)" in md

    def test_markdown_includes_snippet_and_url(self):
        md = PR.render_markdown(self._stub_report())
        assert "**Cirba Solutions**" in md
        assert "<https://doe.house.gov/news/example>" in md

    def test_markdown_pipe_escapes_in_title(self):
        """Pipe characters in titles must be escaped so the markdown table
        doesn't break."""
        rep = self._stub_report()
        rep["matches"][0]["title"] = "Doe | Co-sponsors | Bill"
        md = PR.render_markdown(rep)
        # The escaped form is what survives the pipe table:
        assert r"Doe \| Co-sponsors \| Bill" in md

    def test_empty_matches_shows_no_mentions_line(self):
        rep = self._stub_report()
        rep["matches"] = []
        rep["n_matches"] = 0
        rep["n_distinct_members"] = 0
        md = PR.render_markdown(rep)
        assert "No verified mentions found in the window" in md


# ── Integration tests (real DB required) ──────────────────────────────────────


@pytest.mark.skipif(not DB_PATH.exists(), reason="output/investigation.duckdb not present")
class TestIntegration:
    def test_real_cargill_search_returns_hits(self):
        with PR._connect() as con:
            hits, regex = PR.search(con, ["Cargill"], limit=50)
        # The corpus has multiple Cargill mentions (Supreme Court case + the
        # actual company). The exact count varies with corpus refreshes; the
        # invariant is "more than a handful and every hit names Cargill in
        # title or snippet" — case-insensitive because the corpus uses both
        # "Cargill" and (rarely) "CARGILL" in shouting headlines.
        assert len(hits) > 5
        for h in hits:
            haystack = (h.get("title") or "") + " " + (h.get("snippet") or "")
            assert "cargill" in haystack.lower(), f"row missing Cargill: {h}"

    def test_real_dedup_works(self):
        """De-dup on (bioguide_id, date, title) — the script should never
        return two rows with the same triple, even when the same release
        appears twice in the raw corpus."""
        with PR._connect() as con:
            hits, _ = PR.search(con, ["Cargill"], limit=100)
        seen = {(h["bioguide_id"], h["date"], h["title"]) for h in hits}
        assert len(seen) == len(hits)

    def test_real_case_file_runs(self):
        case_path = REPO_ROOT / "skill" / "press-release-cross-ref" / "cases" / "steinberg_clients.json"
        case = PR.load_case(case_path)
        case["case_id"] = case_path.stem
        with PR._connect() as con:
            report = PR.search_case(case, con, per_client_limit=5)
        assert report["case_id"] == "steinberg_clients"
        assert report["n_clients"] == len(case["clients"])
        # Wabtec + critical minerals should produce matches reliably.
        assert report["n_matches"] >= 5

    def test_real_filter_chamber(self):
        with PR._connect() as con:
            hits, _ = PR.search(con, ["Cargill"], chamber="Senate", limit=100)
        for h in hits:
            assert (h.get("chamber") or "").lower() == "senate"

    def test_real_filter_party(self):
        with PR._connect() as con:
            hits, _ = PR.search(con, ["Cargill"], party="Democrat", limit=100)
        for h in hits:
            assert h.get("party") == "Democrat"

    def test_real_date_window(self):
        with PR._connect() as con:
            hits, _ = PR.search(con, ["Cargill"], since="2024-01-01", until="2024-12-31", limit=100)
        for h in hits:
            assert "2024-01-01" <= (h.get("date") or "") <= "2024-12-31"
