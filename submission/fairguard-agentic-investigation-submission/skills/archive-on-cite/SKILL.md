---
name: archive-on-cite
description: >
  Snapshots every cited URL to Wayback Machine + Archive.today before
  publication so the citations survive when sources move or disappear.
  Walks findings.json, trails.json, and press_releases.json for cited URLs,
  submits each to both services with retry/backoff on 429s and timeouts,
  and writes output/archive_registry.json mapping cited URL → snapshot URLs.
  Two-service redundancy is the journalism standard — Wayback for static
  pages, Archive.today for paywalled / dynamic content. Use before
  publication, before submitting the findings PDF for review, and any time
  you've added a new cited URL to the corpus.
license: MIT
compatibility: Requires Python 3.11+ and uv; needs network access (Wayback Machine and Archive.today).
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
---

# archive-on-cite

## What this skill does

Investigative journalism citation discipline: every URL you cite — Senate
LDA filing, USAspending award, agency bio, news article — should be
archived **before** publication. If the source page moves, gets paywalled,
or disappears, the citation in your published story still resolves to a
permanent snapshot.

This skill enforces that discipline across the FairGuard corpus by walking
the on-disk output of every other skill (findings.json from scan,
trails.json from trace, press_releases.json from pressrel) and submitting
every cited URL to two independent archive services with retry/backoff,
then persisting the snapshot URLs to a registry the rest of the project
can reference.

## Why two services

| Service | Strengths | Weaknesses |
|---|---|---|
| **Wayback Machine** (web.archive.org) | Most-cited by working journalists; deepest historical coverage; stable URLs | Sometimes can't snapshot paywalled or dynamic-content pages; rate-limited |
| **Archive.today** (archive.ph) | Catches paywalled / dynamic content Wayback can't; lower rate limit | Less recognized as a journalism citation source; .ph TLD has TLS issues on some networks |

Two-service redundancy is the standard for serious archiving. The script
records snapshot URLs from both; the registry's `snapshotted_at` flag is
set only when both succeeded (so re-runs of `--skip-recent` re-attempt
partial successes).

## How the script collects URLs

By default, it walks:

| Source | What it picks up |
|---|---|
| `web/public/findings.json` | Each finding's `senate_lda_url` + every embedded press-release match's `url` |
| `web/public/trails.json` | Reserved (USAspending award URLs are constructed lazily — no persistent URLs in current schema) |
| `web/public/press_releases.json` | Every match's `url` across every report |

You can override with `--url` for a single URL or `--urls FILE` for a text
file (one URL per line).

## CLI surface

```bash
# Archive everything cited across the project (default; ~333 URLs)
uv run skills/archive-on-cite/scripts/08_archive_cite.py

# A single URL
uv run skills/archive-on-cite/scripts/08_archive_cite.py --url "https://lda.senate.gov/filings/public/filing/..."

# A file of URLs (one per line)
uv run skills/archive-on-cite/scripts/08_archive_cite.py --urls notes/extra_urls.txt

# Service-specific runs
uv run skills/archive-on-cite/scripts/08_archive_cite.py --service wayback
uv run skills/archive-on-cite/scripts/08_archive_cite.py --service archive_today

# Skip URLs successfully archived in the last N days (default 30)
uv run skills/archive-on-cite/scripts/08_archive_cite.py --skip-recent 7

# Dry run — list what would be archived
uv run skills/archive-on-cite/scripts/08_archive_cite.py --dry-run
```

## Retry and rate limits

| Service | Submission cadence | Retry on | Backoff |
|---|---|---|---|
| Wayback | 1 / second (script-enforced) | HTTP 429/502/503, timeout | 2s, 4s, 8s — up to 3 attempts |
| Archive.today | 1 / second (script-enforced) | HTTP 429/502/503, timeout | 2s, 4s, 8s — up to 3 attempts |

Default timeout is 90 seconds per service per attempt. Wayback's save
endpoint is genuinely slow on dynamic / large pages; the longer timeout
covers that without inflating wall time on the common case.

## Outputs

| Destination | Content |
|---|---|
| `output/archive_registry.json` | Source of truth. Per-URL entry with `wayback_url`, `archive_today_url`, `snapshotted_at`, error messages for failed services |
| `web/public/archive_registry.json` | Mirror so the Reporter UI can surface "archived ✓" badges next to LDA / press-release URLs |
| stderr | Per-URL progress + per-service result. Final exit code reflects which services failed (0 = both succeeded everywhere; 1 = Wayback failed somewhere; 2 = Archive.today failed somewhere; 3 = both failed somewhere) |

## Incremental re-runs

The registry is persisted across runs, so:

```bash
# First run — archives everything from scratch
uv run skills/archive-on-cite/scripts/08_archive_cite.py

# Two weeks later, after adding new press-release matches — only archives
# the new URLs (skips the ones still recent in the registry)
uv run skills/archive-on-cite/scripts/08_archive_cite.py --skip-recent 30
```

Set `--skip-recent 0` to re-archive everything (e.g. before final submission
to refresh stale snapshots).

## Editorial discipline

- **Archive BEFORE publication**, not after. If you publish a citation and
  the source vanishes the next day, you can't go back in time to snapshot
  the original — Wayback may have its own crawl from before that point, but
  Archive.today won't.
- **Partial archives count.** A URL with Wayback but not Archive.today still
  has a usable archive. The registry preserves partial successes.
- **Don't archive private content.** Internal email pointers, shared-drive
  URLs, and anything behind authentication should *not* go through these
  public services. The script only walks the public submission artifacts
  (findings.json, trails.json, press_releases.json); never feed it the
  `comment_log.json` events whose pointers reference private email.
- **Re-archive before final submission.** Snapshots can themselves expire
  in rare cases; a fresh archive within the last 7 days before publication
  is the safe default.

## Reproducibility

The registry is fully reproducible: same URLs in + same network conditions
→ same snapshots out. Re-running the script after a clean checkout
recovers the same archive state by re-submitting any URL that's missing
from a fresh `output/archive_registry.json`.

Both services are public, no API keys required — anyone can re-run the
archive from any environment with internet access.

## When NOT to use this skill

- Private URLs (internal email, authenticated dashboards, shared drives).
- URLs from the `notes/comment_requests/comment_log.json` `pointer` field —
  those reference private email threads and must never be submitted to a
  public archive.
- URLs the original source has explicitly requested not to be archived
  (rare; respect robots.txt / X-Robots-Tag if you discover one).
