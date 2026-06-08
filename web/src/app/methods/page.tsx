/**
 * /methods — How the FairGuard pipeline works, what each skill claims,
 * what it deliberately does not claim. Reproducibility-first walkthrough,
 * written for a reporter (or judge) who has never seen the codebase.
 */

import Link from "next/link"

export const metadata = {
  title: "Methods — FairGuard",
  description:
    "How the FairGuard pipeline works: nine reusable agent skills, what they " +
    "claim, what they cannot claim, how to reproduce every finding from a clean clone.",
}

export default function Page() {
  return (
    <div className="max-w-4xl">
      <header className="mb-10">
        <h1 className="mb-4">Methods</h1>
        <p className="text-xl leading-relaxed text-slate-700">
          FairGuard is a pipeline of nine reusable agent skills that turn five years
          of Senate and House lobbying filings into reproducible investigative
          findings. This page walks through what each skill does, what it can / cannot
          claim, and the four editorial gates a reporter still has to clear before
          publication.
        </p>
        <p className="mt-3 text-base text-slate-600">
          For the canonical reproduction command, see{" "}
          <code className="rounded bg-slate-100 px-1 font-mono text-sm">README.md</code>.
          The whole pipeline is cross-platform (Linux, macOS, Windows) and CI-verified.
        </p>
      </header>

      {/* ── TOC ─────────────────────────────────────────────────────────── */}
      <nav className="mb-12 rounded-xl border border-slate-200 bg-slate-50 p-5">
        <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
          On this page
        </p>
        <ol className="ml-5 list-decimal space-y-1 text-base">
          <li><a href="#pipeline"  className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">Pipeline at a glance</a></li>
          <li><a href="#gates"     className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">The four editorial gates</a></li>
          <li><a href="#skills"    className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">Skill-by-skill walkthrough</a></li>
          <li><a href="#sources"   className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">Data sources</a></li>
          <li><a href="#caveats"   className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">Caveats and known limits</a></li>
          <li><a href="#reproduce" className="text-indigo-700 underline decoration-dotted hover:text-indigo-900">Reproducing from a clean clone</a></li>
        </ol>
      </nav>

      {/* ── Pipeline ────────────────────────────────────────────────────── */}
      <Section id="pipeline" title="Pipeline at a glance">
        <p>
          The pipeline is linear and idempotent — every step writes its output to disk,
          so a reporter can run any single stage without re-running the previous ones.
        </p>
        <PipelineDiagram />

        <p>
          Each box in the diagram corresponds to one Agent Skill. The dispatcher is{" "}
          <code className="rounded bg-slate-100 px-1 font-mono text-sm">/fair-guard</code>
          — typing <code className="rounded bg-slate-100 px-1 font-mono text-sm">/fair-guard scan</code>{" "}
          inside Claude Code runs the scan step end-to-end.
        </p>
      </Section>

      {/* ── Gates ───────────────────────────────────────────────────────── */}
      <Section id="gates" title="The four editorial gates">
        <p>
          Before publishing a causal claim about a candidate, FairGuard requires four
          gates to be cleared. The first two are tooling-driven; the last two are
          human editorial judgment.
        </p>
        <ol className="my-6 list-decimal space-y-4 pl-6">
          <li>
            <strong>Prior agency role.</strong> The LDA{" "}
            <code className="rounded bg-slate-100 px-1 font-mono text-sm">covered_position</code>{" "}
            field is a voluntary self-disclosure. Confirm via an authoritative source —
            agency staff directory (or Internet Archive snapshot), confirmation hearings,
            news archives — before naming the prior role in print.
          </li>
          <li>
            <strong>Money trail.</strong> Federal awards from the agency to the
            lobbyist&apos;s clients are recipient-name-verified against USAspending.gov.
            FairGuard distinguishes <Link href="/glossary#discretionary" className="font-semibold text-indigo-700 underline decoration-dotted">discretionary</Link>{" "}
            (competitively awarded grants — newsworthy) from routine program payments
            (commodity purchases, food aid, formulaic financing — context).
          </li>
          <li>
            <strong><Link href="/glossary#section-207" className="font-semibold text-indigo-700 underline decoration-dotted">§207 cooling-off</Link>.</strong>{" "}
            Was the timing legal? The LDA does <em>not</em> record the exact day a
            lobbyist&apos;s federal employment ended, only the title — so this is a
            manual check, usually via the agency&apos;s OIG report or news coverage
            of the personnel move.
          </li>
          <li>
            <strong>Request for comment.</strong> A drafted, sent, and documented
            request — or a documented refusal — closes this gate. The comment skill
            generates per-firm drafts and tracks events; see{" "}
            <Link href="/comments" className="font-semibold text-indigo-700 underline decoration-dotted">/comments</Link>.
          </li>
        </ol>
        <CalloutNote>
          The four gates are intentionally narrower than &ldquo;is this a story?&rdquo;
          A finding that clears all four is reportable; a finding that fails any of
          them is not yet. FairGuard does not score or rank the editorial weight of
          a story — that&apos;s the reporter&apos;s job.
        </CalloutNote>
      </Section>

      {/* ── Skills ──────────────────────────────────────────────────────── */}
      <Section id="skills" title="Skill-by-skill walkthrough">
        <SkillBlock
          id="doctor"
          name="doctor"
          fullName="setup-validator"
          purpose="Cross-platform setup check + onboarding"
          what="Verifies Python, uv, Node, npm, system dependencies, data dirs, and the DuckDB. Prints a colored pass/warn/fail checklist."
          how="uv run scripts/doctor.py (or /fair-guard doctor)"
          notes="Used by the CI workflow as the gate for clean-clone reproducibility. Exits 0 even with no corpus/DB (treats them as WARN, not ERROR)."
        />
        <SkillBlock
          id="index"
          name="index"
          fullName="lda-corpus-indexer"
          purpose="ETL: raw LDA dumps → DuckDB"
          what="Parses Senate JSON and House XML filings into Parquet (one file per source × quarter), then loads them into 11 DuckDB tables + 2 convenience views."
          how="uv run scripts/01_build_index.py (~2.5 hr full build, ~2 min --sample)"
          notes="Watch for the seven parser quirks documented in skill/lda-corpus-indexer/references/known_quirks.md — each one produces silent data loss if missed. Post-build invariants are checked by scripts/verify_build.py (34 checks)."
        />
        <SkillBlock
          id="resolve"
          name="resolve"
          fullName="entity-resolver"
          purpose="Fuzzy entity resolution"
          what="Builds an entity_map table that canonicalizes org and person names across the corpus (e.g. 'CARGILL INC' and 'Cargill, Incorporated' resolve to the same canonical entity)."
          how="uv run scripts/02_entity_resolver.py"
          notes="Reported F1 = 0.963 against a hand-labeled gold set. That ~4% error rate means a few fuzzy matches are wrong; the resolver flags low-confidence matches so a reporter can spot-check."
        />
        <SkillBlock
          id="scan"
          name="scan"
          fullName="revolving-door-detector"
          purpose="Find former officials lobbying their old agency"
          what="Ranks every LDA lobbyist by agency concentration × volume × seniority. Flags candidates whose covered_position names the same agency they now lobby. Produces findings.json — the input to every other step."
          how="uv run scripts/03_agency_concentration.py [--agency NAME] [--min-filings N]"
          notes="A high concentration is a structural signal — not proof of wrongdoing. Many former officials lobby because their expertise is valuable; the question is whether any individual case crosses §207 or generates a conflict-of-interest pattern worth investigating."
        />
        <SkillBlock
          id="trace"
          name="trace"
          fullName="federal-award-tracer"
          purpose="Follow the money to USAspending.gov"
          what="Queries the USAspending API for federal awards from the lobbyist's target agency to that lobbyist's clients. Verifies by recipient name (not by CIK or DUNS, which churn). Separates discretionary grants from routine program payments."
          how="uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/<case>.json"
          notes="The load-bearing judgment is the 'wide-net-first name-token discipline' — search the shortest distinctive core term, read every returned recipient, then keep same-company SPVs and exclude coincidental collisions. A too-narrow search undercounts by hundreds of millions silently."
        />
        <SkillBlock
          id="pressrel"
          name="pressrel"
          fullName="press-release-cross-ref"
          purpose="Find legislators already talking about these clients"
          what="Cross-references every congressional press release in the corpus for mentions of a finding's clients. Surfaces members who are already on the record (supporting or opposing) — a fair-comment lead."
          how="uv run scripts/05_pressrel_search.py --enrich-findings  (then per-case-file runs)"
          notes="Order matters: --enrich-findings must run before the per-case-file runs. Without it, alias matches get clobbered and coi-graph's triangle count drops."
        />
        <SkillBlock
          id="coi"
          name="coi"
          fullName="coi-graph"
          purpose="Compose scan + trace + pressrel into a conflict-of-interest graph"
          what="Builds a multi-edge graph of lobbyists, firms, agencies, clients, and legislators. Detects triangles (legislator ↔ client ↔ agency), hubs (clients connected to many lobbyists), and bridges (clients connecting otherwise-separate cases)."
          how="uv run scripts/06_coi_graph.py [--top N]"
          notes="Pure-Python SVG renderer (no Graphviz dependency). Output is deterministic given the same input."
        />
        <SkillBlock
          id="comment"
          name="comment"
          fullName="comment-tracker"
          purpose="Request-for-comment workflow"
          what="Per-firm drafts, send events, acknowledgments, substantive replies, follow-ups, and closures — a small state machine over JSON. Derives status + deadline pressure automatically."
          how="uv run scripts/07_comment_tracker.py log <firm> <event> ..."
          notes="The drafts themselves are written to notes/comment_requests/<firm>.md; this skill tracks the back-and-forth, not the prose."
        />
        <SkillBlock
          id="archive"
          name="archive"
          fullName="archive-on-cite"
          purpose="Snapshot every cited URL"
          what="Submits each cited URL to Wayback and Archive.today and records the snapshot URL. Findings + trails + press releases + comment drafts are all scanned."
          how="uv run scripts/08_archive_cite.py [--service wayback|archive_today]"
          notes="Run shortly before publication so links can't 404 you in the post-publication news cycle."
        />
      </Section>

      {/* ── Sources ─────────────────────────────────────────────────────── */}
      <Section id="sources" title="Data sources">
        <SourceRow
          name="U.S. Senate LDA"
          url="https://lda.senate.gov/"
          summary="Lobbying Disclosure Act filings, quarterly, 2022–Q1 2026. Public JSON dumps. Filed by the registrant (firm) under penalty of perjury. The covered_position field is voluntary; not validated by the Senate."
        />
        <SourceRow
          name="U.S. House Office of the Clerk LDA"
          url="https://lobbyingdisclosure.house.gov/"
          summary="House lobbying disclosures (XML). FairGuard reads both, but the scan currently ranks on Senate LDA only — including House would shift rankings."
        />
        <SourceRow
          name="USAspending.gov"
          url="https://www.usaspending.gov/"
          summary="Federal award database (contracts, grants, loans, direct payments). Used by trace. Recipient names are messy — FairGuard reads every returned recipient and keeps same-company SPVs while excluding coincidental collisions."
        />
        <SourceRow
          name="Congressional press releases"
          url="https://www.congress.gov/"
          summary="House + Senate official press releases, 2022–2026. Indexed by bioguide_id and filing quarter."
        />
      </Section>

      {/* ── Caveats ─────────────────────────────────────────────────────── */}
      <Section id="caveats" title="Caveats and known limits">
        <ul className="ml-5 list-disc space-y-3 text-base">
          <li>
            <strong>Senate LDA only for scan ranking.</strong> House filings are
            parsed and stored but not yet folded into the concentration ratio.
            Including them would shift rankings.
          </li>
          <li>
            <strong><code className="rounded bg-slate-100 px-1 font-mono text-sm">covered_position</code> is self-reported.</strong>{" "}
            Lobbyists fill it in themselves. Always verify against an
            authoritative source before naming the prior role in print.
          </li>
          <li>
            <strong>Resolver F1 = 0.963.</strong> Roughly 4% of fuzzy name matches
            are wrong. The resolver flags low-confidence matches; spot-check those.
          </li>
          <li>
            <strong>USAspending recipient names churn.</strong> A subsidiary&apos;s
            name may change between the lobbying filing and the award. FairGuard
            uses a wide-net-first search + manual recipient triage to catch these,
            but is not perfect.
          </li>
          <li>
            <strong>§207 timing is not recorded.</strong> The LDA does not include
            departure dates. The cooling-off check is a manual step (gate 3).
          </li>
          <li>
            <strong>Lobbying is legal.</strong> A structural pattern is not proof
            of wrongdoing. FairGuard surfaces conflict-of-interest <em>structure</em>,
            not corruption.
          </li>
          <li>
            <strong>This is not a real-time feed.</strong> The corpus runs through
            Q1 2026; refresh by re-running the index step against newer LDA dumps.
          </li>
        </ul>
      </Section>

      {/* ── Reproduce ───────────────────────────────────────────────────── */}
      <Section id="reproduce" title="Reproducing from a clean clone">
        <p>From a fresh checkout of the FairGuard repo:</p>
        <pre className="my-4 overflow-x-auto rounded-xl bg-slate-900 px-5 py-4 font-mono text-sm leading-relaxed text-slate-200">
{`git clone <repo> && cd northwestern-challenge
uv sync --extra dev
cd web && npm ci && cd ..

# Either: download the pre-built DuckDB (~10 min)
#   https://drive.google.com/drive/folders/1O_qsxmFitgRfyjPXsgyDSjrbX3L-1Vlf
# Or: run the full build (~2.5 hr)
uv run scripts/01_build_index.py
uv run scripts/verify_build.py

# Reproduce every artifact
uv run scripts/02_entity_resolver.py
uv run scripts/03_agency_concentration.py
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/limbaugh_interior.json
uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/usda_cases.json
uv run scripts/05_pressrel_search.py --enrich-findings    # MUST run first
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/limbaugh_clients.json
uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/usda_clients.json
uv run scripts/06_coi_graph.py
uv run scripts/07_comment_tracker.py export
uv run scripts/08_archive_cite.py

# Verify
uv run python -m pytest         # 261 tests
uv run ruff check scripts/
uv run scripts/09_ap_style_lint.py findings/findings_report.md`}
        </pre>
        <p>
          CI runs an abbreviated version of this on every push and PR (Linux, macOS,
          Windows). See <code className="rounded bg-slate-100 px-1 font-mono text-sm">.github/workflows/ci.yml</code>.
        </p>
      </Section>

      {/* ── Next ────────────────────────────────────────────────────────── */}
      <section className="mb-10 rounded-xl border border-indigo-200 bg-indigo-50 p-6">
        <h2 className="mb-3">Next</h2>
        <ul className="ml-5 list-disc space-y-2 text-base text-slate-800">
          <li>
            Browse the <Link href="/findings" className="font-semibold text-indigo-700 underline decoration-dotted">139 candidates</Link>.
          </li>
          <li>
            Look something up by <Link href="/search" className="font-semibold text-indigo-700 underline decoration-dotted">name</Link>.
          </li>
          <li>
            Read the <Link href="/glossary" className="font-semibold text-indigo-700 underline decoration-dotted">glossary</Link>{" "}
            for terms like <em>§207</em>, <em>LDA</em>, <em>ALI code</em>, <em>discretionary</em>.
          </li>
        </ul>
      </section>
    </div>
  )
}

