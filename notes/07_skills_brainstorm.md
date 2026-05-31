# Skills & Features Brainstorm — Next-Big-Thing for FairGuard

**Date:** 2026-05-30
**Author:** Archit (draft, not yet reviewed with Mokshit)
**Purpose:** Deep technical and domain-specific brainstorm of what FairGuard could add — new skills, adopted-and-credited external skills, reporter-facing tooling, and orchestration layers — that would (a) make us stand out vs. other submissions and (b) genuinely help a working journalist with this corpus.

---

## 1. Where we sit today

We have four skills:

| Mode | Status | Submission dimension served (strongest) |
|------|--------|-----------------------------------------|
| `doctor` | ✅ | Reproducibility (the implicit gate) |
| `index` | ✅ | Token efficiency (heavy lifting off the agent) |
| `scan` | ✅ | Tool assistance (novel: concentration ratio) |
| `resolve` | 🚧 planned | Tool assistance |

We are **strong** on:
- Reproducibility (Docker, `uv`, `doctor`, pre-built DuckDB Drive link)
- Token efficiency (Parquet + DuckDB do all aggregation deterministically)
- One novel tool-assist capability (Bridenstine-pattern detector)

We are **weak** on:
- **Orchestration.** No persistent investigation state. The agent re-derives context each session. The reporter UI displays static JSON; it doesn't capture "what I've checked", "what's verified", "what's cold".
- **Verification.** Every finding ends with a paragraph saying "verify against external sources". The skills don't *help* with that step. The hardest part of the workflow is the part we punt on.
- **Press release exploitation.** 141K press releases sit largely unused. The original "say-vs-pay" plan was scoped out. This is the corpus's most distinctive asset and we are wasting it.
- **Contribution data.** 636K rows in `senate_contributions` is fully untouched. Political contribution flows are the second-most-investigated lobbying angle (after revolving door).
- **Cross-chamber analysis.** `scan` runs on Senate only. House data is parsed but unused for findings.
- **Time-series anomalies.** We have ~17 quarters of data and have not done a single longitudinal slice.

Judges score four dimensions equally (orchestration, efficiency, verification, tool assistance), gated by reproducibility. Reading the rubric literally: **shipping one more strong "scan" wins us less than shoring up orchestration + verification**, because the marginal point on tool assistance plateaus once we have one novel skill, and the other two dimensions are near zero.

The competition writeup says the same thing in the announcement: "the system to leave behind evidence of what it did, where its claims came from, which decisions were made by a person."

---

## 2. What a working journalist actually needs with THIS corpus

Sit at a journalist's desk for an hour with `output/agency_concentration.md` open and ask: what's the next thing I'd want?

**The reporter workflow after running `scan`:**

1. They see "BENJAMIN STEINBERG (ENERGY) — 90.2% concentration". What now?
2. They need to verify Steinberg actually held a senior role at DOE → external lookup (LinkedIn, agency staff directories, news archives).
3. They need to see who Steinberg's clients are and what those clients want from DOE → DuckDB query, but they'd have to write it.
4. They need to check whether the cooling-off period (18 USC §207) applied and when it expired → date math.
5. They need to know whether Steinberg's clients have active DOE contracts → USAspending.gov lookup.
6. They want to know who else at Venn Strategies is in the same situation → fan-out query.
7. They want to look at Steinberg's filings *over time* — did the concentration shift after a specific event? → quarterly time series.
8. They want to cross-check whether the issues Steinberg lobbies on align with what DOE-friendly members of Congress were talking about that quarter → press release join.
9. They draft a comment-request email to Venn Strategies' communications contact → boilerplate they reuse.
10. They draft a freedom-of-information request for related agency correspondence → another piece of boilerplate.
11. They want to keep a running notebook of what's verified vs. open across all 106 candidates so they don't lose track between sessions.
12. They need to export a *defensible* evidence packet for the editor and lawyer.

Steps 2–12 are mostly unsupported today. Every one is a candidate skill.

---

## 3. Top 5 highest-leverage additions (the "next big thing")

Ranked by impact on judging × feasibility before July 15.

### #1 — `investigation-notebook` (orchestration, table-stakes)

A persistent, file-backed investigative notebook that both the agent and the reporter can read/write across sessions. Replaces the "agent re-derives everything each session" anti-pattern.

**Concrete shape:**

