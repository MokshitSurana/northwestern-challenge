# Mid-project plan

**Status check (2026-06-06).** Five Agent Skills shipped (`doctor`, `index`,
`resolve`, `scan`, `trace`), 144 tests green on Linux + macOS + Windows, F1 =
0.963 on the resolver, 34 invariants on the indexer, anchor finding verified,
structural finding generated, money trail recipient-name-verified, §207 +
comment-request drafts ready, Reporter UI shipped at `/` + `/trails` with
kebab menus and per-card exports. The remaining work is editorial, packaging,
and one structural gap (we haven't used the press-release half of the corpus).

This file is a working brief for the rest of the submission window. Two parts:

1. **What's left** — gates and soft items between today and submit.
2. **What to add** — new skills + features ranked by ROI against the
   challenge's four scoring dimensions.

It assumes the reader has skimmed `CLAUDE.md` and the challenge details page
(<https://www.gain-agent-challenge.northwestern.edu/details/>).

---

## 0. The grading rubric we're optimizing for

From the challenge details page. Each of the four technical dimensions scores
0–3 independently, weighted equally, **capped at 1/3 if not reproducible**:

| Dimension | What scores well | How our work maps |
|-----------|------------------|-------------------|
| Findings are real | Sourced, public-interest, specific records | Bridenstine anchor + 139 candidates + recipient-verified money trail |
| Keeps investigation organized | Stateful across sessions; tracks what's open / cold | Currently weak — no comment-tracker, no diff between scan runs |
| Efficient with the corpus | Deterministic tools (Polars, DuckDB) do heavy lifting; the agent reasons | Strong — ETL → Parquet → DuckDB, scan is one SQL pass |
| Human can verify | Every claim → specific record; fast review surface; auditable | Strong — UI has source UUID + LDA link on every card |
| Extends what an agent can do | Entity resolvers, cross-ref utilities, domain parsers | Strong on resolver + LDA quirks; weak on press-release coverage |

The gap is **organization** (no comment-tracker / no diff) and **completeness**
(press releases unused, money trail not wired to USAspending links on the card).

---

## 1. What's left before submission

### 1.1 Hard gates (a missing one of these caps the score)

| # | Item | Why | Effort | Owner |
|---|------|-----|--------|-------|
| 1 | **Add `LICENSE` file (MIT)** | README claims MIT but no file. Challenge explicitly requires MIT-licensed skills. | 5 min | — |
| 2 | **Capture a `trace` skill interaction log** | `traces/` has doctor/index/resolve/scan; missing trace. Submission requires "interaction traces keyed to skill invocations." | 30 min | — |
| 3 | **Actually send the comment requests** | Drafts ready in `notes/09`. The findings report can't say "request for comment pending" forever — at minimum send + log "no response after X days." | 1 day calendar, 1 hr active | — |
| 4 | **Pin the four †-flagged departure dates** | Sherman, Newsome, Bailey, Johnson — month precision needed for §207. Listed in `notes/09`. | 2 hr | — |
| 5 | **Confirm Barbic had no 2021 USDA contact** | Last residual §207 timing question. | 1 hr | — |

### 1.2 README submission map (soft items, but visible to judges)

The challenge wants the README to be a map: included skills, which findings
they support, where the relevant traces are, **outside data used**,
**conflicts of interest**, **legal-risk flags**. Current README touches some
of this but needs explicit sections:

- [ ] **Outside data disclosure.** USAspending.gov live API (via `trace`) is
  outside data and affects findings about named individuals — must be
  disclosed cleanly. Currently mentioned in passing.
- [ ] **Conflicts of interest.** Even "none" needs to be stated explicitly
  with the reasoning (no team member is registered to lobby; no team member
  has financial ties to the named firms; etc.).
- [ ] **Legal-risk flags.** One paragraph aimed at the evaluation panel:
  our §207 review found *no* timed-ban violations among the examined top-10,
  but two cases (Barbic 2021, the four †-flagged) need pinning before any
  publication. No DOJ-referrable findings at this time.
- [ ] **Register the team** on the challenge site (not a code task).

### 1.3 Structural gap (the corpus half we're not using)

The corpus is *lobbying disclosure data* + *Congressional press releases*. We
loaded press releases into `press_releases` but no skill queries them. Judges
who read the challenge description will notice. See §2.A.1 for the fix.

---

## 2. New skills + features (ranked by ROI)

Three tiers: quick wins on existing skills, new investigative capabilities,
process/polish. Each item names the skill/file path so it's actionable.

### Tier A — Quick wins (1 day each)

#### A.1 `pressrel` — search Congressional press releases tied to a candidate ✅ SHIPPED (Day 2, 2026-06-06)

**Why it was #1:** closed the "you only used half the corpus" hole. The
`press_releases` table has 141,332 rows with `bioguide_id`, `member_name`,
`party`, `state`, `chamber`, `date`, `title`, `url`, `text` — far richer than
the original assumption — which supports member-side filters out of the box.

**Concrete payoff (verified on the real DB):** `--enrich-findings` attached
675 verified press-release matches across 29 of the top 40 scan findings in
~10 seconds. The case-file pass for Steinberg DOE clients alone surfaced 59
matches across 37 distinct members; Limbaugh's water-district clients
surfaced a dense Bureau of Reclamation funding-announcement cluster.

**Shipped artifacts:**
- `scripts/05_pressrel_search.py` — DuckDB regex with per-alias smart word
  boundaries (RE2-compatible so it works in DuckDB *and* Python), snippet
  extraction, de-dup on `(bioguide_id, date, title)`, smart-quote tolerance,
  case-file mode + ad-hoc `--mention` mode + batched `--enrich-findings` mode
- `skill/press-release-cross-ref/SKILL.md` — submission artifact
- `skill/press-release-cross-ref/cases/steinberg_clients.json` + `limbaugh_clients.json` — reproducible
- `.agents/skills/fair-guard/modes/pressrel/SKILL.md` — agentskills.io copy
- `.claude/skills/fair-guard/SKILL.md` — dispatcher routes `pressrel` with the
  DuckDB prerequisite guard
- `tests/test_pressrel.py` — 30 tests (unit: regex discipline, snippet
  extraction, schema validation, render shape; integration: real-DB queries
  with the `@skipif(not DB_PATH.exists())` pattern). Total project test count
  now 174.
- Web integration: `web/public/press_releases.json` feed + per-finding
  `press_releases` field on matching rows in `findings.json`. UI route for
  `/pressrel` is queued for the polish day.

#### A.2 `fact-check` — drop in a claim, get back evidence rows

**Why:** directly scored on the "human can verify" dimension. Input: a free-
text claim ("Cargill received $700M from USDA"). Output: structured verdict
(verified / partial / refuted) with the LDA UUIDs + USAspending award IDs that
support or contradict it. Reuses `entity_map` and `trace` plumbing.

**Files:**
- `scripts/06_fact_check.py`
- `skill/fact-checker/SKILL.md`
- Wire as `/fair-guard check "<claim>"`

#### A.3 `comment-tracker` — materialize the §207 / comment workflow

**Why:** the "keeps investigation organized" dimension is our weakest. Today
the workflow lives in `notes/09` Markdown. A small JSON log + CLI is the
minimum viable system:
```json
{ "case": "steinberg_doe", "firm": "Venn Strategies",
  "request_sent_at": "2026-06-08", "deadline": "2026-06-15",
  "response": null, "status": "awaiting" }
```
And a CLI: `uv run scripts/07_comment_tracker.py --log <case> <event>`. Wire
the status onto each finding card in the UI so a reporter sees "✉ awaiting
since Jun 8" at a glance.

**Files:**
- `scripts/07_comment_tracker.py`
- `output/comment_log.json`
- UI: extend `Finding.comment_status` and show on card

#### A.4 Per-card one-pager PDF

The UI already exports Markdown per card. Add: a single-page printable PDF
brief per candidate (firm, prior role, money trail, comment status, §207
verdict). Reporters paste one-pagers into editor meetings — this is genuinely
useful, not just decorative.

**Files:** extend `web/src/app/lib/exports.ts` (probably client-side via
`window.print()` of a hidden print-layout div per card).

#### A.5 `archive-on-cite` hook

Borrow Joe Amditis's pattern. When a skill emits an LDA filing URL or
USAspending award URL, snapshot it to Archive.today and/or Wayback. Closes
"what if the source disappears" risk. Cheap to add, scored on multiple
dimensions.

**Files:**
- `.claude/hooks/archive_on_cite.py` (PostToolUse hook)
- Optional: pre-cache the URLs cited in `findings/findings_report.md` once

### Tier B — New investigative capabilities (2–4 days each)

#### B.1 `coi-graph` — Person × Client × Award × Press-release network

**Why:** the most differentiated skill we could ship. The corpus *is* a graph
of relationships and nobody else's submission will compose the four node
types. Build a small NetworkX graph joining:

```
legislator ─[issued press release praising]─> client
client     ─[is represented by]──────────────> lobbyist
lobbyist   ─[former staff of]────────────────> agency
agency     ─[awarded grant to]───────────────> client
```

Output: JSON adjacency + an SVG. The visualization closes the loop on every
shipped skill — `pressrel` + `scan` + `resolve` + `trace` all feed it.

**Files:**
- `scripts/08_coi_graph.py` (NetworkX + svg out)
- `skill/coi-graph/SKILL.md`
- UI: new `/graph` route that renders the SVG inline

#### B.2 `tipsheet` — Hagar-style lead generator

Nick Hagar's published tipsheet skill recovered ~half the Pulitzer-rubric
leads on arbitrary corpora. We can adapt it for lobbying data: it feeds our
DB + `trace`, returns ranked leads with evidence pointers. Plays directly to
"extends what an agent can do for investigations." Could ship initially as a
thin wrapper that asks Claude to read our scan output + the press releases
and propose 10 leads, then verifies them deterministically with our scripts.

#### B.3 `temporal-anomaly` skill

Find spikes the eye misses: an agency's senior staffer leaves Q1, registers
as a lobbyist Q2, their firm's filings naming that agency triple by Q3,
agency awards to that firm's clients spike Q4. All four signals are in the
DB; nothing currently joins them.

#### B.4 `departure-date-pinner`

Given a name + agency, triangulate the departure month using (a) LDA
registration first-quarter, (b) last press-release mention in their official
capacity, (c) optional web search. Closes the four †-flagged dates from
gate #4 AND is reusable for every future investigation on this corpus.

#### B.5 `bipartite-bridge` skill

Surfaces lobbyists whose covered-position discloses staff work for *both*
parties, or who jumped from minority staff under one admin to lobbying the
same committee under the other. Different story shape than "former agency
head," and the data supports it.

#### B.6 `disclosure-gap` skill

LDA filings have known blank-field problems. Audit filings for missing
required fields (issues, contribution amounts that don't sum, lobbyists
listed in narrative but not in the lobbyists table) and flag potential
non-compliance. Real DOJ-referrable angle.

### Tier C — Process / polish (low code, high credibility)

#### C.1 AP-style hook on `findings_report.md` and per-card exports

Joe Amditis ships one. Wire as a pre-commit on `findings/` and on the export
helpers in `web/src/app/lib/exports.ts`. Journalist judges will notice.

#### C.2 `/fair-guard story` — scaffold a publishable lede + nut graf

Pulls candidate + trail + comment status + §207 verdict; emits a draft a
reporter can edit. Saves grunt work; demonstrates end-to-end value.

#### C.3 Cross-session memory / autocontext

Pattern from `claude-skills-journalism`. Every time a reporter dismisses a
candidate ("not actually newsworthy because X"), append the reason to a
`lessons/` directory under the relevant skill so future runs filter the
noise.

#### C.4 Multi-agent verify pass before publish

Hagar's adversarial pattern: parallel agents independently re-check each
top-10 finding's role / trail / §207 numbers from scratch. Either bumps
verification confidence or flags drift. Cheap; large credibility gain.

#### C.5 Reporter-friendly diff view

Between scan runs, what changed? New candidates above threshold, candidates
that dropped off, deltas in money trail. Newsrooms care about *new* signals,
not the whole table re-served. Implement as `scripts/scan_diff.py` + a small
"What's new since last scan" strip at the top of the Findings page.

---

## 3. Recommended ordering (5 working days)

Adjust if comment-request replies arrive — that bumps "send + log responses"
forward.

| Day | Bucket | Tasks | Status |
|-----|--------|-------|--------|
| 1 | Gates | Add `LICENSE`. Capture `trace` interaction log. Add README sections (outside data / COI / legal-risk). Send the comment requests (calendar starts now). | ✅ Done 2026-06-06 — 4/4 gates closed; comment-request packets staged in `notes/comment_requests/` ready to send |
| 2 | Corpus completeness | Ship `pressrel` (A.1). This is the single biggest perception gain. | ✅ Done 2026-06-06 — 6th skill shipped end-to-end with 30 tests + 2 reproducible case files; 675 matches attached to 29/40 scan findings |
| 3 | Capability story | Pick **one** of `coi-graph` (B.1) or `fact-check` (A.2) and ship it cleanly rather than half-shipping both. Recommended: `coi-graph` — more differentiated. | ⬜ next |
| 4 | Polish | `comment-tracker` (A.3) + per-card one-pager PDF (A.4) + AP-style hook (C.1) + archive-on-cite (A.5) + Reporter UI route for `/pressrel`. | ⬜ |
| 5 | Proof | Re-run everything end-to-end on a clean clone. Recapture traces. Regenerate the PDF. Pin the four departure dates. Final README pass. | ⬜ |

---

## 4. Out-of-scope (deliberately not doing)

Listed so we don't get tempted mid-submission:

- **OCR / document ingestion.** Hagar covers this well but the LDA + press-
  release corpus is already structured. Adding OCR would be a different
  competition.
- **Full review interface like Hagar's prison-records UI.** Our Reporter UI
  is good enough for verification; building a per-record editor is a month
  of work for marginal scoring gain.
- **Outside-corpus enrichment beyond USAspending.** No FEC, no OpenSecrets,
  no LinkedIn scraping. Each one adds disclosure burden + reproducibility
  risk for a small information gain.
- **Newsletter / publishing skills.** Out of competition scope.

---

## 5. Open questions for the team

- Do we send the comment requests under a real outlet's masthead, or as
  "FairGuard investigators c/o the GAIN challenge"? The latter is honest but
  may get lower response rates. **Decision needed by Day 1.**
- For `coi-graph`, do we render the SVG in the UI or just ship the JSON +
  Graphviz file? UI is shinier; JSON is more reusable. **Probably both.**
- Do we want to support an in-UI annotation layer so a reporter can mark
  candidates as "dismissed / pursuing / confirmed" and have that persist?
  Useful but adds a real storage decision (file? localStorage? sqlite?).
  **Defer unless time on Day 5.**
