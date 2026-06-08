# Trace — `/fair-guard pressrel`

**Date:** 2026-06-07
**Skill invoked:** `pressrel` (press-release-cross-ref v1.0.0)
**Platform:** Windows 11, Python 3.11.15
**Outcome:** Three bundled case files reproduced against the DuckDB; one batched `--enrich-findings` pass attached **714 verified press-release matches across 30 of 40 scan findings** in ~10 seconds.

---

## Invocation 1 — case-file mode (Steinberg DOE clients)

```bash
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json
```

The dispatcher checked the DuckDB prerequisite (`output/investigation.duckdb` exists) and routed to `skill/press-release-cross-ref/SKILL.md`, which loaded `steinberg_clients.json` — 9 client aliases (Anovion, Talon Nickel, Forge Battery, Cabot Corp, Wabtec, Amsted, Burns & McDonnell, Battery Materials & Tech Coalition, plus the thematic "critical minerals" anchor).

**Script behavior:**

1. Built a per-alias regex with per-alias smart word boundaries (RE2-safe for DuckDB). Critical: aliases starting or ending in non-word characters get `\b` only on the word-character side, so `A&M (Texas)` doesn't lose its boundary check.
2. Issued one DuckDB regex scan per client against `press_releases.text` and `.title`, with smart-quote tolerance baked into the regex (so `Land O'Lakes` matches `Land O'Lakes` *and* `Land O'Lakes` with the curly apostrophe).
3. De-duped on `(bioguide_id, date, title)` — re-issued releases and cross-posts don't inflate the per-client tally.
4. Extracted a 120-char-radius snippet around the first match with the matched phrase wrapped in `**bold**` for instant triage.

**Output (verbatim, abbreviated):**

```
## Press-release cross-ref: Steinberg DOE clients — Congressional press-release cross-ref

Searched Congressional press releases (2022-01-01 to 2026-04-01) for mentions of
**9** client name(s). Found **59** verified matches across **37** distinct member(s).

### Per-client tallies

| Client                                | Mentions | Distinct members | First       | Last        |
|---------------------------------------|---------:|-----------------:|-------------|-------------|
| Anovion                               |        3 |                3 | 2022-10-20  | 2025-07-10  |
| Talon Nickel                          |        8 |                4 | 2023-11-02  | 2026-02-04  |
| Forge Battery                         |        1 |                1 | 2024-09-20  | 2024-09-20  |
| Cabot Corporation                     |        2 |                2 | 2024-03-13  | 2024-09-20  |
| Wabtec                                |       16 |                5 | 2022-07-26  | 2025-09-23  |
| Amsted Industries                     |        0 |                0 | —           | —           |
| Burns & McDonnell                     |        3 |                1 | 2022-09-12  | 2025-09-12  |
| Battery Materials & Tech Coalition    |        1 |                1 | 2024-05-01  | 2024-05-01  |
| Critical minerals (thematic)          |       25 |               20 | 2026-02-11  | 2026-03-27  |

embedded press-release evidence in 1 finding row(s) of web/public/findings.json
```

Because the case file has a `match: [{lobbyist_name: "Benjamin Steinberg", agency_short: "energy"}]` block, the report was also embedded into the matching scan-finding row in `findings.json` as a `press_releases` field. The Reporter UI's findings page now shows a Press-release panel inline on the Steinberg card.

## Invocation 2 — batched enrich-findings pass

```bash
uv run scripts/05_pressrel_search.py --enrich-findings
```

Pulls every scan finding's `top_clients_str`, builds one big alias union, runs **one** batched DuckDB regex scan over all 141,332 press releases, then attributes each match back to the originating client in Python via per-client regex re-scan of the snippet. This is what keeps the runtime ~constant in the number of findings — a per-finding scan would take minutes.

```
enriching 40 findings with 129 unique client names…
  one batched scan returned 714 de-duplicated press-release rows
updated 30 finding row(s) with 714 total press-release matches
done — 30 findings enriched, 714 total matches attached
```

## Ordering note for reproducibility

`--enrich-findings` overwrites the `press_releases` field on each finding row. Case-file runs (with `match` blocks) populate the same field with richer per-alias data. To preserve the richer matches, run **enrich first, then case files**:

```bash
uv run scripts/05_pressrel_search.py --enrich-findings                      # bulk pass first
uv run scripts/05_pressrel_search.py --case <case>.json                     # case files override
```

This is the ordering the coi-graph triangle detector benefits from: case-file aliases find "Cargill" in press releases that `top_clients_str`'s literal "CARGILL INC" misses, so the (legislator, Cargill, USDA) triangles only form when the case-file data is present.

## The judgment that mattered

The load-bearing decision is the per-alias word-boundary handling. Plain `\b...\b` would have failed for aliases like `A&M (Texas)` (no boundary between `)` and a space — both non-word). The script computes `left = \b if alias[0].isalnum() else ""` and analogous for right, so the regex still compiles and matches under both Python's `re` and DuckDB's RE2. This was a real bug caught by the `test_no_substring_match` integration test on the live DB.

## Reproducibility

Same case file + same corpus → byte-identical JSON output (modulo `generated_at` timestamps). The 30 tests in `tests/test_pressrel.py` cover the regex discipline, snippet extraction, schema validation, and DB integration; CI runs the 25 non-DB tests on every push.

```bash
# Full reproduce of the case-file invocation:
uv run scripts/05_pressrel_search.py \
  --case skill/press-release-cross-ref/cases/steinberg_clients.json \
  --out notes/pressrel_steinberg.md \
  --json output/pressrel_steinberg.json
```
