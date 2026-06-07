---
name: archive
description: >
  Snapshots every cited URL to Wayback Machine + Archive.today before
  publication so the citations survive when sources move or disappear.
  Walks findings.json, trails.json, and press_releases.json for cited URLs,
  submits each to both services with retry/backoff on 429s and timeouts,
  and writes output/archive_registry.json mapping cited URL → snapshot URLs.
  Two-service redundancy is the journalism standard. Use before
  publication, before submitting the findings PDF for review, and any time
  you've added new cited URLs to the corpus.
license: MIT
compatibility: Requires Python 3.11+ and uv. Needs network access to web.archive.org and archive.ph. No DB.
metadata:
  author: FairGuard (Mokshit Surana, Archit Rathod)
  version: "1.0.0"
  part-of: fair-guard
  companion-to: scan, trace, pressrel
  tools: bash, python, file-read, file-write
---

# archive-on-cite

Short-name `archive`. Submission-facing full skill file at
`skill/archive-on-cite/SKILL.md`; this modes copy mirrors the same
guidance with frontmatter cleaned up for agentskills.io.

## What this skill does

Every URL you cite — Senate LDA filing, USAspending award, agency bio,
news article — should be archived **before** publication. If the source
page moves, gets paywalled, or disappears, the citation in your published
story still resolves to a permanent snapshot. Two services for redundancy:
Wayback for static pages, Archive.today for paywalled/dynamic.

## CLI surface

```bash
uv run scripts/08_archive_cite.py                              # everything cited (~333 URLs)
uv run scripts/08_archive_cite.py --url <single-url>
uv run scripts/08_archive_cite.py --urls notes/extra_urls.txt
uv run scripts/08_archive_cite.py --service wayback            # or archive_today
uv run scripts/08_archive_cite.py --skip-recent 7              # only URLs older than N days
uv run scripts/08_archive_cite.py --dry-run                    # list URLs without submitting
```

## Outputs

| Destination | Content |
|---|---|
| `output/archive_registry.json` | Source of truth — per-URL Wayback + Archive.today snapshot URLs |
| `web/public/archive_registry.json` | Mirror for the Reporter UI |
| stderr | Per-URL progress + per-service result |

Exit codes: 0 = both services succeeded for every URL; 1 = Wayback failed
somewhere; 2 = Archive.today failed somewhere; 3 = both failed somewhere.

## Editorial discipline

- Archive BEFORE publication, not after.
- Partial archives count — a URL with Wayback but not Archive.today still
  has a usable snapshot.
- Never archive private content (internal email pointers, shared drives,
  the `pointer` fields in `comment_log.json`).
