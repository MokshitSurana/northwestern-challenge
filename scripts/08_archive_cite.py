#!/usr/bin/env python3
"""
08_archive_cite.py — Snapshot every cited URL to Wayback Machine + Archive.today.

Investigative journalism citation discipline: every URL you cite (Senate LDA
filing, USAspending award, agency bio, news article) should be archived BEFORE
publication so that if the source moves or disappears the citation still
works. Two-service redundancy is the standard — Wayback catches static pages
reliably, Archive.today catches dynamic/paywalled content Wayback can't.

This script:

  1. Reads the URLs cited across our submission artifacts (findings.json,
     trails.json, press_releases.json) plus an optional --urls FILE.
  2. Submits each URL to web.archive.org/save/ (Wayback) and to
     archive.ph/submit/ (Archive.today).
  3. Polls for the snapshot URLs (Wayback returns a 'Content-Location'; Archive
     issues a refresh token then a final URL).
  4. Writes a registry at output/archive_registry.json mapping cited URL →
     {wayback_url, archive_today_url, snapshotted_at, status}.
  5. Returns an exit code that reflects which services failed (0 = both
     succeeded for every URL; 1 = Wayback failed for at least one; 2 =
     Archive.today failed for at least one; 3 = both failed for at least one).
     The registry records partial successes — a URL with Wayback but no
     Archive.today still has a useful archive.

Usage:
    uv run scripts/08_archive_cite.py                          # archive everything cited
    uv run scripts/08_archive_cite.py --urls notes/urls.txt    # one URL per line
    uv run scripts/08_archive_cite.py --url https://example.com  # single URL
    uv run scripts/08_archive_cite.py --dry-run                # list what would be archived
    uv run scripts/08_archive_cite.py --service wayback        # only Wayback
    uv run scripts/08_archive_cite.py --service archive_today  # only Archive.today
    uv run scripts/08_archive_cite.py --skip-recent 7          # skip URLs archived in last N days

The registry is persisted across runs so re-running the script is incremental
— previously-archived URLs are skipped unless their snapshot is older than
--skip-recent days (default 30).

Network etiquette: 1-second delay between submissions per service. Wayback's
save API is rate-limited; bursting will get 429s.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "output" / "archive_registry.json"
WEB_PUBLIC = REPO_ROOT / "web" / "public"
WEB_REGISTRY = WEB_PUBLIC / "archive_registry.json"

WAYBACK_SAVE = "https://web.archive.org/save/"
ARCHIVE_TODAY_SUBMIT = "https://archive.ph/submit/"

USER_AGENT = "FairGuard-Archive/1.0 (https://github.com/MokshitSurana/northwestern-challenge)"

DEFAULT_SKIP_RECENT_DAYS = 30


# ── URL collection ────────────────────────────────────────────────────────────


def collect_urls_from_findings(findings_path: Path) -> set[str]:
    """Walk findings.json and pull every URL we cite: each finding's Senate
    LDA URL, every embedded trail's award sources (none currently, but the
    field is reserved), every embedded press_releases match's URL."""
    out: set[str] = set()
    if not findings_path.exists():
        return out
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    for f in data.get("findings", []):
        if f.get("senate_lda_url"):
            out.add(f["senate_lda_url"])
        pr = f.get("press_releases") or {}
        for g in pr.get("by_client", []):
            for m in g.get("matches", []):
                if m.get("url"):
                    out.add(m["url"])
    return out


def collect_urls_from_trails(trails_path: Path) -> set[str]:
    """Trails currently don't store per-award URLs (USAspending links are
    constructed lazily) — included for symmetry / future schema growth."""
    out: set[str] = set()
    if not trails_path.exists():
        return out
    # Reserved.
    return out


def collect_urls_from_pressrel(pressrel_path: Path) -> set[str]:
    out: set[str] = set()
    if not pressrel_path.exists():
        return out
    data = json.loads(pressrel_path.read_text(encoding="utf-8"))
    for r in data.get("reports", []):
        for m in r.get("matches", []):
            if m.get("url"):
                out.add(m["url"])
    return out