- A `notebook/` directory in the project, gitignored by default (reporter-private), one markdown file per **subject of interest** (e.g., `notebook/steinberg-doe.md`, `notebook/artemis-group.md`).
- A YAML frontmatter on each file with structured state: `status: open | verified | dismissed | needs-comment`, `last_checked`, `assigned_to`, `risk_flags`, `next_action`, `external_links`.
- A `notebook/_index.md` (auto-maintained by the skill) listing every subject with status + a 1-line description.
- A `notebook/_queue.md` ranked priority queue of unverified leads — agent surfaces top 10 on session start.
- The skill provides verbs: `open <subject>`, `note <subject> "..."`, `verify <subject> --source <url>`, `dismiss <subject> --reason "..."`, `link <subject-a> <subject-b>`.

**Why this scores hard:**
- Directly maps to the orchestration rubric ("strong skill keeps track of what's been checked, what's still open, which entities matter, and which threads went cold, so the journalist doesn't have to re-brief the agent every time they come back").
- Composable across every other skill — every other skill writes its findings *into* the notebook, every other skill can read prior state.
- File-based = inspectable, diffable, version-controllable. No hidden agent state.

**Inspiration to credit:**
- `jamditis/claude-skills-journalism` — `autocontext` plugin (lessons accumulate per-skill across sessions). Different goal (skill evolution vs. investigation state) but architecture is similar.
- `jamditis/claude-skills-journalism` — `project-memory` and `project-retrospective` patterns.

**Effort:** 2–3 days. The agent verbs are markdown manipulation. The hard part is designing the schema so it doesn't drift.

---

### #2 — `say-vs-pay-tracker` (tool assistance + new finding capability)

Cross-references what members of Congress *say* publicly (press release topics by quarter) with who is *paying* to lobby on the same issues in the same quarter. Originally planned in `notes/03_skill_packaging_plan.md` then dropped when Track 2 became `scan`. Bringing it back, in a leaner form.

**Concrete shape:**

- Maps press release text → ALI issue codes via a small local classifier (TF-IDF + logistic regression, or a thin sentence-transformers similarity model against ALI-code seed sentences). No LLM tokens consumed per release.
- For each `(bioguide_id, ali_code, quarter)`: count press releases on that topic and total lobbying spend on that topic targeting that chamber.
- Surfaces "divergence" rankings — members with *low* press output but high incoming lobby pressure (silent recipients), and members with *high* press output and matching corporate lobby flow (potentially coordinated).
- Outputs a sortable table; also writes a Mokshit-style "structural finding" markdown that lists the top 30.

**Why it's the second big bet:**
- It's the natural extension of the corpus and the *only* finding type that uses press releases. Without it, the press release dump is dead weight in our submission.
- "Say-vs-pay" is one of the most legible investigative framings to a non-technical judge. Anyone can read it.
- Mechanically novel — no public tool I know of joins LDA quarterly spend with bioguide-keyed press release output.

**Risks to call out up front:**
- ALI codes are coarse (76 codes). Classifier needs to map free press-release text to that taxonomy — easy on "HCR" (healthcare), hard on "TAX" vs "BUD".
- Press releases are non-uniform: some members publish dozens/quarter, some publish two. Need to normalize. Spell out methodology so the judge can audit.

**Effort:** 4–6 days. Build the classifier on a hand-labeled 200-sample seed (1 day). Run on 141K releases (1 hour). SQL join + scoring (1 day). Write up structural finding (2 days).

---

### #3 — `evidence-packet` (verification, the editor-defense layer)

For any single subject (a person, a firm, a finding), produce a **frozen evidence packet** — a self-contained directory the editor / lawyer can review without re-running the agent.

**Concrete shape:**

```
evidence/steinberg-doe/
  claims.md                   # human-readable: every claim with citation
  filings.csv                 # every Senate/House row supporting the claims
  press_releases.csv          # any matched press releases
  source_paths.txt            # filenames of the raw JSON/XML rows used
  queries.sql                 # exact DuckDB queries that produced claims.md
  external_links.md           # links to LDA.senate.gov, USAspending, news refs
  archive_urls.md             # Wayback snapshots of each external link
  checksums.txt               # SHA-256 of every artifact above
  README.md                   # how to re-verify this packet from scratch
```

The skill takes a subject identifier (from the notebook) and produces this dir on demand. Re-runnable, so updates are mechanical.