// ── Components ───────────────────────────────────────────────────────────

function Section({
  id, title, children,
}: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mb-14 scroll-mt-32">
      <h2 className="mb-4">{title}</h2>
      <div className="space-y-4 text-base leading-relaxed text-slate-700">{children}</div>
    </section>
  )
}

function SkillBlock({
  id, name, fullName, purpose, what, how, notes,
}: {
  id: string
  name: string
  fullName: string
  purpose: string
  what: string
  how: string
  notes: string
}) {
  return (
    <article
      id={`skill-${id}`}
      className="mb-5 scroll-mt-32 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <header className="mb-3 flex flex-wrap items-baseline gap-3">
        <code className="rounded-md bg-indigo-50 px-2 py-1 font-mono text-base font-bold text-indigo-800 ring-1 ring-indigo-200">
          /fair-guard {name}
        </code>
        <span className="text-base font-semibold text-slate-700">{fullName}</span>
        <span className="text-sm italic text-slate-500">— {purpose}</span>
      </header>
      <dl className="space-y-2 text-base">
        <Row label="What it does">{what}</Row>
        <Row label="How to run">
          <code className="rounded bg-slate-100 px-1 font-mono text-sm">{how}</code>
        </Row>
        <Row label="Notes">{notes}</Row>
      </dl>
    </article>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[8rem,1fr] sm:gap-3">
      <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="text-slate-700">{children}</dd>
    </div>
  )
}

