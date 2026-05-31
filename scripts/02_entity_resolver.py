#!/usr/bin/env python3
"""
02_entity_resolver.py — Normalize messy organization and person names into
canonical clusters with provenance.

Reads `senate_filings.registrant_name`, `senate_filings.client_name`, and
`senate_lobbyists.lobbyist_name` from output/investigation.duckdb, runs the
two-stage normalize-then-fuzzy resolver, and writes the result as a single
`entity_map` table back into the DuckDB store.

Outputs (in output/investigation.duckdb):

    entity_map  (
        raw_name        VARCHAR,    -- original string as it appears in source
        entity_type     VARCHAR,    -- 'organization' | 'person'
        canonical_name  VARCHAR,    -- canonical form for the cluster
        cluster_id      VARCHAR,    -- shared by all variants of one entity
        confidence      DOUBLE,     -- 0.0–1.0
        match_method    VARCHAR,    -- 'exact' | 'normalized_exact' |
                                    --   'fuzzy_high' | 'fuzzy_low' | 'singleton'
        n_variants      INTEGER     -- # raw strings in the cluster
    )

Usage:
    uv run scripts/02_entity_resolver.py                # full run (orgs + people)
    uv run scripts/02_entity_resolver.py --orgs-only
    uv run scripts/02_entity_resolver.py --people-only
    uv run scripts/02_entity_resolver.py --threshold 92  # fuzzy cutoff
    uv run scripts/02_entity_resolver.py --dry-run       # no DB writes
    uv run scripts/02_entity_resolver.py --eval          # report F1 on held-out
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(os.environ.get("OUTPUT_ROOT", "output")) / "investigation.duckdb"

# ── Normalization ──────────────────────────────────────────────────────────────

# Legal suffixes to strip from organization names. Order matters: strip
# multi-token suffixes first. All matched at the END of the string only.
ORG_SUFFIXES = [
    r"\bL\.?\s*L\.?\s*P\.?\b",       # L.L.P., LLP
    r"\bL\.?\s*L\.?\s*C\.?\b",       # L.L.C., LLC
    r"\bP\.?\s*L\.?\s*L\.?\s*C\.?\b",  # PLLC
    r"\bP\.?\s*L\.?\s*C\.?\b",       # PLC
    r"\bP\.?\s*C\.?\b",              # P.C.
    r"\bIncorporated\b",
    r"\bCorporation\b",
    r"\bCompany\b",
    r"\bLimited\b",
    r"\bL\.?\s*P\.?\b",              # L.P.
    r"\bCorp\.?\b",
    r"\bInc\.?\b",
    r"\bLtd\.?\b",
    r"\bCo\.?\b",
    r"\bGmbH\b",
    r"\bAG\b",
    r"\bS\.?A\.?\b",
    r"\bN\.?V\.?\b",
]
ORG_SUFFIX_RE = re.compile(
    r"(?:[,.\s]+(?:" + "|".join(ORG_SUFFIXES) + r"))+\s*$",
    re.IGNORECASE,
)

# Alias markers — FKA / formerly known as / DBA / etc. Names commonly appear as
#   "INFLECTION POINT (FKA ARISTOTLE INTERNATIONAL, INC.)"
#   "ENVIRI F/K/A HARSCO CORPORATION"  (no parens; slashed abbreviation)
#   "BROOKS BAWDEN MOORE, LLC, FORMERLY REPORTED AS BROOKS BAWDEN, LLC"
#   "NOVEL STRATEGIES (FKA) PRISM GROUP"  (FKA in middle, after the new name)
# We strip the marker AND extract the aliased form as a separate variant so
# the union-find pass can link the same entity under both its current and
# former names.
#
# Regex pieces:
#   _ALIAS_KW = the keyword: FKA, F.K.A., F/K/A, FNA, formerly, formerly known as, etc.
_ALIAS_KW = (
    r"(?:"
    r"f\s*[\./]?\s*k\s*[\./]?\s*a\s*[\./]?"     # FKA / F.K.A. / F/K/A
    r"|n\s*[\./]?\s*k\s*[\./]?\s*a\s*[\./]?"    # NKA / N.K.A.
    r"|f\s*[\./]?\s*n\s*[\./]?\s*a\s*[\./]?"    # FNA / F.N.A.
    r"|d\s*[\./]?\s*b\s*[\./]?\s*a\s*[\./]?"    # DBA / D/B/A
    r"|formerly\s+known\s+as"
    r"|formerly\s+reported\s+as"
    r"|formerly"
    r"|previously\s+known\s+as"
    r"|previously"
    r"|now\s+known\s+as"
    r"|now"
    r"|the\s+former"
    r"|a\s*[\./]?\s*k\s*[\./]?\s*a\s*[\./]?"    # AKA
    r")"
)

# Parenthesized alias: "X (FKA Y)" — captures X and Y separately.
ALIAS_PAREN_RE = re.compile(
    rf"^(?P<main>.+?)\s*[\(\[]\s*{_ALIAS_KW}\s*[\)\]]?\s*(?P<alias>[^)\]]*?)\s*[\)\]]\s*(?P<tail>.*)$",
    re.IGNORECASE,
)
# Trailing-after-comma alias: "X, FKA Y" / "X formerly Y"
ALIAS_TRAIL_RE = re.compile(
    rf"^(?P<main>.+?)\s*,?\s*\b{_ALIAS_KW}\s+(?P<alias>.+)$",
    re.IGNORECASE,
)


# "on behalf of" — a registrant lobbying for a named client should also resolve
# as that client.
ON_BEHALF_RE = re.compile(
    r"^(?P<main>.+?)\s+(?:on\s+behalf\s+of|obo|o/b/o)\s+(?P<alias>.+)$",
    re.IGNORECASE,
)


def _extract_aliases_one_pass(name: str) -> list[str]:
    """Single-pass alias extraction. Internal helper for extract_org_aliases."""
    if not name:
        return []
    # 1. Parenthesized: "X (FKA Y) Z"
    m = ALIAS_PAREN_RE.match(name)
    if m:
        main_part = m.group("main").strip()
        alias = m.group("alias").strip()
        tail = m.group("tail").strip()
        # Empty alias with non-empty tail: "X (FKA) Y" means "X formerly Y".
        # Swap so the tail becomes the alias (the former name).
        if not alias and tail:
            return [main_part, tail]
        # Normal case: "X (FKA Y) Z" → main = "X Z", alias = "Y"
        main = (main_part + " " + tail).strip()
        if alias:
            return [main, alias]
        return [main]
    # 2. Trailing: "X, FKA Y"
    m = ALIAS_TRAIL_RE.match(name)
    if m:
        main = m.group("main").strip().rstrip(",")
        alias = m.group("alias").strip()
        if alias:
            return [main, alias]
        return [main]
    # 3. On-behalf-of: "X on behalf of Y" — extract both.
    m = ON_BEHALF_RE.match(name)
    if m:
        return [m.group("main").strip(), m.group("alias").strip()]
    return [name]


def extract_org_aliases(name: str, max_depth: int = 3) -> list[str]:
    """Recursively extract main + alias forms. Aliases can themselves contain
    aliases (e.g. "X (FKA Y D/B/A Z)" → ["X", "Y", "Z"]). Recurses up to
    max_depth levels to keep terminal.
    """
    if not name:
        return []
    seen: set[str] = set()
    out: list[str] = []
    stack = [(name, 0)]
    while stack:
        current, depth = stack.pop(0)
        if current in seen or depth > max_depth:
            continue
        seen.add(current)
        forms = _extract_aliases_one_pass(current)
        if len(forms) == 1 and forms[0] == current:
            out.append(current)
            continue
        for f in forms:
            stack.append((f, depth + 1))
    return out

# Common token replacements
TOKEN_NORMALIZE = {
    "and": "&",
    "&amp;": "&",
}


ORG_HONORIFIC_RE = re.compile(
    r"^(?:mr|mrs|ms|miss|dr|hon|sir|the\s+honorable|prof)\.?\s+",
    re.IGNORECASE,
)


def _normalize_org_core(name: str) -> str:
    """Inner normalizer: lowercase, strip suffixes, collapse whitespace.

    Does NOT strip alias markers — callers should pass the main-or-alias form
    extracted by extract_org_aliases. This split lets us emit one cluster
    per name variant (main and alias) rather than collapsing them.
    """
    if not name:
        return ""
    s = name
    # Strip leading honorific ("Mr.", "Dr.", "Hon.") — these appear on orgs
    # registered by an individual person (e.g., "MR. MARK REY").
    s = ORG_HONORIFIC_RE.sub("", s)
    s = s.lower()
    s = s.replace("&amp;", "&")
    # Normalize "&" by always surrounding with a single space so tokenization
    # behaves the same for "park & k" and "park&k".
    s = re.sub(r"\s*&\s*", " & ", s)
    for _ in range(3):
        new = ORG_SUFFIX_RE.sub("", s).strip(" ,.;")
        if new == s:
            break
        s = new
    if s.startswith("the "):
        s = s[4:]
    s = re.sub(r"[^a-z0-9&]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_org(name: str) -> str:
    """Public normalizer: extract alias forms and return the main normalized
    form. The first form is the "current name" (or the only name if no alias
    marker was present). For full multi-form behavior callers should use
    extract_org_aliases() directly.
    """
    if not name:
        return ""
    forms = extract_org_aliases(name)
    return _normalize_org_core(forms[0]) if forms else ""


# ── Person name normalization ──────────────────────────────────────────────────

# Suffixes that don't change identity
PERSON_SUFFIXES = re.compile(
    r"\s*,?\s*(?:jr\.?|sr\.?|ii|iii|iv|v|esq\.?|md|phd|j\.?d\.?)\b\.?$",
    re.IGNORECASE,
)
# Titles to strip
PERSON_PREFIXES = re.compile(
    r"^(?:mr\.?|mrs\.?|ms\.?|miss|dr\.?|hon\.?|prof\.?|sir|the\s+honorable)\s+",
    re.IGNORECASE,
)


def normalize_person(name: str) -> tuple[str, str, str]:
    """Return (last, first, middle_initial) for a person name.

    Handles both "Smith, John A." and "John A. Smith" formats.
    """
    if not name:
        return ("", "", "")
    s = name.strip()
    s = PERSON_PREFIXES.sub("", s)
    s = PERSON_SUFFIXES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    if "," in s:
        # "Smith, John A." form
        parts = s.split(",", 1)
        last = parts[0].strip().lower()
        rest = parts[1].strip().split() if len(parts) > 1 else []
    else:
        # "John A. Smith" form (or just "John Smith")
        tokens = s.split()
        if len(tokens) == 1:
            return (tokens[0].lower(), "", "")
        last = tokens[-1].lower()
        rest = tokens[:-1]
    first = rest[0].lower() if rest else ""
    middle = ""
    if len(rest) > 1:
        m = rest[1].strip(".")
        middle = m[0].lower() if m else ""
    # strip trailing punct
    last = re.sub(r"[^a-z\-']", "", last)
    first = re.sub(r"[^a-z\-']", "", first)
    return (last, first, middle)


# ── Resolution ────────────────────────────────────────────────────────────────

class UnionFind:
    """Tiny union-find for clustering raw → canonical IDs."""
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def resolve_orgs(
    raw_names: list[str],
    threshold: int = 92,
) -> list[dict]:
    """Resolve a list of organization names into clusters.

    Algorithm:
      1. Group by normalized form (exact-after-normalization → free wins).
      2. Within each first-token block, fuzzy-pair using token_sort_ratio
         at the given threshold.
      3. Cluster via union-find; pick most frequent raw spelling as canonical.

    Returns a list of {raw_name, canonical_name, cluster_id, confidence,
    match_method, n_variants} dicts (one per raw input).
    """
    # Step 1: for each raw name, emit one or more normalized forms (the main
    # form plus any FKA aliases). Each form maps back to its raw name. If a
    # raw has two forms, both forms get unioned immediately so they share a
    # cluster regardless of what else later joins them.
    by_norm: dict[str, list[str]] = defaultdict(list)
    raw_to_norms: dict[str, list[str]] = {}
    for raw in raw_names:
        if not raw:
            continue
        forms = extract_org_aliases(raw)
        norms = [n for n in (_normalize_org_core(f) for f in forms) if n]
        if not norms:
            continue
        # Deduplicate but preserve order
        seen = set()
        norms = [n for n in norms if not (n in seen or seen.add(n))]
        raw_to_norms[raw] = norms
        for n in norms:
            by_norm[n].append(raw)

    uf = UnionFind()
    norm_keys = list(by_norm.keys())

    # Initialize: every normalized form is its own cluster
    for k in norm_keys:
        uf.find(k)

    # Immediate union: forms emitted from the SAME raw name (main + alias) are
    # by definition the same entity.
    for raw, norms in raw_to_norms.items():
        if len(norms) > 1:
            for n in norms[1:]:
                uf.union(norms[0], n)

    # Step 2: block by first token, fuzzy-pair within block
    by_block: dict[str, list[str]] = defaultdict(list)
    for k in norm_keys:
        tok = k.split(" ", 1)[0] if k else ""
        if tok:
            by_block[tok].append(k)

    for tok, members in by_block.items():
        if len(members) < 2:
            continue
        # O(b^2) within block — fine because blocks are small
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                # quick length sanity
                if abs(len(a) - len(b)) > max(len(a), len(b)) // 2:
                    continue
                score = fuzz.token_sort_ratio(a, b)
                if score >= threshold:
                    uf.union(a, b)

    # Step 3: collect clusters
    clusters: dict[str, list[str]] = defaultdict(list)  # canonical-norm → [norm…]
    for k in norm_keys:
        clusters[uf.find(k)].append(k)

    # Pick canonical raw spelling per cluster: the most frequent raw name
    out: list[dict] = []
    for cluster_root, norms in clusters.items():
        # gather all raw spellings under this cluster
        raws: list[str] = []
        for n in norms:
            raws.extend(by_norm[n])
        # most common raw spelling wins as canonical display
        canonical_raw = Counter(raws).most_common(1)[0][0]
        cluster_id = "org:" + hashlib.md5(cluster_root.encode("utf-8")).hexdigest()[:12]
        n_variants = len(set(raws))
        for raw in set(raws):
            norm = normalize_org(raw)
            # determine match_method
            if raw == canonical_raw:
                method = "exact" if n_variants == 1 else "normalized_exact"
            elif norm == normalize_org(canonical_raw):
                method = "normalized_exact"
                confidence = 1.0
            else:
                # fuzzy-joined
                score = fuzz.token_sort_ratio(norm, normalize_org(canonical_raw))
                method = "fuzzy_high" if score >= 95 else "fuzzy_low"
            # confidence
            if method in ("exact", "normalized_exact"):
                confidence = 1.0
            elif method == "fuzzy_high":
                confidence = 0.95
            else:
                confidence = max(0.5, fuzz.token_sort_ratio(norm, normalize_org(canonical_raw)) / 100)
            if n_variants == 1:
                method = "singleton"
                confidence = 1.0
            out.append({
                "raw_name": raw,
                "entity_type": "organization",
                "canonical_name": canonical_raw,
                "cluster_id": cluster_id,
                "confidence": round(confidence, 4),
                "match_method": method,
                "n_variants": n_variants,
            })
    return out


def resolve_people(
    raw_names: list[str],
    threshold: int = 95,
) -> list[dict]:
    """Resolve a list of person names into clusters.

    Algorithm:
      1. Normalize each name to (last, first, middle_initial).
      2. Block by (last_name, first_initial). Within block, exact match on
         (last, first) clusters immediately. Fuzzy match on last name (≥ 95)
         WITH matching first initial joins clusters too.
    """
    parsed = []
    for raw in raw_names:
        if not raw:
            continue
        last, first, mid = normalize_person(raw)
        if last:
            parsed.append((raw, last, first, mid))

    uf = UnionFind()
    keys = [f"{last}|{first}|{mid}" for _, last, first, mid in parsed]
    for k in keys:
        uf.find(k)
    # union same (last, first) regardless of middle initial
    by_lastfirst: dict[tuple[str, str], list[str]] = defaultdict(list)
    for k, (_, last, first, mid) in zip(keys, parsed):
        by_lastfirst[(last, first)].append(k)
    for ks in by_lastfirst.values():
        if len(ks) < 2:
            continue
        for k in ks[1:]:
            uf.union(ks[0], k)

    # Fuzzy last-name pass — only joins where (first_initial, fuzzy_last) match
    # but the EXACT (last, first) pair already differs. We use it to catch
    # spelling variants of the last name (Smith / Smyth) under the same person.
    # We never merge two distinct (last, first) pairs that are already exact —
    # those represent different people and must stay apart.
    by_initial: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for k, (_, last, first, mid) in zip(keys, parsed):
        if first and last:
            by_initial[first[0]].append((k, last, first))

    for init, members in by_initial.items():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                k_i, last_i, first_i = members[i]
                k_j, last_j, first_j = members[j]
                # If first names AND last names match exactly, the earlier
                # by_lastfirst pass already unioned them.
                # If first names differ, they're different people — never union.
                if first_i != first_j:
                    continue
                # Same first name but DIFFERENT last names → maybe a spelling
                # variant. Apply fuzzy threshold.
                if last_i == last_j:
                    continue  # exact same — already unioned
                if abs(len(last_i) - len(last_j)) > 2:
                    continue
                if fuzz.ratio(last_i, last_j) >= threshold:
                    uf.union(k_i, k_j)

    # collect clusters
    clusters: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for k, (raw, last, first, mid) in zip(keys, parsed):
        clusters[uf.find(k)].append((raw, last, first, mid))

    out: list[dict] = []
    for cluster_root, members in clusters.items():
        raws = [m[0] for m in members]
        canonical_raw = Counter(raws).most_common(1)[0][0]
        cluster_id = "person:" + hashlib.md5(cluster_root.encode("utf-8")).hexdigest()[:12]
        n_variants = len(set(raws))
        canonical_norm = normalize_person(canonical_raw)
        for raw, last, first, mid in members:
            if raw == canonical_raw:
                method = "exact" if n_variants == 1 else "normalized_exact"
                confidence = 1.0
            elif (last, first) == (canonical_norm[0], canonical_norm[1]):
                method = "normalized_exact"
                confidence = 1.0
            else:
                score = fuzz.ratio(last, canonical_norm[0])
                method = "fuzzy_high" if score >= 97 else "fuzzy_low"
                confidence = max(0.5, score / 100)
            if n_variants == 1:
                method = "singleton"
                confidence = 1.0
            out.append({
                "raw_name": raw,
                "entity_type": "person",
                "canonical_name": canonical_raw,
                "cluster_id": cluster_id,
                "confidence": round(confidence, 4),
                "match_method": method,
                "n_variants": n_variants,
            })
    # dedupe rows (a raw name appearing twice with same cluster)
    seen = set()
    unique_out = []
    for r in out:
        k = (r["raw_name"], r["cluster_id"])
        if k in seen:
            continue
        seen.add(k)
        unique_out.append(r)
    return unique_out


# ── DB I/O ─────────────────────────────────────────────────────────────────────

def fetch_raw_orgs(con: duckdb.DuckDBPyConnection) -> list[str]:
    """All distinct registrant_name and client_name strings from Senate filings."""
    rows = con.execute("""
        SELECT DISTINCT name FROM (
            SELECT registrant_name AS name FROM senate_filings WHERE registrant_name IS NOT NULL
            UNION
            SELECT client_name    AS name FROM senate_filings WHERE client_name    IS NOT NULL
            UNION
            SELECT org_name       AS name FROM house_filings  WHERE org_name       IS NOT NULL
            UNION
            SELECT client_name    AS name FROM house_filings  WHERE client_name    IS NOT NULL
        )
    """).fetchall()
    return [r[0] for r in rows]


def fetch_raw_people(con: duckdb.DuckDBPyConnection) -> list[str]:
    """All distinct lobbyist names from Senate and House."""
    rows = con.execute("""
        SELECT DISTINCT name FROM (
            SELECT lobbyist_name AS name FROM senate_lobbyists WHERE lobbyist_name IS NOT NULL
            UNION
            SELECT lobbyist_name AS name FROM house_lobbyists  WHERE lobbyist_name IS NOT NULL
        )
    """).fetchall()
    return [r[0] for r in rows]


def write_entity_map(con: duckdb.DuckDBPyConnection, mappings: list[dict]) -> None:
    """Write the resolver output into a fresh entity_map table.

    Drops and recreates the table — entity resolution is a full-corpus operation.
    """
    con.execute("DROP TABLE IF EXISTS entity_map")
    con.execute("""
        CREATE TABLE entity_map (
            raw_name        VARCHAR,
            entity_type     VARCHAR,
            canonical_name  VARCHAR,
            cluster_id      VARCHAR,
            confidence      DOUBLE,
            match_method    VARCHAR,
            n_variants      INTEGER
        )
    """)
    # bulk insert via DataFrame for speed
    import polars as pl
    df = pl.DataFrame(mappings)
    con.register("df_view", df)
    con.execute("INSERT INTO entity_map SELECT * FROM df_view")
    con.execute("CREATE INDEX idx_entity_raw ON entity_map(raw_name)")
    con.execute("CREATE INDEX idx_entity_cluster ON entity_map(cluster_id)")


def print_summary(mappings: list[dict]) -> None:
    by_method = Counter(m["match_method"] for m in mappings)
    by_type = Counter(m["entity_type"] for m in mappings)
    n_clusters = len({m["cluster_id"] for m in mappings})
    print()
    print(f"  Total raw rows:        {len(mappings):>10,}")
    print(f"  Unique clusters:       {n_clusters:>10,}")
    print(f"  Compression ratio:     {len(mappings) / max(n_clusters, 1):>10.2f}x")
    print("  Entity types:")
    for t, n in by_type.most_common():
        print(f"    {t:<15} {n:>10,}")
    print("  Match methods:")
    for m, n in by_method.most_common():
        print(f"    {m:<20} {n:>10,}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--orgs-only", action="store_true")
    p.add_argument("--people-only", action="store_true")
    p.add_argument("--threshold", type=int, default=92, help="Fuzzy match threshold for orgs (default 92)")
    p.add_argument("--person-threshold", type=int, default=95, help="Fuzzy match threshold for persons (default 95)")
    p.add_argument("--dry-run", action="store_true", help="Skip DB write")
    p.add_argument("--limit", type=int, default=None, help="Limit raw input rows for fast testing")
    args = p.parse_args()

    if not DB_PATH.exists():
        sys.exit(f"DB not found: {DB_PATH}. Run /fair-guard index first or download pre-built output/.")

    print("=" * 60)
    print("FairGuard — entity resolver")
    print("=" * 60)
    print(f"DB: {DB_PATH}")

    con = duckdb.connect(str(DB_PATH))  # not read_only — need to write entity_map

    mappings: list[dict] = []

    if not args.people_only:
        print("\nResolving organizations…")
        raw_orgs = fetch_raw_orgs(con)
        if args.limit:
            raw_orgs = raw_orgs[:args.limit]
        print(f"  Pulled {len(raw_orgs):,} distinct org strings")
        org_map = resolve_orgs(raw_orgs, threshold=args.threshold)
        print(f"  → {len({m['cluster_id'] for m in org_map}):,} clusters")
        mappings.extend(org_map)

    if not args.orgs_only:
        print("\nResolving people…")
        raw_people = fetch_raw_people(con)
        if args.limit:
            raw_people = raw_people[:args.limit]
        print(f"  Pulled {len(raw_people):,} distinct person strings")
        person_map = resolve_people(raw_people, threshold=args.person_threshold)
        print(f"  → {len({m['cluster_id'] for m in person_map}):,} clusters")
        mappings.extend(person_map)

    print_summary(mappings)

    if args.dry_run:
        print("\n[--dry-run] skipping DB write")
        return

    print("\nWriting entity_map…")
    write_entity_map(con, mappings)
    n = con.execute("SELECT COUNT(*) FROM entity_map").fetchone()[0]
    print(f"  entity_map row count: {n:,}")
    con.close()


if __name__ == "__main__":
    main()
