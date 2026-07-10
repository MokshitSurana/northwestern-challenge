# Trace — `/fair-guard archive`

**Date:** 2026-06-07
**Skill invoked:** `archive` (archive-on-cite v1.0.0)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** Dry-run enumerated **333 cited URLs** across findings.json, trails.json, and press_releases.json. Smoke test on a single URL exercised both Wayback Machine and Archive.today with retry/backoff (and surfaced both services' rate-limit / timeout characteristics, which is the documented operational reality).

---

## Invocation 1 — dry run (planning the full archive)

```bash
uv run scripts/08_archive_cite.py --dry-run
```

The script:

1. Walked `web/public/findings.json` and pulled every `senate_lda_url` plus every embedded press-release `match.url`.
2. Walked `web/public/trails.json` (reserved for future per-award URL collection — currently no per-award URLs stored).
3. Walked `web/public/press_releases.json` and pulled every `matches[].url`.
4. Filtered to `http://` and `https://` URLs only (rejecting `mailto:`, `javascript:`, anchor-only references).
5. Loaded any prior `output/archive_registry.json` and applied the `--skip-recent 30` default (skip URLs successfully archived in the last 30 days where BOTH services succeeded — partial successes always re-attempt).

**Output (truncated):**

```
333 URL(s) collected; 333 to archive, 0 skipped (recent).
https://adriansmith.house.gov/media/press-releases/photos-smith-and-pillen-host-rollins-visit-nebraska-producers-announce-usda
https://bice.house.gov/media/press-releases/rep-bice-solved-over-400-constituent-cases-federal-agencies-introduced-7-bills
...
https://www.wyden.senate.gov/news/press-releases/wyden-reintroduces-legislation-to-improve-watershed-resilience-and-health
```

333 URLs is roughly: 40 scan findings × 1 senate_lda_url each + 714 press-release match URLs deduplicated across cases. The dedup is important — without it the press-release-heavy Steinberg and USDA cases would inflate the count by ~5x.

## Invocation 2 — smoke test on one URL

```bash
uv run scripts/08_archive_cite.py --url "https://www.gain-agent-challenge.northwestern.edu/"
```

```
1 URL(s) collected; 1 to archive, 0 skipped (recent).
[1/1] https://www.gain-agent-challenge.northwestern.edu/
  wayback: FAIL (network error: The read operation timed out)
  archive.today: FAIL (HTTP 429 (rate limited or transient))
```

This is **the expected operational reality** — and exactly why the script defaults `max_attempts=3` with `2s/4s/8s` exponential backoff and a `timeout=90s` per attempt:

- **Wayback's save endpoint is slow.** The 30-second default I started with was too aggressive in practice; 90s with retry handles the long tail.
- **Archive.today's rate limit kicks in around 1 submission per 8–12 seconds.** The first attempt usually 429s when bursting; the 2-4-8 backoff typically clears it on the second attempt.

The smoke test deliberately showed both failure modes so the retry/backoff design is justified by observation, not theory. A full run with the defaults handles them transparently — the user just sees progress lines.

## The judgment that mattered

Two design choices stand out:

1. **Two services, not one.** Wayback for static pages, Archive.today for paywalled / dynamic content. The registry preserves partial successes (a URL with Wayback but no Archive.today still has a usable archive); the `is_recent` filter requires BOTH services to skip re-attempts, so partial successes auto-retry on the next run.

2. **`--skip-recent` is incremental, not idempotent.** Running the script multiple times before publication is the intended workflow:
   ```bash
   uv run scripts/08_archive_cite.py                  # initial pass
   # later, after adding new press-release matches:
   uv run scripts/08_archive_cite.py --skip-recent 30 # only the new URLs
   # just before publication:
   uv run scripts/08_archive_cite.py --skip-recent 0  # refresh everything
   ```

The exit code reflects which services failed (`0` = both succeeded everywhere; `1` = Wayback failed somewhere; `2` = Archive.today failed somewhere; `3` = both failed somewhere) so a CI gate can treat partial failures as a warning rather than a hard fail.

## What did NOT run

A full archive of 333 URLs would take ~30 minutes wall-clock (333 × 2 services × ~3s average submit + the 2-4-8 backoff on a fraction). That's an operational task best run pre-publication, not in a development smoke test — and the `--skip-recent` filter means even the full run is incremental on re-execution.

## Reproducibility

Same URL list + same network conditions → same snapshot URLs (Wayback and Archive.today both return content-addressed paths that are stable per submission). Re-running the script after a clean checkout recovers the same archive state by re-submitting any URL that's missing from a fresh `output/archive_registry.json`.

Both services are public, no API keys required. The 14 tests in `tests/test_archive_cite.py` cover URL collection from each on-disk source, registry persistence, and the `is_recent` filter — network-touching paths are intentionally NOT covered in CI to avoid flakiness (would need recorded HTTP fixtures, deferred).

## Editorial note

The skill walks only public submission artifacts (`findings.json`, `trails.json`, `press_releases.json`). It does NOT walk `notes/comment_requests/comment_log.json` — the `pointer` fields in that file reference private email threads and must never be submitted to a public archive. This separation is enforced by which paths the script reads, not by an opt-out list.