function SourceRow({
  name, url, summary,
}: { name: string; url: string; summary: string }) {
  return (
    <div className="mb-4 rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-1 flex flex-wrap items-baseline gap-2">
        <h3 className="text-lg font-bold text-slate-900">{name}</h3>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-sm text-indigo-700 underline decoration-dotted hover:text-indigo-900"
        >
          {url}
        </a>
      </div>
      <p className="text-base leading-relaxed text-slate-700">{summary}</p>
    </div>
  )
}

function CalloutNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-5 rounded-lg border border-amber-200 bg-amber-50 p-5">
      <p className="text-base leading-relaxed text-amber-900">{children}</p>
    </div>
  )
}

// ── Pipeline diagram ─────────────────────────────────────────────────────
//
// Visual flow alternating "data state" pills (slate) with "skill step" cards
// (colored). Each skill card anchors to its detail block lower on the page.

type SkillTone = "slate" | "violet" | "indigo" | "emerald" | "amber" | "rose"

const TONE_STYLES: Record<SkillTone, {
  border: string
  bg: string
  badge: string
  arrow: string
}> = {
  slate:   { border: "border-slate-300",   bg: "bg-slate-50",   badge: "bg-slate-700 text-white",     arrow: "text-slate-400"   },
  violet:  { border: "border-violet-300",  bg: "bg-violet-50",  badge: "bg-violet-600 text-white",    arrow: "text-violet-400"  },
  indigo:  { border: "border-indigo-300",  bg: "bg-indigo-50",  badge: "bg-indigo-600 text-white",    arrow: "text-indigo-400"  },
  emerald: { border: "border-emerald-300", bg: "bg-emerald-50", badge: "bg-emerald-600 text-white",   arrow: "text-emerald-400" },
  amber:   { border: "border-amber-300",   bg: "bg-amber-50",   badge: "bg-amber-600 text-white",     arrow: "text-amber-400"   },
  rose:    { border: "border-rose-300",    bg: "bg-rose-50",    badge: "bg-rose-600 text-white",      arrow: "text-rose-400"    },
}

