#!/usr/bin/env python3
"""
05_pressrel_search.py — Cross-reference Congressional press releases against
lobbying findings.

The press-release half of the corpus is what turns a structural lobbying finding
into a story with named legislators in it: when a member of Congress publicly
issues a press release praising or advocating for the same company that's being
lobbied for by a former agency official, that's the alignment a reporter wants
to see. This script searches 141K+ Congressional press releases (2022-2026,
House + Senate) for verified mentions of client / firm names, with member-side
filters (party, state, chamber, domain) and a snippet extraction that shows the
mention in context. Output is a journalism-ready markdown table plus a JSON
payload and (by default) web writes that enrich the Reporter UI.

Why a dedicated skill: 141K rows of free-text on disk is a poor place to do
ad-hoc grep. This wraps DuckDB regex search with the matching discipline we've
learned the hard way:

  1. Word-boundary matching, so "Cargill" doesn't false-match "Cargilltech."
  2. Per-client tallies + de-dup on (bioguide_id, date, title) — re-issued
     releases and cross-posts otherwise inflate counts.
  3. A snippet that shows the actual matched phrase, not the title, so a
     reporter can verify the mention without opening the URL.
  4. A `match` block on case files that keys the result back to a scan-finding
     row (mirrors the `trace` skill), so press-release evidence shows up
     inline on the candidate's card in the Reporter UI.

Usage:
    uv run scripts/05_pressrel_search.py --mention "Cirba Solutions"
    uv run scripts/05_pressrel_search.py --mention "battery supply chain" \\
        --since 2022-01-01 --party Democrat --chamber Senate
    uv run scripts/05_pressrel_search.py \\
        --case skill/press-release-cross-ref/cases/steinberg_clients.json
    uv run scripts/05_pressrel_search.py --enrich-findings
    uv run scripts/05_pressrel_search.py --print-template

Reads from output/investigation.duckdb (table: press_releases). Does not write
to that DB. Writes (default):
  - stdout (or --out FILE):       markdown table + framing note
  - --json FILE (optional):       raw JSON payload
  - web/public/press_releases.json: upserted per case_id, drives /pressrel UI
  - web/public/findings.json:     each matching finding row gains a
                                   `press_releases` field (skipped with --no-web)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "output" / "investigation.duckdb"
WEB_PUBLIC = REPO_ROOT / "web" / "public"
FINDINGS_JSON = WEB_PUBLIC / "findings.json"
PRESSREL_JSON = WEB_PUBLIC / "press_releases.json"

# Default window matches the rest of the corpus.
DEFAULT_SINCE = "2022-01-01"
DEFAULT_UNTIL = "2026-04-01"

# Snippet sizing: 120 chars on each side gives a reporter enough to assess
# whether the mention is substantive (named in a quote, named in a list of
# achievements) vs. incidental (named in a constituent letter).
SNIPPET_RADIUS = 120

# Cap per-client matches so a high-profile name doesn't drown the output.
# Anything above this and the reporter should narrow the query, not scroll.
DEFAULT_PER_CLIENT_LIMIT = 25

# cp1252 noise — the raw press release files have a sprinkling of replacement
# characters (�) where the original encoding wasn't UTF-8 clean. We surface
# them as-is in the snippet but ask DuckDB to also try the smart-quote variants
# when building search regexes.
SMART_QUOTE_PAIRS = [("'", "[‘’']"), ('"', '[“”\"]')]


# ── Text helpers ──────────────────────────────────────────────────────────────


def _norm_ws(s: str) -> str:
    """Collapse all whitespace runs to a single space — snippets read better."""
    return re.sub(r"\s+", " ", s).strip()


def build_term_regex(aliases: list[str]) -> str:
    """Build a single case-insensitive, word-boundary regex matching any of the
    aliases. Escapes regex meta-characters and substitutes smart-quote variants
    for ASCII quotes/apostrophes so 'O'Lakes' matches both 'O'Lakes' and
    'O’Lakes'.

    Boundary handling is per-alias rather than wrapping the whole alternation in
    \\b...\\b. \\b is a transition between word and non-word characters; if the
    alias's first or last char is itself non-word (e.g. 'A&M (Texas)' ends in
    ')'), a trailing \\b would never match because both sides of the boundary
    are non-word. So we add \\b only on sides where the alias has a word
    character. The boundary property a journalist actually wants — 'Cargill'
    matches but 'Cargilltechnologies' doesn't — is preserved either way because
    the boundary on the *word-character* side is the one that prevents the
    substring extension. RE2-compatible (DuckDB uses RE2; lookbehind would
    break)."""
    parts = []
    for raw in aliases:
        a = raw.strip()
        if not a:
            continue
        escaped = re.escape(a)
        # Re-allow smart quotes for the typographic apostrophes/quotes inside.
        for plain, klass in SMART_QUOTE_PAIRS:
            escaped = escaped.replace(re.escape(plain), klass)
        # Per-alias boundary: \b only where the adjacent character is word-class.
        left = r"\b" if a[0].isalnum() or a[0] == "_" else ""
        right = r"\b" if a[-1].isalnum() or a[-1] == "_" else ""
        parts.append(f"{left}(?:{escaped}){right}")
    if not parts:
        # An impossible-to-match pattern; signals "no real aliases".
        return r"(?!x)x"
    return r"(?:" + "|".join(parts) + r")"


def first_snippet(text: str, regex: str, radius: int = SNIPPET_RADIUS) -> str:
    """Return a snippet of `text` around the first regex match, with the
    matched phrase wrapped in **markdown bold** so it's instantly visible.
    Collapses whitespace and prefixes/suffixes ellipses when truncating."""
    if not text:
        return ""
    m = re.search(regex, text, flags=re.IGNORECASE)
    if not m:
        return ""
    start = max(0, m.start() - radius)
    end = min(len(text), m.end() + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    raw = text[start : m.start()] + "**" + m.group(0) + "**" + text[m.end() : end]
    return prefix + _norm_ws(raw) + suffix


# ── DuckDB query ──────────────────────────────────────────────────────────────


def _connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or DB_PATH
    if not path.exists():
        sys.exit(
            f"FATAL: {path} not found.\n"
            "Run /fair-guard index or download the pre-built output/ folder "
            "(see /fair-guard doctor for instructions)."
        )
    return duckdb.connect(str(path), read_only=True)


def search(
    con: duckdb.DuckDBPyConnection,
    aliases: list[str],
    since: str = DEFAULT_SINCE,
    until: str = DEFAULT_UNTIL,
    party: str | None = None,
    state: str | None = None,
    chamber: str | None = None,
    domain_contains: str | None = None,
    limit: int = 5000,
) -> tuple[list[dict], str]:
    """Run one regex-or'd scan over the press_releases table. Returns a list of
    match dicts (post-snippet, post-dedup) and the regex used. The limit is a
    safety valve: 5000 raw matches is far past any sensible reporter query and
    indicates the alias list is too broad.

    Filters use parameterized SQL — never f-string user input. The regex itself
    is built by build_term_regex() from caller-supplied aliases; DuckDB's
    regexp_matches uses RE2-flavored regex and is sandboxed by DuckDB."""
    regex = build_term_regex(aliases)

    where = ["date >= ?", "date <= ?", "(regexp_matches(text, ?, 'i') OR regexp_matches(title, ?, 'i'))"]
    params: list[object] = [since, until, regex, regex]

    if party:
        where.append("party = ?")
        params.append(party)
    if state:
        where.append("UPPER(state) = ?")
        params.append(state.upper())
    if chamber:
        where.append("LOWER(chamber) = ?")
        params.append(chamber.lower())
    if domain_contains:
        where.append("LOWER(domain) LIKE ?")
        params.append(f"%{domain_contains.lower()}%")

    sql = (
        "SELECT bioguide_id, member_name, party, state, chamber, "
        "date, title, url, domain, text "
        "FROM press_releases WHERE " + " AND ".join(where) + " "
        "ORDER BY date DESC LIMIT ?"
    )
    params.append(limit)

    rows = con.execute(sql, params).fetchall()
    cols = ["bioguide_id", "member_name", "party", "state", "chamber",
            "date", "title", "url", "domain", "text"]

    # De-dup on (bioguide_id, date, title): re-issued releases and cross-posts.
    seen: set[tuple] = set()
    out: list[dict] = []
    for r in rows:
        d = dict(zip(cols, r))
        key = (d["bioguide_id"], d["date"], d["title"])
        if key in seen:
            continue
        seen.add(key)
        d["snippet"] = first_snippet(d["text"], regex)
        # Body text is bulky; drop it from the output payload.
        del d["text"]
        out.append(d)
    return out, regex


# ── Case-file support ─────────────────────────────────────────────────────────


CASE_TEMPLATE = {
    "label": "Steinberg DOE clients — press release cross-ref",
    "clients": [
        {"name": "Cirba Solutions", "aliases": ["Cirba Solutions"]},
        {"name": "EnerSys", "aliases": ["EnerSys"]},
    ],
    "filters": {
        "since": "2022-01-01",
        "until": "2026-04-01",
        "party": None,
        "state": None,
        "chamber": None,
        "domain_contains": None,
    },
    "match": [
        {"lobbyist_name": "Benjamin Steinberg", "agency_short": "energy"}
    ],
}


def load_case(path: Path) -> dict:
    """Validate a case file. Required: label, clients[].name. Aliases default
    to [name] if absent. Filters default to the corpus window."""
    case = json.loads(path.read_text(encoding="utf-8"))
    if "label" not in case:
        sys.exit(f"case file missing required key: 'label'")
    if not isinstance(case.get("clients"), list) or not case["clients"]:
        sys.exit("case file requires a non-empty 'clients' list")
    for i, c in enumerate(case["clients"]):
        if "name" not in c:
            sys.exit(f"clients[{i}] missing required key: 'name'")
        if not c.get("aliases"):
            c["aliases"] = [c["name"]]
    f = case.setdefault("filters", {})
    f.setdefault("since", DEFAULT_SINCE)
    f.setdefault("until", DEFAULT_UNTIL)
    return case


def search_case(case: dict, con: duckdb.DuckDBPyConnection,
                per_client_limit: int = DEFAULT_PER_CLIENT_LIMIT) -> dict:
    """Run per-client searches and aggregate into a single report dict. We do
    per-client (rather than one big or'd regex) so each match can be attributed
    to a specific client — that's what makes the per-client tally honest."""
    f = case["filters"]
    per_client = []
    matches: list[dict] = []
    members: set[str] = set()
    for c in case["clients"]:
        hits, _regex = search(
            con, c["aliases"],
            since=f["since"], until=f["until"],
            party=f.get("party"), state=f.get("state"),
            chamber=f.get("chamber"), domain_contains=f.get("domain_contains"),
            limit=per_client_limit * 4,
        )
        hits = hits[:per_client_limit]
        for h in hits:
            h["client"] = c["name"]
            matches.append(h)
            members.add(h["bioguide_id"] or h["member_name"])
        dates = sorted([h["date"] for h in hits if h["date"]])
        per_client.append({
            "client": c["name"],
            "aliases": c["aliases"],
            "n_matches": len(hits),
            "n_distinct_members": len({h["bioguide_id"] or h["member_name"] for h in hits}),
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
        })
    matches.sort(key=lambda h: (h["date"] or ""), reverse=True)
    return {
        "case_id": case.get("case_id") or "ad-hoc",
        "label": case["label"],
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": f,
        "match": case.get("match", []),
        "n_clients": len(case["clients"]),
        "n_matches": len(matches),
        "n_distinct_members": len(members),
        "per_client": per_client,
        "matches": matches,
    }


# ── Output rendering ──────────────────────────────────────────────────────────


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"## Press-release cross-ref: {report['label']}")
    lines.append("")
    f = report["filters"]
    win = f"{f.get('since', '')} to {f.get('until', '')}"
    filt = []
    for k in ("party", "state", "chamber", "domain_contains"):
        if f.get(k):
            filt.append(f"{k}={f[k]}")
    filt_str = f" — filters: {', '.join(filt)}" if filt else ""
    lines.append(
        f"Searched Congressional press releases ({win}){filt_str} for mentions of "
        f"**{report['n_clients']}** client name(s). Found **{report['n_matches']}** "
        f"verified matches across **{report['n_distinct_members']}** distinct member(s)."
    )
    lines.append("")

    # Per-client tally
    lines.append("### Per-client tallies")
    lines.append("")
    lines.append("| Client | Mentions | Distinct members | First | Last |")
    lines.append("|--------|---------:|-----------------:|-------|------|")
    for pc in report["per_client"]:
        first = pc["first_date"] or "—"
        last = pc["last_date"] or "—"
        lines.append(
            f"| {pc['client']} | {pc['n_matches']} | {pc['n_distinct_members']} | {first} | {last} |"
        )
    lines.append("")

    # Match table
    if report["matches"]:
        lines.append("### Matches")
        lines.append("")
        lines.append("| Date | Member (Party · State · Chamber) | Title | URL | Snippet |")
        lines.append("|------|--------------------------------|-------|-----|---------|")
        for m in report["matches"]:
            party = (m.get("party") or "—")[:1]
            state = m.get("state") or "—"
            chamber = (m.get("chamber") or "—")[:1]
            member = f"{m.get('member_name') or '—'} ({party}·{state}·{chamber})"
            title = (m.get("title") or "—").replace("|", "\\|")
            url = m.get("url") or "—"
            snippet = (m.get("snippet") or "").replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {m['date']} | {member} | {title} | <{url}> | {snippet} |")
        lines.append("")
    else:
        lines.append("_No verified mentions found in the window._")
        lines.append("")

    # Framing
    lines.append("### Framing")
    lines.append("")
    lines.append(
        "These are members of Congress publicly aligning themselves with the same "
        "companies their colleagues' former staffers are paid to represent. The "
        "signal is editorial: when a member touts a project, look for the lobbying "
        "chain — and the funding chain — behind it. **None of this is wrongdoing on "
        "its face**; it becomes a story when the member sits on a committee that "
        "oversees the relevant program, when the press release is dated near a "
        "specific grant award or rulemaking, or when the same firm or staffer has "
        "an independent recorded relationship with the member's office. Cross-check "
        "every match against the lobbying registration record and the relevant "
        "committee jurisdiction before publishing a causal claim."
    )
    lines.append("")
    return "\n".join(lines)


