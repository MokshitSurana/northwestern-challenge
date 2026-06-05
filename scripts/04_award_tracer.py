#!/usr/bin/env python3
"""
04_award_tracer.py — Follow the money behind a revolving-door case.

Given a lobbyist, their client list, and the federal agency they target, this
queries USAspending.gov for the federal awards each client received from that
agency, verifies every row against the recipient's real name (the API's recipient
search is fuzzy), and emits a journalism-ready markdown table plus a framing note
that separates *discretionary* awards (competitive grants — newsworthy) from
*routine* program participation (commodity purchases, food aid, formula financing).

This is the "follow the money" companion to revolving-door-detector: scan finds the
structural pattern (a former official lobbying their old agency), this skill traces
whether that agency is steering real dollars to the lobbyist's clients.

Why a dedicated skill: the USAspending API has three gotchas that a fresh agent gets
wrong every time, all of which are handled here —
  1. `award_type_codes` must all come from ONE group per request (mixing grants +
     loans returns HTTP 422). We query each requested group separately and combine.
  2. Loan awards have no "Award Amount" sort field (HTTP 400), so loans are sorted
     by recipient name and flagged; by default loans are excluded for a conservative
     total.
  3. `recipient_search_text` is FUZZY — "Cargill" also returns "Paseo Cargill Energy".
     Every row is filtered against caller-supplied name tokens before it counts.

Usage:
    uv run scripts/04_award_tracer.py --case path/to/case.json
    uv run scripts/04_award_tracer.py --case case.json --out notes/money_trail.md
    uv run scripts/04_award_tracer.py --case case.json --json out.json
    uv run scripts/04_award_tracer.py --print-template   # show the case-file schema

Case file schema (JSON):
    {
      "lobbyist": "Bryson Steinberg",
      "agency":   "Department of Energy",       # USAspending toptier agency name
      "award_groups": ["grants"],               # any of: grants contracts direct loans
      "time_period": {"start": "2021-01-01", "end": "2026-06-04"},   # optional
      "clients": [
        {
          "label":       "Cirba Solutions",        # display name in the table
          "search":      "Cirba Solutions",        # recipient_search_text (fuzzy)
          "name_tokens": ["CIRBA SOLUTIONS"]       # row kept only if one appears in
        }                                          #   the real Recipient Name (UPPER)
      ]
    }

Not a database skill — it makes live HTTPS calls to api.usaspending.gov and needs
network access. Figures are reproducible from the committed case files in
skill/federal-award-tracer/cases/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Award-type-code groups. Every USAspending request must use codes from ONE group.
AWARD_GROUPS: dict[str, list[str]] = {
    "grants": ["02", "03", "04", "05"],   # block / formula / project grants, coop agreements
    "contracts": ["A", "B", "C", "D"],    # definitive contract / purchase order / etc.
    "direct": ["06", "10"],               # direct payment / other financial assistance
    "loans": ["07", "08"],                # direct loan / guaranteed loan
}

# Award-amount sort is unavailable for loans; sort those by recipient instead.
_NO_AMOUNT_SORT = {"loans"}

FIELDS = [
    "Award ID",
    "Recipient Name",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Award Type",
    "Description",
    "Start Date",
]

# Sub-agency / program signals that mark dollars as ROUTINE program participation
# rather than discretionary, competitively-awarded grants. These are heuristics to
# steer the framing note — always confirm before publishing.
ROUTINE_SUBAGENCY_SIGNALS = [
    "agricultural marketing service",        # AMS commodity purchases
    "foreign agricultural service",          # FAS food aid / export programs
    "farm service agency",                   # FSA commodity & loan programs
    "commodity credit corporation",          # CCC price support
    "rural utilities service",               # RUS infrastructure financing
    "rural housing service",
    "rural business",
    "food and nutrition service",            # FNS nutrition formula programs
]


def _post(body: dict) -> dict:
    """POST to USAspending with retry/backoff on transient errors."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        API, data=data, headers={"Content-Type": "application/json"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            sys.stderr.write(f"HTTP {e.code}: {e.read()[:300]!r}\n")
            return {"results": []}
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            sys.stderr.write(f"network error: {e}\n")
            return {"results": []}
    return {"results": []}