def collect_default_urls() -> set[str]:
    out: set[str] = set()
    out |= collect_urls_from_findings(WEB_PUBLIC / "findings.json")
    out |= collect_urls_from_trails(WEB_PUBLIC / "trails.json")
    out |= collect_urls_from_pressrel(WEB_PUBLIC / "press_releases.json")
    # Filter junk: keep only http(s), skip mailto, javascript, anchors.
    return {u for u in out if u.startswith(("http://", "https://"))}


# ── Registry persistence ──────────────────────────────────────────────────────


def load_registry() -> dict:
    if not REGISTRY.exists():
        return {"generated_at": None, "n_urls": 0, "entries": {}}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(reg: dict) -> None:
    reg["generated_at"] = datetime.now(UTC).isoformat()
    reg["n_urls"] = len(reg.get("entries") or {})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    # Mirror a slimmed copy to web/public for the UI to surface "archived ✓"
    # icons next to the matching URLs (Day-5 polish).
    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    WEB_REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def is_recent(entry: dict, days: int) -> bool:
    """A URL is 'recently archived' if both services succeeded within the
    last N days. Partial successes always re-attempt."""
    if not entry:
        return False
    snap = entry.get("snapshotted_at")
    if not snap:
        return False
    try:
        snap_dt = datetime.fromisoformat(snap)
        if snap_dt.tzinfo is None:
            snap_dt = snap_dt.replace(tzinfo=UTC)
    except ValueError:
        return False
    if datetime.now(UTC) - snap_dt > timedelta(days=days):
        return False
    return bool(entry.get("wayback_url")) and bool(entry.get("archive_today_url"))


# ── Wayback Machine ───────────────────────────────────────────────────────────


