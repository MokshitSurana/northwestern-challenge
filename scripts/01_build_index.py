#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
01_build_index.py — ETL pipeline for the Northwestern journalism challenge.

Reads Senate LDA JSON, House LDA XML, and congressional press releases,
writes flat Parquet files per source chunk, then loads everything into
a single DuckDB file (investigation.duckdb) for fast querying.

Usage:
    uv run scripts/01_build_index.py              # full build (~30-90 min)
    uv run scripts/01_build_index.py --sample     # one quarter each (~2 min)
    uv run scripts/01_build_index.py --parquet-only  # skip DuckDB step
    uv run scripts/01_build_index.py --duckdb-only   # rebuild DB from existing Parquet

Environment variables:
    DATA_ROOT    path to data root directory (default: data/data)
    OUTPUT_ROOT  path for output files      (default: output)
"""

import argparse
import os
import sys
import time
from pathlib import Path

import orjson
import polars as pl
from lxml import etree
from tqdm import tqdm

# ── Paths ──────────────────────────────────────────────────────────────────────

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "output"))
PARQUET_DIR = OUTPUT_ROOT / "parquet"
DB_PATH     = OUTPUT_ROOT / "investigation.duckdb"

PRESS_ROOT  = DATA_ROOT / "congress_press"
SENATE_ROOT = DATA_ROOT / "senate"
HOUSE_ROOT  = DATA_ROOT / "house"

# ── Helpers ────────────────────────────────────────────────────────────────────

def safe_float(val) -> float | None:
    try:
        return float(val) if val not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_money(val) -> float | None:
    """Strip $, commas from a money string and return float."""
    if not val:
        return None
    cleaned = str(val).replace("$", "").replace(",", "").strip()
    return safe_float(cleaned)


def _date_to_quarter(date_str: str | None) -> str | None:
    """'2025-04-15' -> '2025-Q2'. Returns None if unparseable."""
    if not date_str:
        return None
    try:
        y, m = int(date_str[:4]), int(date_str[5:7])
        q = (m - 1) // 3 + 1
        return f"{y}-Q{q}"
    except Exception:
        return None


def write_parquet(records: list[dict], path: Path, label: str,
                  schema_overrides: dict | None = None) -> int:
    """Write list-of-dicts to a Parquet file. Returns row count."""
    if not records:
        print(f"    [skip] {label}: 0 records")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(
        records,
        infer_schema_length=min(len(records), 500),
        schema_overrides=schema_overrides or {},
    )
    df.write_parquet(path, compression="zstd")
    size_kb = path.stat().st_size // 1024
    print(f"    [ok]   {label}: {len(df):,} rows  ({size_kb:,} KB)")
    return len(df)


# ── Press releases ─────────────────────────────────────────────────────────────

def parse_press_file(path: Path) -> list[dict]:
    records = []
    source_path = str(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = orjson.loads(line)
            except Exception:
                continue
            member = rec.get("member") or {}
            records.append({
                "bioguide_id":  safe_str(member.get("bioguide_id")),
                "member_name":  safe_str(member.get("name")),
                "party":        safe_str(member.get("party")),
                "state":        safe_str(member.get("state")),
                "chamber":      safe_str(member.get("chamber")),
                "date":         safe_str(rec.get("date")),
                # Derived quarter — avoids reparsing 200K dates in every query
                "filing_quarter": _date_to_quarter(safe_str(rec.get("date"))),
                "title":        safe_str(rec.get("title")),
                "url":          safe_str(rec.get("url")),
                "domain":       safe_str(rec.get("domain")),
                "text":         safe_str(rec.get("text")),
                "source_path":  source_path,
            })
    return records


def build_press_index(sample: bool = False) -> int:
    print("\n── Press releases ──────────────────────────────────────────────────")
    total = 0

    # 2026 files sit at the root of congress_press/
    root_files = sorted(PRESS_ROOT.glob("*.jsonl"))
    if sample:
        root_files = root_files[:1]
    for path in root_files:
        recs = parse_press_file(path)
        total += write_parquet(recs, PARQUET_DIR / f"press_{path.stem}.parquet", path.stem)

    # 2022-2025 live in year subdirs
    years = [2025] if sample else [2022, 2023, 2024, 2025]
    for year in years:
        year_dir = PRESS_ROOT / str(year)
        if not year_dir.exists():
            continue
        paths = sorted(year_dir.glob("*.jsonl"))
        if sample:
            paths = paths[:1]
        for path in paths:
            recs = parse_press_file(path)
            total += write_parquet(recs, PARQUET_DIR / f"press_{path.stem}.parquet", path.stem)

    print(f"  Total press rows: {total:,}")
    return total


# ── Senate LDA ─────────────────────────────────────────────────────────────────

def parse_senate_filings_file(path: Path):
    """Parse one senate filings JSON → 5 lists of flat dicts."""
    source_path = str(path)
    size_mb = path.stat().st_size / 1e6
    print(f"  Loading {path.name}  ({size_mb:.0f} MB)…")
    t0 = time.time()
    with open(path, "rb") as f:
        data = orjson.loads(f.read())
    print(f"  Loaded {len(data):,} filings in {time.time()-t0:.1f}s")

    filings, activities, lobbyists, gov_entities, foreign_entities = [], [], [], [], []

    for filing in tqdm(data, desc="  Parsing", leave=False, unit="filing"):
        uuid       = safe_str(filing.get("filing_uuid"))
        registrant = filing.get("registrant") or {}
        client     = filing.get("client") or {}

        filings.append({
            "filing_uuid":            uuid,
            "filing_type":            safe_str(filing.get("filing_type")),
            "filing_type_display":    safe_str(filing.get("filing_type_display")),
            "filing_year":            filing.get("filing_year"),
            "filing_period":          safe_str(filing.get("filing_period")),
            "filing_period_display":  safe_str(filing.get("filing_period_display")),
            "income":                 safe_float(filing.get("income")),
            "expenses":               safe_float(filing.get("expenses")),
            "dt_posted":              safe_str(filing.get("dt_posted")),
            "registrant_id":          safe_str(registrant.get("id")),
            "registrant_name":        safe_str(registrant.get("name")),
            "registrant_description": safe_str(registrant.get("description")),
            "registrant_country":     safe_str(filing.get("registrant_country")),
            "registrant_state":       safe_str(filing.get("registrant_state")),
            "client_id":              safe_str(client.get("id")),
            "client_name":            safe_str(client.get("name")),
            "client_description":     safe_str(client.get("description")),
            "source_path":            source_path,
        })

        for act_idx, act in enumerate(filing.get("lobbying_activities") or []):
            activities.append({
                "filing_uuid":         uuid,
                "activity_idx":        act_idx,
                "general_issue_code":  safe_str(act.get("general_issue_code")),
                "description":         safe_str(act.get("description")),
                "source_path":         source_path,
            })
            for lob in act.get("lobbyists") or []:
                if not isinstance(lob, dict):
                    continue
                # Senate JSON: name is nested under lob["lobbyist"]["first_name"/"last_name"]
                lob_obj   = lob.get("lobbyist") or {}
                first     = safe_str(lob_obj.get("first_name"))
                last      = safe_str(lob_obj.get("last_name"))
                lob_name  = " ".join(filter(None, [first, last])) or None
                lobbyists.append({
                    "filing_uuid":      uuid,
                    "activity_idx":     act_idx,
                    "lobbyist_name":    lob_name,
                    "covered_position": safe_str(lob.get("covered_position")),
                    # Senate parser
                    "is_new": safe_str(lob.get("new")),
                    "source_path":      source_path,
                })
            for ge in act.get("government_entities") or []:
                if not isinstance(ge, dict):
                    continue
                gov_entities.append({
                    "filing_uuid":  uuid,
                    "activity_idx": act_idx,
                    "entity_name":  safe_str(ge.get("name")),
                    "source_path":  source_path,
                })

        for fe in filing.get("foreign_entities") or []:
            if not isinstance(fe, dict):
                continue
            foreign_entities.append({
                "filing_uuid":  uuid,
                "entity_name":  safe_str(fe.get("name")),
                "country":      safe_str(fe.get("country")),
                "ppb_country":  safe_str(fe.get("ppb_country")),
                "source_path":  source_path,
            })

    return filings, activities, lobbyists, gov_entities, foreign_entities


def parse_senate_contributions_file(path: Path, year: int) -> list[dict]:
    source_path = str(path)
    print(f"  Loading contributions {year}…")
    with open(path, "rb") as f:
        data = orjson.loads(f.read())
    rows = []
    for c in data:
        uuid       = safe_str(c.get("filing_uuid"))
        registrant = c.get("registrant") or {}
        for item in c.get("contribution_items") or []:
            if not isinstance(item, dict):
                continue
            rows.append({
                "filing_uuid":      uuid,
                "filer_type":       safe_str(c.get("filer_type")),
                "registrant_name":  safe_str(registrant.get("name")),
                "filing_year":      year,
                "item_type":        safe_str(item.get("type")),
                "amount":           safe_float(item.get("amount")),
                "payee":            safe_str(item.get("payee")),
                "honoree":          safe_str(item.get("honoree")),
                "contributor_name": safe_str(item.get("contributor_name")),
                "source_path":      source_path,
            })
    return rows


def build_senate_index(sample: bool = False) -> int:
    print("\n── Senate filings ──────────────────────────────────────────────────")
    years = [2025] if sample else [2022, 2023, 2024, 2025, 2026]
    total = 0

    for year in years:
        fpath = SENATE_ROOT / str(year) / "filings" / f"filings_{year}.json"
        if not fpath.exists():
            print(f"  [miss] {fpath}")
            continue

        filings, activities, lobbyists, gov_entities, foreign_entities = \
            parse_senate_filings_file(fpath)

        yr = str(year)
        total += write_parquet(filings,         PARQUET_DIR / f"senate_filings_{yr}.parquet",         f"senate_filings_{yr}")
        total += write_parquet(activities,       PARQUET_DIR / f"senate_activities_{yr}.parquet",       f"senate_activities_{yr}")
        total += write_parquet(lobbyists,        PARQUET_DIR / f"senate_lobbyists_{yr}.parquet",        f"senate_lobbyists_{yr}")
        total += write_parquet(gov_entities,     PARQUET_DIR / f"senate_gov_entities_{yr}.parquet",     f"senate_gov_entities_{yr}")
        write_parquet(foreign_entities,          PARQUET_DIR / f"senate_foreign_entities_{yr}.parquet", f"senate_foreign_entities_{yr}")

        cpath = SENATE_ROOT / str(year) / "contributions" / f"contributions_{year}.json"
        if cpath.exists():
            rows = parse_senate_contributions_file(cpath, year)
            write_parquet(rows, PARQUET_DIR / f"senate_contributions_{yr}.parquet", f"senate_contributions_{yr}")

    print(f"  Total senate rows: {total:,}")
    return total


# ── House LDA (XML) ────────────────────────────────────────────────────────────

PERIOD_MAP = {
    "Registrations": "Registrations",
    "1stQuarter":    "Q1",
    "2ndQuarter":    "Q2",
    "3rdQuarter":    "Q3",
    "4thQuarter":    "Q4",
}


def parse_house_dir_name(dirname: str) -> tuple[int, str]:
    """'2025_1stQuarter_XML' → (2025, 'Q1')"""
    parts = dirname.replace("_XML", "").split("_", 1)
    year   = int(parts[0])
    period = PERIOD_MAP.get(parts[1], parts[1]) if len(parts) > 1 else "Unknown"
    return year, period


def parse_house_xml(path: Path, year: int, period: str):
    """Parse one House XML filing → (filing_dict, activities[], lobbyists[])"""
    source_path = str(path)
    try:
        tree = etree.parse(str(path))
        root = tree.getroot()
    except Exception:
        return None, [], []

    def txt(tag) -> str | None:
        val = root.findtext(tag)
        return safe_str(val)

    filing = {
        "house_id":             safe_str(path.stem),
        "senate_id":            txt("senateID"),
        "filing_year":          year,
        "filing_period":        period,
        "org_name":             txt("organizationName"),
        "client_name":          txt("clientName"),
        "client_is_govt_entity":txt("clientGovtEntity"),
        "income":               parse_money(txt("income")),
        "expenses":             parse_money(txt("expenses")),
        "no_lobbying":          txt("noLobbying"),
        "termination_date":     txt("terminationDate"),
        "signed_date":          txt("signedDate"),
        "report_year":          txt("reportYear"),
        "report_type":          txt("reportType"),
        "source_path":          source_path,
    }

    # Activities — extract per ali_info block, since each block pairs one code
    # with one description (and a separate lobbyists list per block).
    # Fall back to legacy tag paths for older filings.
    activities = []
    lobbyists  = []

    ali_info_blocks = root.findall(".//alis/ali_info")
    if ali_info_blocks:
        # Modern schema: per-block activity + lobbyists nested under each block
        for i, block in enumerate(ali_info_blocks):
            code = safe_str(block.findtext("issueAreaCode"))
            desc = safe_str(block.findtext("specific_issues/description"))
            if not (code or desc):
                continue
            activities.append({
                "house_id":     safe_str(path.stem),
                "activity_idx": i,
                "ali_code":     code,
                "description":  desc,
                "source_path":  source_path,
            })
            # Lobbyists nested per ali_info block
            for lob_el in block.findall(".//lobbyists/lobbyist"):
                first  = safe_str(lob_el.findtext("lobbyistFirstName"))
                last   = safe_str(lob_el.findtext("lobbyistLastName"))
                suffix = safe_str(lob_el.findtext("lobbyistSuffix"))
                name   = " ".join(filter(None, [first, last, suffix])) or None
                cov    = safe_str(lob_el.findtext("coveredPosition"))
                if name or cov:
                    lobbyists.append({
                        "house_id":         safe_str(path.stem),
                        "activity_idx":     i,
                        "lobbyist_name":    name,
                        "covered_position": cov,
                        "is_new":           safe_str(lob_el.findtext("lobbyistNew")),
                        "source_path":      source_path,
                    })
    else:
        # Legacy schema: flat ali_Code list under <alis>, lobbyists list separate
        ali_codes = [el.text.strip() for el in root.findall(".//alis/ali_Code")
                     if (el.text or "").strip()]
        descs     = [el.text.strip() for el in root.findall(".//specific_issues/description")
                     if (el.text or "").strip()]
        n = max(len(ali_codes), len(descs))
        for i in range(n):
            activities.append({
                "house_id":     safe_str(path.stem),
                "activity_idx": i,
                "ali_code":     ali_codes[i] if i < len(ali_codes) else None,
                "description":  descs[i]     if i < len(descs)     else None,
                "source_path":  source_path,
            })
        for lob_el in root.findall(".//lobbyists/lobbyist"):
            first  = safe_str(lob_el.findtext("lobbyistFirstName"))
            last   = safe_str(lob_el.findtext("lobbyistLastName"))
            suffix = safe_str(lob_el.findtext("lobbyistSuffix"))
            name   = " ".join(filter(None, [first, last, suffix])) or None
            # legacy schema also used <lobbyistName>, keep as fallback
            if not name:
                name = safe_str(lob_el.findtext("lobbyistName"))
            cov    = safe_str(lob_el.findtext("coveredPosition"))
            if name or cov:
                lobbyists.append({
                    "house_id":         safe_str(path.stem),
                    "activity_idx":     None,  # legacy: no per-activity association
                    "lobbyist_name":    name,
                    "covered_position": cov,
                    "is_new":           safe_str(lob_el.findtext("lobbyistNew")),
                    "source_path":      source_path,
                })

    return filing, activities, lobbyists


def build_house_index(sample: bool = False) -> int:
    print("\n── House filings (XML) ─────────────────────────────────────────────")
    xml_dirs = sorted(HOUSE_ROOT.glob("*_XML"))

    if sample:
        xml_dirs = [d for d in xml_dirs if "2025_1stQuarter" in d.name]

    total = 0
    for xml_dir in xml_dirs:
        year, period = parse_house_dir_name(xml_dir.name)
        xml_files = sorted(xml_dir.glob("*.xml"))
        if sample:
            xml_files = xml_files[:500]

        print(f"  {xml_dir.name}: {len(xml_files):,} files")

        filings, activities, lobbyists = [], [], []
        errors = 0
        for xml_path in tqdm(xml_files, desc=f"  {xml_dir.name}", leave=False, unit="file"):
            f, acts, lobs = parse_house_xml(xml_path, year, period)
            if f is None:
                errors += 1
                continue
            filings.append(f)
            activities.extend(acts)
            lobbyists.extend(lobs)

        if errors:
            print(f"    [warn] {errors} XML parse errors skipped")

        tag = f"{year}_{period}"
        total += write_parquet(
            filings,
            PARQUET_DIR / f"house_filings_{tag}.parquet",
            f"house_filings_{tag}",
            schema_overrides={
                "house_id": pl.Utf8,
                "senate_id": pl.Utf8,
                "filing_period": pl.Utf8,
                "org_name": pl.Utf8,
                "client_name": pl.Utf8,
                "client_is_govt_entity": pl.Utf8,
                "no_lobbying": pl.Utf8,
                "termination_date": pl.Utf8,
                "signed_date": pl.Utf8,
                "report_year": pl.Utf8,
                "report_type": pl.Utf8,
                "source_path": pl.Utf8,
            },
        )
        total += write_parquet(
            activities,
            PARQUET_DIR / f"house_activities_{tag}.parquet",
            f"house_activities_{tag}",
            schema_overrides={
                "house_id": pl.Utf8,
                "ali_code": pl.Utf8,
                "description": pl.Utf8,
                "source_path": pl.Utf8,
            },
        )
        write_parquet(
            lobbyists,
            PARQUET_DIR / f"house_lobbyists_{tag}.parquet",
            f"house_lobbyists_{tag}",
            schema_overrides={
                "house_id": pl.Utf8,
                "lobbyist_name": pl.Utf8,
                "covered_position": pl.Utf8,
                "is_new": pl.Utf8,
                "source_path": pl.Utf8,
            },
        )

    print(f"  Total house rows: {total:,}")
    return total


# ── DuckDB ─────────────────────────────────────────────────────────────────────

TABLE_PATTERNS = {
    "press_releases":         "press_*.parquet",
    "senate_filings":         "senate_filings_*.parquet",
    "senate_activities":      "senate_activities_*.parquet",
    "senate_lobbyists":       "senate_lobbyists_*.parquet",
    "senate_gov_entities":    "senate_gov_entities_*.parquet",
    "senate_foreign_entities":"senate_foreign_entities_*.parquet",
    "senate_contributions":   "senate_contributions_*.parquet",
    "house_filings":          "house_filings_*.parquet",
    "house_activities":       "house_activities_*.parquet",
    "house_lobbyists":        "house_lobbyists_*.parquet",
}


def build_duckdb():
    import duckdb
    print(f"\n── DuckDB ──────────────────────────────────────────────────────────")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    for table, pattern in TABLE_PATTERNS.items():
        files = list(PARQUET_DIR.glob(pattern))
        if not files:
            print(f"    [skip] {table}: no Parquet files found")
            continue
        glob_path = str(PARQUET_DIR / pattern).replace("\\", "/")
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{glob_path}', union_by_name=True)")
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    [ok]   {table}: {count:,} rows")

    # ── Convenience views ──────────────────────────────────────────────────────
    con.execute("""
        CREATE OR REPLACE VIEW revolving_door AS
        SELECT
            sl.filing_uuid,
            sf.filing_year,
            sf.filing_period,
            sf.registrant_name,
            sf.client_name,
            sl.lobbyist_name,
            sl.covered_position,
            sf.income,
            sf.expenses
        FROM senate_lobbyists sl
        JOIN senate_filings   sf USING (filing_uuid)
        WHERE sl.covered_position IS NOT NULL
          AND sl.covered_position != ''
    """)
    print("    [ok]   view: revolving_door")

    con.execute("""
        CREATE OR REPLACE VIEW senate_spend_by_issue AS
        SELECT
            sa.general_issue_code,
            sf.filing_year,
            sf.filing_period,
            COUNT(DISTINCT sf.filing_uuid)  AS filings,
            COUNT(DISTINCT sf.client_name)  AS unique_clients,
            SUM(sf.income)                  AS total_income,
            SUM(sf.expenses)                AS total_expenses
        FROM senate_activities sa
        JOIN senate_filings    sf USING (filing_uuid)
        WHERE sa.general_issue_code IS NOT NULL
        GROUP BY ALL
        ORDER BY filing_year, filing_period, total_income DESC NULLS LAST
    """)
    print("    [ok]   view: senate_spend_by_issue")

    con.close()
    size_gb = DB_PATH.stat().st_size / 1e9
    print(f"\n  DB written to {DB_PATH}  ({size_gb:.2f} GB)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample",       action="store_true",
                        help="Process one quarter per dataset — fast validation run")
    parser.add_argument("--parquet-only", action="store_true",
                        help="Write Parquet files but skip DuckDB build")
    parser.add_argument("--duckdb-only",  action="store_true",
                        help="Skip ETL — rebuild DuckDB from existing Parquet files")
    parser.add_argument("--clean", action="store_true",
                        help="Delete existing Parquet files before building")
    args = parser.parse_args()

    if not DATA_ROOT.exists():
        print(f"ERROR: DATA_ROOT not found: {DATA_ROOT}", file=sys.stderr)
        print("Set the DATA_ROOT environment variable to the correct path.", file=sys.stderr)
        sys.exit(1)
    
    if args.clean and PARQUET_DIR.exists():
        import shutil
        print(f"[CLEAN] removing {PARQUET_DIR}")
        shutil.rmtree(PARQUET_DIR)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    if args.sample:
        print("[SAMPLE] one quarter per dataset")
    else:
        print("[FULL BUILD] expect 30-90 minutes")

    if not args.duckdb_only:
        build_press_index(sample=args.sample)
        build_senate_index(sample=args.sample)
        build_house_index(sample=args.sample)

    if not args.parquet_only:
        build_duckdb()

    elapsed = (time.time() - t_start) / 60
    print(f"\n[DONE] in {elapsed:.1f} minutes")
    if not args.parquet_only:
        print(f"   DB       → {DB_PATH}")
    print(f"   Parquet  → {PARQUET_DIR}")


if __name__ == "__main__":
    main()