**Why this scores hard:**
- Directly maps to the verification rubric: "presents evidence in a form that's fast to review, and leaves a trace an editor could audit without re-doing the work."
- The competition expects this kind of artifact from the *findings report* but doesn't ask the *skill* to produce it. We're the team that does both.

**Effort:** 2 days. Mostly templating + a Wayback fetch utility.

**Adopted external pieces (credit):**
- `jamditis/claude-skills-journalism` — `web-archiving` skill — exact pattern for Wayback / Archive.today multi-redundancy.

---

### #4 — `contribution-tracer` (new finding capability, exploits unused data)

The `senate_contributions` table has 636K political contribution rows. They are sourced from the LDA "LD-203" semi-annual contribution reports, embedded in the same JSON dump as filings. Every row links a registrant (lobbying firm) to a payee (PAC, candidate, party) with an amount.

**Concrete shape:**

- For each `(registrant, payee)` pair, compute total $ flow per cycle.
- Cross-reference payees → bioguide_id → committee memberships → agencies of jurisdiction.
- Surface: "Firm X gave $Y to members of Committee Z while filing N lobbying disclosures targeting Agency A under Committee Z's jurisdiction." That's a one-sentence headline.
- Cross-reference: "Firm X lobbied for client Y at agency A. Members of committees with jurisdiction over A received $Z from firm X in the same period."

**Why this matters:**
- We are leaving the second-most-investigated lobbying angle entirely on the table.
- The data is already in the database; this is just queries + scoring.
- Pairs naturally with `scan` — same firms, different lens.

**Risks:**
- LD-203 reports differ from FEC reports. Need to flag the distinction in methodology.
- Personal-vs-PAC contributions need separation.

**Effort:** 3–4 days for a single-finding-grade version.

---

### #5 — `comment-request-drafter` (verification + journalism workflow)

When a reporter is ready to publish a claim about a named person/firm, journalism ethics requires a comment request. Drafting this email well is repetitive and high-stakes — a good template is reusable across 106 subjects.

**Concrete shape:**

- Input: a notebook subject file + a draft finding.
- Output: a comment-request email tailored to that subject. Includes:
  - Subject line, opening with deadline.
  - The specific claims being made (verbatim from the finding).
  - The questions the reporter would like answered.
  - The records the reporter has (filing UUIDs, not for sharing, but to signal seriousness).
  - The publication offer-of-response window.
- Also generates the **FOIA / records request** for any agency communications that would corroborate or rebut.

**Inspiration to credit:**
- `jamditis/claude-skills-journalism` — `story-pitch` and `foia-requests` skills. Adopt-and-adapt rather than rebuild.
- `fdaudens/ai-journalism-skills` — `fact-checker` general workflow.

**Effort:** 1–2 days, mostly templating.

---

## 4. Second tier — strong adds, lower urgency

### #6 — `bioguide-bridge` (cross-corpus connective tissue)

A small skill that maps `bioguide_id` (press releases) ↔ canonical member name ↔ chamber ↔ committee assignments ↔ party ↔ state. This is connective tissue every other skill needs. Built once, reused everywhere.

**Why it matters:** The lobbying corpus identifies committees and chambers; press releases identify members by `bioguide_id`. To do *any* member-level analysis, this bridge has to exist. We've been ad-hoc'ing it.