def submit_wayback(url: str, timeout: int = 90, max_attempts: int = 3) -> tuple[bool, str | None, str | None]:
    """Submit a URL to web.archive.org/save/. Returns (success, snapshot_url,
    error_message). The save endpoint redirects to the freshly-saved snapshot
    URL on success; we capture that URL from the Location header (if any)
    or from the resolved URL.

    Retry-aware: transient errors (HTTP 429/502/503, timeouts) get up to
    max_attempts tries with exponential backoff (2s, 4s, 8s). Wayback's save
    endpoint is genuinely slow — a 30-second timeout was too aggressive in
    practice, so the default is 90s."""
    save_url = WAYBACK_SAVE + url
    last_err = "unknown"
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(2 ** attempt)  # 2s, 4s, 8s
        try:
            req = urllib.request.Request(save_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                final = resp.geturl()
                if "web.archive.org/web/" in final:
                    return True, final, None
                cl = resp.headers.get("Content-Location") or resp.headers.get("Location")
                if cl:
                    snap = "https://web.archive.org" + cl if cl.startswith("/") else cl
                    return True, snap, None
                return False, None, f"unexpected response url: {final}"
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < max_attempts - 1:
                last_err = f"HTTP {e.code} (will retry)"
                continue
            return False, None, f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_attempts - 1:
                last_err = "timeout (will retry)"
                continue
            return False, None, f"network error: {e}"
    return False, None, f"exhausted retries ({last_err})"


# ── Archive.today ─────────────────────────────────────────────────────────────


_ARCHIVE_TODAY_REFRESH_RE = re.compile(
    r'<meta http-equiv="refresh"[^>]*url=([^"\s]+)', re.IGNORECASE
)


def submit_archive_today(url: str, timeout: int = 90, max_attempts: int = 3) -> tuple[bool, str | None, str | None]:
    """POST to archive.ph/submit/ with the URL. Archive.today's flow returns
    HTML containing a meta-refresh to the final snapshot URL.

    Retry-aware: same shape as submit_wayback. Archive.today's 429 rate
    limit kicks in around 1 submission per 8-12 seconds; the 2-4-8 backoff
    typically clears it on the second attempt."""
    data = urllib.parse.urlencode({"url": url}).encode()
    last_err = "unknown"
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(2 ** attempt)
        req = urllib.request.Request(
            ARCHIVE_TODAY_SUBMIT,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                cl = resp.headers.get("Content-Location") or resp.headers.get("Refresh")
                if cl:
                    m = re.search(r"url=([^,;\s]+)", cl)
                    if m:
                        return True, m.group(1), None
                m = _ARCHIVE_TODAY_REFRESH_RE.search(body)
                if m:
                    return True, m.group(1), None
                m = re.search(r'(https?://archive\.(?:ph|today|li|fo|is)/[\w]+)', body)
                if m:
                    return True, m.group(1), None
                return False, None, "submission accepted but no snapshot URL in response"
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < max_attempts - 1:
                last_err = f"HTTP {e.code} (will retry)"
                continue
            return False, None, f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_attempts - 1:
                last_err = "timeout (will retry)"
                continue
            return False, None, f"network error: {e}"
    return False, None, f"exhausted retries ({last_err})"


# ── Main driver ───────────────────────────────────────────────────────────────


def archive_one(url: str, services: set[str]) -> dict:
    """Snapshot one URL to the requested services. Returns the entry dict to
    merge into the registry."""
    entry: dict = {
        "url": url,
        "snapshotted_at": datetime.now(UTC).isoformat(),
        "wayback_url": None,
        "wayback_error": None,
        "archive_today_url": None,
        "archive_today_error": None,
    }
    if "wayback" in services:
        ok, snap, err = submit_wayback(url)
        entry["wayback_url"] = snap if ok else None
        entry["wayback_error"] = err
        time.sleep(1.0)  # polite delay between services
    if "archive_today" in services:
        ok, snap, err = submit_archive_today(url)
        entry["archive_today_url"] = snap if ok else None
        entry["archive_today_error"] = err
        time.sleep(1.0)
    return entry


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--url", help="Archive a single URL.")
    g.add_argument("--urls", type=Path, help="Path to a text file (one URL per line).")
    ap.add_argument("--service", choices=["wayback", "archive_today", "both"],
                    default="both", help="Which service(s) to use (default both).")
    ap.add_argument("--skip-recent", type=int, default=DEFAULT_SKIP_RECENT_DAYS,
                    help=f"Skip URLs successfully archived within N days (default {DEFAULT_SKIP_RECENT_DAYS}).")
    ap.add_argument("--dry-run", action="store_true",
                    help="List what would be archived; don't submit anything.")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Build the URL list.
    if args.url:
        urls = {args.url}
    elif args.urls:
        urls = {ln.strip() for ln in args.urls.read_text(encoding="utf-8").splitlines() if ln.strip()}
    else:
        urls = collect_default_urls()
    if not urls:
        sys.exit("no URLs to archive (try --url or --urls FILE)")

    services = {"wayback", "archive_today"} if args.service == "both" else {args.service}

    reg = load_registry()
    entries = reg.setdefault("entries", {})

    # Filter to URLs that need work.
    to_do = [u for u in sorted(urls) if not is_recent(entries.get(u), args.skip_recent)]
    skipped = len(urls) - len(to_do)
    sys.stderr.write(
        f"{len(urls)} URL(s) collected; {len(to_do)} to archive, {skipped} skipped (recent).\n"
    )

    if args.dry_run:
        for u in to_do:
            print(u)
        return 0

    n_wayback_fail = 0
    n_archive_fail = 0
    for i, url in enumerate(to_do, 1):
        sys.stderr.write(f"[{i}/{len(to_do)}] {url}\n")
        entry = archive_one(url, services)
        prev = entries.get(url) or {}
        # Preserve previous-service result if this run skipped that service.
        if "wayback" not in services and prev.get("wayback_url"):
            entry["wayback_url"] = prev["wayback_url"]
            entry["wayback_error"] = prev.get("wayback_error")
        if "archive_today" not in services and prev.get("archive_today_url"):
            entry["archive_today_url"] = prev["archive_today_url"]
            entry["archive_today_error"] = prev.get("archive_today_error")
        entries[url] = entry
        if entry["wayback_error"]:
            n_wayback_fail += 1
            sys.stderr.write(f"  wayback: FAIL ({entry['wayback_error']})\n")
        elif entry["wayback_url"]:
            sys.stderr.write(f"  wayback: {entry['wayback_url']}\n")
        if entry["archive_today_error"]:
            n_archive_fail += 1
            sys.stderr.write(f"  archive.today: FAIL ({entry['archive_today_error']})\n")
        elif entry["archive_today_url"]:
            sys.stderr.write(f"  archive.today: {entry['archive_today_url']}\n")
        # Persist after every URL — a crash mid-batch shouldn't lose all work.
        save_registry(reg)

    # Exit code reflects which services had failures.
    if n_wayback_fail and n_archive_fail:
        return 3
    if n_archive_fail:
        return 2
    if n_wayback_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