# ── Web writes ────────────────────────────────────────────────────────────────


def _to_web_match(m: dict) -> dict:
    """Slim the match record before embedding in findings.json — the UI doesn't
    need the bioguide_id or domain (URL covers the link)."""
    return {
        "client": m.get("client"),
        "date": m.get("date"),
        "member_name": m.get("member_name"),
        "party": m.get("party"),
        "state": m.get("state"),
        "chamber": m.get("chamber"),
        "title": m.get("title"),
        "url": m.get("url"),
        "snippet": m.get("snippet"),
    }


def write_pressrel_json(report: dict) -> None:
    """Upsert this report into web/public/press_releases.json (keyed by
    case_id), parallel to how trace upserts trails.json."""
    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    existing: dict = {"reports": []}
    if PRESSREL_JSON.exists():
        try:
            existing = json.loads(PRESSREL_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {"reports": []}
    reports = [
        r for r in existing.get("reports", [])
        if r.get("case_id") != report["case_id"]
    ]
    # Cap embedded matches in the global feed — the UI shows top-5 per client.
    slim = dict(report)
    slim["matches"] = [_to_web_match(m) for m in report["matches"][:50]]
    reports.append(slim)
    reports.sort(key=lambda r: r.get("n_matches", 0), reverse=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_reports": len(reports),
        "reports": reports,
    }
    PRESSREL_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.stderr.write(f"wrote {PRESSREL_JSON} ({len(reports)} report(s))\n")


def embed_in_findings(report: dict, per_client_cap: int = 5) -> int:
    """If the report has a `match` block, attach its slim per-client matches to
    every findings.json row that matches one of the (lobbyist_name,
    agency_short) keys. Returns rows updated. Mirrors trace's embed pattern.

    The embedded structure groups matches by client so the UI can render a
    compact 'Press releases praising {client}' panel under the candidate's
    card."""
    keys = report.get("match") or []
    if not keys or not FINDINGS_JSON.exists():
        return 0
    try:
        data = json.loads(FINDINGS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    def _norm(name: str | None, agency: str | None) -> tuple[str, str]:
        return ((name or "").strip().upper(), (agency or "").strip().lower())

    wanted = {_norm(m.get("lobbyist_name"), m.get("agency_short")) for m in keys}

    # Group by client for the embedded payload.
    by_client: dict[str, list[dict]] = defaultdict(list)
    for m in report["matches"]:
        by_client[m["client"]].append(_to_web_match(m))
    grouped = [
        {
            "client": client,
            "n_matches": len(ms),
            "matches": ms[:per_client_cap],
        }
        for client, ms in by_client.items()
    ]
    grouped.sort(key=lambda g: g["n_matches"], reverse=True)
    embed_payload = {
        "case_id": report["case_id"],
        "label": report["label"],
        "generated_at": report["generated_at"],
        "n_clients_with_matches": sum(1 for g in grouped if g["n_matches"] > 0),
        "n_matches_total": report["n_matches"],
        "by_client": grouped,
    }

    updated = 0
    for f in data.get("findings", []):
        if _norm(f.get("lobbyist_name"), f.get("agency_short")) in wanted:
            f["press_releases"] = embed_payload
            updated += 1
    if updated:
        FINDINGS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stderr.write(f"embedded press-release evidence in {updated} finding row(s) of {FINDINGS_JSON}\n")
    return updated


# ── --enrich-findings mode ────────────────────────────────────────────────────


def enrich_all_findings(
    con: duckdb.DuckDBPyConnection,
    since: str = DEFAULT_SINCE,
    until: str = DEFAULT_UNTIL,
    per_client_cap: int = 5,
    top_n_findings: int = 40,
) -> tuple[int, int]:
    """Walk every finding row, extract its top-clients list, run a single
    batched scan, and attach press-release evidence per finding.

    Batching: one regex scan over press_releases for all clients across all
    findings, then dispatch matches per finding in Python. This keeps the
    runtime ~constant in the number of findings — a per-finding scan would
    take minutes.

    Returns (n_findings_updated, n_total_matches_attached)."""
    if not FINDINGS_JSON.exists():
        sys.stderr.write(f"{FINDINGS_JSON} does not exist — run /fair-guard scan first.\n")
        return 0, 0
    data = json.loads(FINDINGS_JSON.read_text(encoding="utf-8"))
    findings = data.get("findings", [])[:top_n_findings]
    if not findings:
        return 0, 0

    # Build a per-finding alias list. `top_clients_str` is " | "-separated.
    # We use the canonical name as the only alias here (no fuzzy variants) so
    # mention counts are precise; reporters who want broader matching should
    # author a case file.
    finding_clients: list[tuple[int, list[str]]] = []
    all_aliases: list[str] = []
    for idx, f in enumerate(findings):
        clients = [c.strip() for c in (f.get("top_clients_str") or "").split("|") if c.strip()]
        finding_clients.append((idx, clients))
        all_aliases.extend(clients)
    all_aliases = sorted(set(all_aliases))
    if not all_aliases:
        return 0, 0

    sys.stderr.write(
        f"enriching {len(findings)} findings with {len(all_aliases)} unique client names…\n"
    )
    all_hits, regex = search(con, all_aliases, since=since, until=until, limit=20000)
    sys.stderr.write(
        f"  one batched scan returned {len(all_hits)} de-duplicated press-release rows\n"
    )

    # For each hit, figure out which client name(s) it mentions. We re-scan
    # the snippet to find matches — cheap because snippet is ~250 chars.
    n_updated = 0
    n_attached = 0
    for idx, clients in finding_clients:
        if not clients:
            continue
        per_client: dict[str, list[dict]] = defaultdict(list)
        # Build a per-client regex for snippet attribution.
        per_client_regexes = {c: build_term_regex([c]) for c in clients}
        for hit in all_hits:
            for c, r in per_client_regexes.items():
                if re.search(r, hit.get("snippet", ""), flags=re.IGNORECASE):
                    h = dict(hit)
                    h["client"] = c
                    per_client[c].append(_to_web_match(h))
                    break  # Attribute each hit to a single client.
        if not per_client:
            continue
        grouped = [
            {
                "client": c,
                "n_matches": len(ms),
                "matches": sorted(ms, key=lambda m: m.get("date") or "", reverse=True)[:per_client_cap],
            }
            for c, ms in per_client.items()
        ]
        grouped.sort(key=lambda g: g["n_matches"], reverse=True)
        total = sum(g["n_matches"] for g in grouped)
        findings[idx]["press_releases"] = {
            "case_id": f"auto-enrich-{findings[idx].get('rank')}",
            "label": f"Auto-enriched from scan top clients",
            "generated_at": datetime.now(UTC).isoformat(),
            "n_clients_with_matches": len([g for g in grouped if g["n_matches"] > 0]),
            "n_matches_total": total,
            "by_client": grouped,
        }
        n_updated += 1
        n_attached += total

    if n_updated:
        FINDINGS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stderr.write(
            f"updated {n_updated} finding row(s) with {n_attached} total press-release matches\n"
        )
    return n_updated, n_attached


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--mention", type=str,
                    help="Ad-hoc: search for this term (word-bounded, case-insensitive).")
    ap.add_argument("--case", type=Path,
                    help="Path to a JSON case file (per-client lookup with optional match block).")
    ap.add_argument("--enrich-findings", action="store_true",
                    help="Auto cross-ref every scan-finding row's top clients against press releases.")
    ap.add_argument("--print-template", action="store_true",
                    help="Print the case-file JSON schema and exit.")

    # Filters (ad-hoc mode)
    ap.add_argument("--since", default=DEFAULT_SINCE, help=f"Start date (default {DEFAULT_SINCE}).")
    ap.add_argument("--until", default=DEFAULT_UNTIL, help=f"End date (default {DEFAULT_UNTIL}).")
    ap.add_argument("--party", help="Filter to one party (e.g. Republican, Democrat).")
    ap.add_argument("--state", help="Filter to one state postal code (e.g. CA).")
    ap.add_argument("--chamber", help="Filter to House or Senate.")
    ap.add_argument("--domain-contains", help="Substring match on member's official site domain (e.g. 'senate.gov').")
    ap.add_argument("--per-client-limit", type=int, default=DEFAULT_PER_CLIENT_LIMIT,
                    help="Cap matches per client in case-file mode.")

    # Outputs
    ap.add_argument("--out", type=Path, help="Write markdown to this path (else stdout).")
    ap.add_argument("--json", type=Path, dest="json_out", help="Also write the raw JSON payload here.")
    ap.add_argument("--no-web", action="store_true",
                    help="Skip web/public writes (CI mode).")

    args = ap.parse_args()

    # Force UTF-8 stdout (Windows cp1252 default mangles the snippet ellipses).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if args.print_template:
        print(json.dumps(CASE_TEMPLATE, indent=2))
        return 0

    if args.enrich_findings:
        with _connect() as con:
            n, total = enrich_all_findings(con, since=args.since, until=args.until)
        sys.stderr.write(f"done — {n} findings enriched, {total} total matches attached\n")
        return 0

    # Build the report.
    if args.case:
        case = load_case(args.case)
        case["case_id"] = case.get("case_id") or args.case.stem
        # Allow case-file filters to be overridden by CLI flags.
        for k, v in (("since", args.since != DEFAULT_SINCE and args.since or None),
                     ("until", args.until != DEFAULT_UNTIL and args.until or None),
                     ("party", args.party), ("state", args.state),
                     ("chamber", args.chamber), ("domain_contains", args.domain_contains)):
            if v is not None:
                case["filters"][k] = v
        with _connect() as con:
            report = search_case(case, con, per_client_limit=args.per_client_limit)
    elif args.mention:
        case = {
            "case_id": f"adhoc-{re.sub(r'[^a-z0-9]+', '-', args.mention.lower())[:40]}",
            "label": f"Ad-hoc search: {args.mention}",
            "clients": [{"name": args.mention, "aliases": [args.mention]}],
            "filters": {
                "since": args.since, "until": args.until,
                "party": args.party, "state": args.state,
                "chamber": args.chamber, "domain_contains": args.domain_contains,
            },
            "match": [],
        }
        with _connect() as con:
            report = search_case(case, con, per_client_limit=args.per_client_limit)
    else:
        ap.error("must pass one of --mention, --case, --enrich-findings, --print-template")

    md = render_markdown(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        sys.stderr.write(f"wrote {args.out}\n")
    else:
        print(md)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stderr.write(f"wrote {args.json_out}\n")

    if not args.no_web:
        write_pressrel_json(report)
        if report.get("match"):
            embed_in_findings(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