type Stage = {
  skill: string
  skillAnchor: string
  what: string
  output: { label: string; detail: string }
  tone: SkillTone
}

const PIPELINE_START = { label: "Raw LDA dumps", detail: "8.6 GB · Senate JSON + House XML · gitignored under data/" }

const PIPELINE: Stage[] = [
  {
    skill: "index", skillAnchor: "skill-index", tone: "slate",
    what: "Parse JSON + XML into Parquet, then load into DuckDB",
    output: { label: "investigation.duckdb", detail: "≈3 GB · 11 tables + 2 views" },
  },
  {
    skill: "resolve", skillAnchor: "skill-resolve", tone: "violet",
    what: "Fuzzy entity resolution across org & person names",
    output: { label: "entity_map table", detail: "F1 = 0.963 against a hand-labeled gold set" },
  },
  {
    skill: "scan", skillAnchor: "skill-scan", tone: "indigo",
    what: "Rank former officials by agency concentration × volume × seniority",
    output: { label: "findings.json", detail: "139 candidates across 22 agencies" },
  },
  {
    skill: "trace", skillAnchor: "skill-trace", tone: "emerald",
    what: "USAspending awards from each agency to that lobbyist's clients",
    output: { label: "trails.json", detail: "Federal $ traced, recipient-name-verified" },
  },
  {
    skill: "pressrel", skillAnchor: "skill-pressrel", tone: "amber",
    what: "Congressional press releases mentioning each client (2022–2026)",
    output: { label: "press_releases.json", detail: "Legislators on the record" },
  },
  {
    skill: "coi", skillAnchor: "skill-coi", tone: "rose",
    what: "Compose scan + trace + pressrel into a conflict-of-interest graph",
    output: { label: "coi_graph.json", detail: "Triangles, hubs, bridges across cases" },
  },
  {
    skill: "comment", skillAnchor: "skill-comment", tone: "slate",
    what: "Request-for-comment workflow — sent, acknowledged, replied, overdue",
    output: { label: "comment_log.json", detail: "Per-firm event timelines" },
  },
  {
    skill: "archive", skillAnchor: "skill-archive", tone: "slate",
    what: "Snapshot every cited URL to Wayback + Archive.today",
    output: { label: "archive_registry.json", detail: "Durable citations before publication" },
  },
]