def query(search: str, agency: str, group: str,
          start: str, end: str, limit: int = 100) -> list[dict]:
    """Return award rows for one recipient-search / agency / award-type group."""
    codes = AWARD_GROUPS[group]
    body = {
        "filters": {
            "recipient_search_text": [search],
            "award_type_codes": codes,
            "time_period": [{"start_date": start, "end_date": end}],
            "agencies": [{"type": "awarding", "tier": "toptier", "name": agency}],
        },
        "fields": FIELDS,
        "limit": limit,
    }
    if group in _NO_AMOUNT_SORT:
        body["sort"] = "Recipient Name"
        body["order"] = "asc"
    else:
        body["sort"] = "Award Amount"
        body["order"] = "desc"
    return _post(body).get("results", [])


def trace_client(client: dict, agency: str, groups: list[str],
                 start: str, end: str) -> dict:
    """Sum a client's awards across the requested groups, keeping only rows whose
    real Recipient Name contains one of the client's name tokens. De-dupes by Award
    ID. Returns a per-client summary dict."""
    tokens = [t.upper() for t in client["name_tokens"]]
    seen: dict[str, dict] = {}
    for group in groups:
        for r in query(client["search"], agency, group, start, end):
            recip = (r.get("Recipient Name") or "").upper()
            if not any(t in recip for t in tokens):
                continue
            award_id = r.get("Award ID") or f"{group}:{recip}:{r.get('Award Amount')}"
            seen[award_id] = {
                "amount": r.get("Award Amount") or 0,
                "recipient": r.get("Recipient Name"),
                "subagency": r.get("Awarding Sub Agency") or "",
                "award_type": r.get("Award Type") or "",
                "description": (r.get("Description") or "")[:120],
            }
        time.sleep(0.25)
    total = sum(v["amount"] for v in seen.values())
    routine_amt = sum(
        v["amount"] for v in seen.values()
        if any(sig in v["subagency"].lower() for sig in ROUTINE_SUBAGENCY_SIGNALS)
    )
    return {
        "label": client["label"],
        "total": total,
        "n_awards": len(seen),
        "recipients": sorted({v["recipient"] for v in seen.values()}),
        "routine_amount": routine_amt,
        "discretionary_amount": total - routine_amt,
        "awards": sorted(seen.values(), key=lambda v: v["amount"], reverse=True),
    }


def fmt_usd(x: float) -> str:
    return f"${x:,.0f}"