**Data source:** [bioguide.congress.gov](https://bioguide.congress.gov/) — public, no API key, JSON endpoint per member, plus a bulk YAML at `unitedstates/congress-legislators` (well-known public-domain).

**Effort:** 1 day.

---

### #7 — `cooling-off-checker` (legal-risk verification helper)

Given `(lobbyist_name, prior_role, prior_agency_exit_date, first_lobbying_filing_date)`, evaluate cooling-off period status per 18 USC §207. Flags potential violations + the boundary cases (post-presidential, ≥ Executive Schedule II, "very senior", "senior").

**Why it matters:** Bridenstine's cooling-off expired clean. Many of the other 106 cases might not. We need to be able to say "this case has cooling-off concerns" or "this case is post-cooling-off" with confidence before publishing.

**Risks:** Statutory interpretation is hard. The skill should output **status candidates + the statutory cite** for a lawyer to confirm, not a legal opinion.

**Effort:** 2 days (mostly mapping prior roles → cooling-off tier).

---

### #8 — `external-corroboration` (multi-source verification)

Given a finding subject, fan out to public sources to corroborate biographical claims:

- USAspending.gov API → has the subject's *clients* received federal contracts from the subject's *former agency*?
- congress.gov API → bill texts containing client / agency names.
- Wayback Machine → archived versions of the subject's LinkedIn / firm website at relevant dates.
- News archive search (one of Google News, NYT API, AP, ProQuest if available).
- LDA.senate.gov form view URL for each cited filing.

Output: a corroboration matrix per claim. Score how strongly each external source confirms.

**Inspiration to credit:**
- `jamditis/claude-skills-journalism` — `source-verification` skill (SIFT method, multi-archive redundancy).
- `fdaudens/ai-journalism-skills` — `osint` skill (Bellingcat / IDI tools).

**Effort:** 3–4 days. API integrations are the bulk; the logic is straightforward.

---

### #9 — `issue-spike-detector` (anomaly detection on time series)

For each ALI code, build a quarterly time series of disclosed spend / filing count. Detect statistically significant spikes (z-score > 3 over 4-quarter rolling baseline). Cross-reference: who drove the spike — which firms entered, which firms scaled up?

**Example output:**
> "Q3 2024 cryptocurrency (FIN) filings spiked 4.2σ above the 2023 baseline. 73% of new filings came from three firms: A, B, C. Firm A's largest client was X."

**Why it matters:** Spike → news event → story. Pure pattern detection. Cheap to run; surfaces fresh leads.

**Effort:** 2 days.

---

### #10 — `bill-shadow-tracker` (issue-specific lobbying lens)

Given a bill number (S.XXXX, H.R.XXXX), find every filing whose `specific_lobbying_issues` text mentions it, plus the firms, clients, and agencies behind. Cross-reference press releases citing the bill.

**Why it matters:** Reporters often arrive with a *bill* in mind, not a *firm*. This pivots the entire corpus around a bill identifier.

**Effort:** 1–2 days. SQL + a regex for bill citations.

---

### #11 — `network-graph` (visual investigation tool)

Output a JSON-LD or Cytoscape-compatible graph of a firm's network: lobbyists → firm → clients → agencies → issues. Reporter UI renders it. Reporter can expand a node and see the underlying filings.

**Why it matters:** Pictures sell stories. Also surfaces multi-hop connections (e.g., shared clients between firms, shared lobbyists between firms).

**Risks:** Visualization libraries are heavy. Keep it minimal — single Sigma.js page, not a full app.

**Inspiration:** `fdaudens/ai-journalism-skills` — `scrolly-sveltekit` pattern for scroll-driven narrative if we want to be ambitious; otherwise plain React component in the existing Next.js app.

**Effort:** 2 days for the data export, 2 days for the UI.

---

### #12 — `freshly-registered-detector` (new-firm anomaly)

Find firms whose first Senate or House filing is within the last 4–6 quarters, staffed by ≥1 person whose `covered_position` indicates senior agency exit. The Bridenstine-firm-emergence pattern. We caught Artemis; how many *other* freshly-registered firms with this DNA exist?

**Why it matters:** `scan` finds firms with established concentration. This catches firms *as they emerge* — earlier journalism intervention.

**Effort:** 1–2 days. Reuses `scan` infrastructure.

---

### #13 — `client-defection-tracer` (book-of-business movement)

A senior staffer leaves Firm A and starts at Firm B. Do they bring clients with them? Compute: clients first appearing at Firm B within ±2 quarters of a departing lobbyist's first filing there.

**Why it matters:** Reveals informal-capture relationships in the lobbying industry. Pattern is well-known in fintech / pharma but rarely quantified.

**Effort:** 2 days.

---

## 5. Third tier — "nice if we have time"

| Skill | One-line |
|---|---|
| `dormant-firm-detector` | Registered firms with zero filings (potential shells). |
| `outlier-income-flag` | Firms with extreme income/filing ratios (over/under-reporting). |
| `client-overlap-mapper` | Pairs of firms that share unusual clients. |
| `gov-entity-resolver` | Expand `AGENCY_REGISTRY` to all federal entities + parent-child mapping. |
| `top-firms-quarterly` | Auto-refresh league tables. |
| `firm-deathwatch` | Firms whose filings dropped sharply (lost a major client?). |
| `lobbyist-mobility-index` | Per-lobbyist count of firm transitions (high mobility = mercenary). |
| `cross-chamber-discrepancy` | Filings on one side but not the other when both are expected. |
| `text-similarity-on-issues` | Cluster lobbying-issue text strings (same lobby campaign, different filers). |

---

## 6. External skills to ADOPT (with credit)

This is the "import a community skill, adapt it as a mode, credit upstream" play. The competition values reuse; we get to point to the canonical authors rather than rebuilding.

| Adopted skill | Upstream author | What we'd change |
|---|---|---|
| `web-archiving` | [Joe Amditis](https://github.com/jamditis/claude-skills-journalism) | Use as-is to back the `evidence-packet` skill. |
| `foia-requests` | Joe Amditis | Pre-template for "agency comms about $LOBBYIST during $WINDOW" — FOIA boilerplate parameterized by `notebook` subject. |
| `source-verification` | Joe Amditis | Wire into the comment-request and external-corroboration flows. |
| `interview-prep` | Joe Amditis | When a reporter is ready to interview a subject, generate a context dump from the notebook. |
| `fact-checker` | [Florent Daudens](https://huggingface.co/spaces/fdaudens/ai-journalism-skills) | Adapt the multi-source fact-check workflow to specifically check LDA-sourced claims. |
| `osint` (Buried Signals curated) | via Florent Daudens | Add as a reference card in `evidence-packet` — when a reporter needs OSINT tools beyond what we provide. |
| `data-journalism` | Joe Amditis | Style guide enforcement for findings markdown — chart conventions, methodology section. |
| `newsroom-style` (AP style) | Joe Amditis | Run over `findings_report.md` before PDF export. |
| `ai-writing-detox` | Joe Amditis | Same — strip AI-slop patterns from our own writeups before submission. |
| `page-monitoring` | Joe Amditis | Watch the LDA archive for *new* filings related to subjects in the notebook. (Operationally interesting after submission, too.) |

**Implementation:** Add a `skill/adopted/<upstream-name>/SKILL.md` directory per adopted skill, with frontmatter listing original author + URL + license + a "Changes from upstream" note. Don't fork-and-divorce; symlink or vendor at a known commit. Document the version pin.

**License care:** Joe Amditis's repo is MIT; Florent Daudens's HF space doesn't state license clearly — check before vendoring, or just reference / link rather than vendor.

---

## 7. UI / reporter-facing extensions

The existing reporter UI shows static `findings.json`. To match what the skills above produce, we'd want:

1. **Notebook view** — list of subjects from `notebook/_index.md`, status chips, last-edited timestamp. Click into a subject to see its notes + linked evidence packet.
2. **Evidence-packet viewer** — open the frozen `evidence/<subject>/` dir, render `claims.md` with inline links to `filings.csv` rows and external links.
3. **Network panel** — Cytoscape/Sigma rendering of a firm's network (from #11).
4. **Time-series panel** — quarterly spend chart per firm or per issue (for #9).
5. **Say-vs-pay panel** — bioguide-keyed scatter or heat map (for #2).
6. **Comment-request draft pane** — render the email + a one-click "copy to clipboard" / "open in mail client".

Most of these are React components on the existing Next.js app. Keep data flow file-based (read JSON / markdown from disk on the server) so the reporter doesn't need a backend. Document this pattern explicitly in `web/README.md` so a judge can run it.

---

## 8. Architectural moves

### 8.1. Move from "static findings" to "investigation-as-state"

Today: `scripts/03_agency_concentration.py` produces `findings.json` once. The UI is read-only. If a reporter dismisses a finding ("Steinberg's Wikipedia confirms his role wasn't actually senior"), there's nowhere to record that decision.

Proposal: every finding lands in the **notebook** as a subject, status = "open". The reporter and the agent can both update it. The UI reflects current state, not the original scan output. The `scan` script becomes one *source* of subjects among others.

This is the single biggest architectural change. It's what turns FairGuard from "a clever query" into "an investigation environment."

### 8.2. Standardize on a "subject identifier" across skills

Today each skill names entities differently (`lobbyist_name` upper-case, `registrant_name` mixed case, etc.). Introduce a stable **subject ID** — e.g., `lda://lobbyist/{registrant_id}/{normalized-name}` — that the notebook, evidence packets, network graph, and comment requests all use. The `resolve` skill produces it; everyone else consumes it.

This unblocks composition. Without it, every skill has to redo entity resolution and skills can't reference each other's outputs cleanly.

### 8.3. Make every skill emit "events" to a shared log

A simple JSONL: `investigation.log.jsonl`. Every skill invocation appends `{ts, skill, action, subject, summary, files_written}`. The notebook displays a session timeline. Traces are derived from this log instead of being copy-paste artifacts.

Side benefit: directly addresses the competition's "interaction traces" requirement. Instead of manually pasting chat logs, we have a structured machine-readable trace.

---

## 9. Things to NOT build

Worth explicitly listing so we don't waste budget:

- **A general-purpose RAG/embedding index.** Tempting but wrong dimension to compete on — judges value deterministic tools, not yet-another-vector-store. The press release semantic search inside `say-vs-pay-tracker` is the only embedding use that earns its keep.
- **A "chat with the data" web UI.** Already exists in Claude Code itself; building a worse copy is anti-leverage.
- **Anything requiring API keys we don't have or can't budget.** No paid GPT/Claude inside the pipeline, no scraping behind paywalls, no Twitter/X API.
- **An entity-resolver that aims for F1 > 0.95.** The plan capped at 0.92 for good reason. Resolvers are a black hole.
- **A bespoke graph database.** DuckDB + Parquet is plenty. Adding Neo4j is reproducibility-hostile.
- **A heavy plugin/marketplace system.** Use the existing `modes/` architecture. Don't invent new packaging.

---

## 10. Prioritized roadmap (recommendation)

If we have 6 weeks to July 15:

**Weeks 1–2 (the orchestration-and-verification bet):**
1. `investigation-notebook` — orchestration. Highest leverage on a weak dimension.
2. `evidence-packet` — verification. Pairs with #1.
3. `bioguide-bridge` — connective tissue. Required by 4, 5, 9.

**Weeks 3–4 (the data-exploitation bet):**
4. `say-vs-pay-tracker` — second flagship finding. Uses press releases.
5. `contribution-tracer` — third flagship finding. Uses contributions.

**Week 5 (the verification-workflow polish):**
6. `comment-request-drafter` — verification layer.
7. `cooling-off-checker` — legal-risk helper.
8. Adopt + credit 4–6 upstream skills (web-archiving, foia-requests, source-verification, fact-checker, newsroom-style, ai-writing-detox).

**Week 6 (submission polish):**
9. Reporter UI extensions for notebook + evidence packets.
10. `issue-spike-detector` if time remains (otherwise drop to v2).
11. Re-record traces to use `investigation.log.jsonl`.
12. Findings report PDF export.

If we have only 3 weeks: cut tier 2 and 3 entirely, keep #1, #2, #3, #4, #5 from the top-5 list. The bet is on orchestration + verification + one new finding type, not on quantity.

---

## 11. What makes us *unique* (the elevator pitch for judges)

> FairGuard treats agentic investigative journalism as an *environment*, not a one-shot query. The skills are composable: `index` builds the corpus, `resolve` provides stable subject IDs, `scan` and `say-vs-pay` and `contribution-tracer` surface findings, `investigation-notebook` carries state across sessions, `evidence-packet` makes every finding editor-defensible, and `comment-request-drafter` produces the journalism artifacts that go out the door. Every skill writes to a shared event log that doubles as the interaction trace. A reporter can pause mid-investigation, come back two weeks later, and pick up exactly where the agent left off — with every claim still sourced to a specific filing UUID and every external link archived.

The Bridenstine finding is the demo. The 106-candidate ranking is the structural extension. The notebook + evidence packet is the *infrastructure that makes it actually shippable as journalism*. That's the gap most submissions will leave open, and it's the gap the rubric is targeting.

---

## 12. Open questions for Mokshit

- Top 5 list (§3) — agree on the ranking? My priors: orchestration is the biggest gap. Disagree if you think `say-vs-pay` is unrealistic in the timeframe.
- Adopted-skill credit pattern — vendor at a pinned commit vs. document-only reference. Vendoring is more reproducible but bigger repo. Vote?
- Notebook directory: gitignored by default (reporter-private) or checked in (transparent)? I lean gitignored with a `notebook/example/` sample checked in.
- Findings report PDF format — straight markdown export, or do we use `pdf-design` / `pdf-playground` from jamditis for a branded look?
- For say-vs-pay: do we hand-label 200 press releases for the ALI classifier, or pay for one Sonnet pass over a 1000-release sample and use that as the training set?