function PipelineDiagram() {
  return (
    <div className="my-8 rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-6 sm:p-8">
      <DataPill {...PIPELINE_START} kind="input" />
      {PIPELINE.map((stage, i) => (
        <StageGroup key={stage.skill} stage={stage} index={i} />
      ))}
      <div className="mt-6 flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
        <span aria-hidden className="mt-0.5 text-xl">📰</span>
        <p className="text-base leading-relaxed text-emerald-900">
          <strong>End of pipeline.</strong> Every artifact above is read by the web UI —
          a reporter then clears the <a href="#gates" className="font-semibold underline decoration-dotted">four editorial gates</a>{" "}
          and writes the story.
        </p>
      </div>
    </div>
  )
}

function StageGroup({ stage, index }: { stage: Stage; index: number }) {
  const tone = TONE_STYLES[stage.tone]
  return (
    <div>
      <Connector tone={stage.tone} />
      <Link
        href={`#${stage.skillAnchor}`}
        className={`block rounded-xl border ${tone.border} ${tone.bg} p-4 transition hover:shadow-md sm:p-5`}
      >
        <div className="flex flex-wrap items-center gap-3">
          <span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold tabular-nums ${tone.badge}`}>
            {index + 1}
          </span>
          <code className={`rounded-md px-2 py-1 font-mono text-sm font-bold ${tone.badge}`}>
            /fair-guard {stage.skill}
          </code>
          <p className="min-w-0 flex-1 text-base text-slate-800">{stage.what}</p>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Details ↓
          </span>
        </div>
      </Link>
      <Connector tone={stage.tone} />
      <DataPill kind="output" {...stage.output} />
    </div>
  )
}

function DataPill({
  kind, label, detail,
}: { kind: "input" | "output"; label: string; detail: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 shadow-sm">
      <span aria-hidden className="text-xl text-slate-400">
        {kind === "input" ? "📥" : "📄"}
      </span>
      <div className="min-w-0">
        <p className="font-mono text-base font-bold text-slate-900">{label}</p>
        <p className="text-sm text-slate-600">{detail}</p>
      </div>
    </div>
  )
}

function Connector({ tone }: { tone: SkillTone }) {
  const t = TONE_STYLES[tone]
  return (
    <div className="flex items-center justify-center py-1.5" aria-hidden>
      <svg
        viewBox="0 0 24 24"
        className={`h-6 w-6 ${t.arrow}`}
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 4v16M6 14l6 6 6-6" />
      </svg>
    </div>
  )
}