def build_markdown(case: dict, results: list[dict]) -> str:
    """Render the journalism-ready table + framing note."""
    results = sorted(results, key=lambda r: r["total"], reverse=True)
    hits = [r for r in results if r["total"] > 0]
    grand = sum(r["total"] for r in hits)
    routine = sum(r["routine_amount"] for r in hits)
    discretionary = grand - routine
    groups = ", ".join(case["award_groups"])

    lines: list[str] = []
    lines.append(f"## Money trail: {case['lobbyist']} → {case['agency']}")
    lines.append("")
    lines.append(
        f"Federal {groups} awarded by **{case['agency']}** to "
        f"{case['lobbyist']}'s lobbying clients, verified by recipient name against "
        f"USAspending.gov. Loans are {'included' if 'loans' in case['award_groups'] else 'excluded'} "
        "(conservative)."
    )
    lines.append("")
    lines.append("| Client | Verified total | Awards | Recipient name(s) on file |")
    lines.append("|--------|---------------:|-------:|---------------------------|")
    for r in hits:
        recips = "; ".join(r["recipients"])
        lines.append(
            f"| {r['label']} | {fmt_usd(r['total'])} | {r['n_awards']} | {recips} |"
        )
    lines.append(f"| **TOTAL** | **{fmt_usd(grand)}** | | |")
    lines.append("")

    misses = [r["label"] for r in results if r["total"] <= 0]
    if misses:
        lines.append(f"*No verified {case['agency']} {groups} found for: "
                     + ", ".join(misses) + ".*")
        lines.append("")

    # Framing note: discretionary vs routine.
    lines.append("### Framing")
    lines.append("")
    if grand > 0:
        pct_disc = 100 * discretionary / grand
        if routine <= 0:
            lines.append(
                f"All {fmt_usd(grand)} traced flows through programs that are "
                "*not* obviously routine — none of it through sub-agencies that "
                "typically administer formula / commodity / financing programs "
                "(e.g. AMS commodity purchases, FAS food aid, RUS financing)."
            )
        else:
            lines.append(
                f"Of the {fmt_usd(grand)} traced, {fmt_usd(discretionary)} "
                f"(about {pct_disc:.0f}%) flows through programs that are *not* "
                "obviously routine, while "
                f"{fmt_usd(routine)} flows through sub-agencies that typically "
                "administer formula / commodity / financing programs "
                "(e.g. AMS commodity purchases, FAS food aid, RUS financing)."
            )
    lines.append("")
    lines.append(
        "**Report this as conflict-of-interest *structure*, not proven wrongdoing.** "
        "Discretionary, competitively-awarded grants from the former official's agency "
        "to that official's clients are the newsworthy core; routine program "
        "participation is context. Confirm each award's program type, the cooling-off "
        "status (18 USC §207), and seek comment before publishing a causal claim."
    )
    lines.append("")

    # Routine-signal callouts so the reporter can audit the split.
    flagged = [r for r in hits if r["routine_amount"] > 0]
    if flagged:
        lines.append("<details><summary>Routine-program signals detected</summary>")
        lines.append("")
        for r in flagged:
            subs = sorted({
                a["subagency"] for a in r["awards"]
                if any(s in a["subagency"].lower() for s in ROUTINE_SUBAGENCY_SIGNALS)
            })
            lines.append(f"- **{r['label']}**: {fmt_usd(r['routine_amount'])} via "
                         + "; ".join(subs))
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


CASE_TEMPLATE = {
    "lobbyist": "Bryson Steinberg",
    "agency": "Department of Energy",
    "award_groups": ["grants"],
    "time_period": {"start": "2021-01-01", "end": "2026-06-04"},
    "clients": [
        {
            "label": "Cirba Solutions",
            "search": "Cirba Solutions",
            "name_tokens": ["CIRBA SOLUTIONS"],
        },
        {
            "label": "EnerSys",
            "search": "EnerSys",
            "name_tokens": ["ENERSYS"],
        },
    ],
}


def load_case(path: Path) -> dict:
    case = json.loads(path.read_text(encoding="utf-8"))
    for key in ("lobbyist", "agency", "award_groups", "clients"):
        if key not in case:
            sys.exit(f"case file missing required key: {key!r}")
    bad = [g for g in case["award_groups"] if g not in AWARD_GROUPS]
    if bad:
        sys.exit(f"unknown award_groups {bad}; valid: {sorted(AWARD_GROUPS)}")
    for c in case["clients"]:
        for key in ("label", "search", "name_tokens"):
            if key not in c:
                sys.exit(f"client {c} missing required key: {key!r}")
    return case


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", type=Path, help="path to a case JSON file")
    ap.add_argument("--out", type=Path, help="write markdown to this file (else stdout)")
    ap.add_argument("--json", type=Path, dest="json_out",
                    help="also write the raw per-client results as JSON here")
    ap.add_argument("--print-template", action="store_true",
                    help="print the case-file JSON schema and exit")
    args = ap.parse_args()

    # Windows consoles default to cp1252, which can't encode "→"/"§". Force UTF-8
    # so the markdown prints identically on every platform.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if args.print_template:
        print(json.dumps(CASE_TEMPLATE, indent=2))
        return 0
    if not args.case:
        ap.error("--case is required (or use --print-template)")

    case = load_case(args.case)
    tp = case.get("time_period", {})
    start = tp.get("start", "2021-01-01")
    end = tp.get("end", "2026-06-04")

    results = [
        trace_client(c, case["agency"], case["award_groups"], start, end)
        for c in case["clients"]
    ]
    md = build_markdown(case, results)

    if args.out:
        args.out.write_text(md, encoding="utf-8")
        sys.stderr.write(f"wrote {args.out}\n")
    else:
        print(md)

    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        sys.stderr.write(f"wrote {args.json_out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
