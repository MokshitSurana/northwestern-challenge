/**
 * FairGuard — Landing page
 *
 * Oriented at a journalist (or judge) landing on the site cold. Goal: in ~30
 * seconds, answer "what is this, why does it matter, where do I start?"
 *
 * Numbers are computed at build time from the four authoritative JSON files
 * already shipped in web/public/ (findings, trails, press_releases, comment_log).
 * No client-side fetch — the landing has to render even with JS disabled.
 */

import Link from "next/link"
import findingsData from "../../public/findings.json"
import trailsData from "../../public/trails.json"
import pressrelData from "../../public/press_releases.json"
import commentData from "../../public/comment_log.json"
import type {
  CommentLogPayload,
  Finding,
  FindingsPayload,
  PressrelPayload,
  TrailsPayload,
} from "./types"
import { findingSlug } from "./lib/exports"

export const metadata = {
  title: "FairGuard — Federal lobbying, audited",
  description:
    "Reusable agent skills for investigative reporting on federal lobbying. " +
    "Find former officials lobbying their old agency, trace the federal money, " +
    "cross-reference congressional press releases, request comment.",
}

const fmtUSD = (n: number) =>
  n >= 1_000_000_000
    ? `$${(n / 1_000_000_000).toFixed(2)}B`
    : n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(0)}M`
      : `$${n.toLocaleString()}`

export default function Page() {
  const findingsPayload = findingsData as FindingsPayload
  const trailsPayload = trailsData as TrailsPayload
  const pressrelPayload = pressrelData as PressrelPayload
  const commentPayload = commentData as CommentLogPayload

  const findings: Finding[] = findingsPayload.findings ?? []
  const agencyCount = new Set(findings.map((f) => f.agency_short)).size
  const totalTraced = trailsPayload.trails.reduce((s, t) => s + (t.total ?? 0), 0)
  const totalDiscretionary = trailsPayload.trails.reduce(
    (s, t) => s + (t.discretionary_total ?? 0),
    0
  )
  const totalPressMatches = pressrelPayload.reports.reduce(
    (s, r) => s + (r.n_matches ?? 0),
    0
  )
  const distinctLegislators = new Set(
    pressrelPayload.reports.flatMap((r) =>
      r.matches.map((m) => m.member_name)
    )
  ).size
  const commentEntries = commentPayload.entries ?? []
  const commentSent = commentEntries.filter((e) =>
    ["sent", "acknowledged", "awaiting_substantive", "responded",
     "closed_response", "closed_no_response", "escalated_to_counsel",
     "no_response_by_deadline"].includes(e.status)
  ).length

  const topThree = findings.slice(0, 3)

  return (
    <div>
      {/* Hero ───────────────────────────────────────────────────────────── */}
      <section className="mb-12">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-semibold text-indigo-800 ring-1 ring-indigo-200">
            Northwestern GAIN — Agentic AI Investigative Journalism Challenge
          </span>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200">
            9 reusable agent skills
          </span>
        </div>
        <h1 className="mb-5 max-w-3xl">
          Federal lobbying, audited — so reporters can spend their time on the story.
        </h1>
        <p className="max-w-3xl text-xl leading-relaxed text-slate-700">
          FairGuard turns five years of Senate and House lobbying filings, USAspending
          award data, and congressional press releases into a single audit trail.
          Find former officials lobbying their old agency, follow the federal money,
          see which legislators are already talking about the same clients, then send
          a fair request for comment — with every claim traceable back to a filing UUID.
        </p>

        {/* Primary CTA row */}
        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            href="/findings"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-lg font-semibold text-white transition hover:bg-indigo-700"
          >
            See the {findingsPayload.total_candidates} candidates →
          </Link>
          <Link
            href="/search"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-lg font-semibold text-indigo-700 ring-1 ring-indigo-300 transition hover:bg-indigo-50"
          >
            Look up a name
          </Link>
          <Link
            href="/methods"
            className="text-base font-semibold text-slate-600 underline decoration-dotted underline-offset-4 hover:text-slate-900"
          >
            How does this work?
          </Link>
        </div>
      </section>

      {/* Headline numbers ────────────────────────────────────────────────── */}
      <section className="mb-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <HeadlineStat
          label="Structural candidates"
          value={findingsPayload.total_candidates.toLocaleString()}
          sub={`across ${agencyCount} agencies`}
        />
        <HeadlineStat
          label="Federal $ traced"
          value={fmtUSD(totalTraced)}
          sub={`${fmtUSD(totalDiscretionary)} discretionary`}
        />
        <HeadlineStat
          label="Press-release hits"
          value={totalPressMatches.toLocaleString()}
          sub={`${distinctLegislators} legislators on the record`}
        />
        <HeadlineStat
          label="Comment requests sent"
          value={`${commentSent} / ${commentEntries.length}`}
          sub="drafted, sent, awaiting reply"
        />
      </section>

      {/* Four big tiles ─────────────────────────────────────────────────── */}
      <section className="mb-14">
        <h2 className="mb-5">Where do I start?</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          <Tile
            tone="indigo"
            badge="1. Browse"
            title="Findings"
            href="/findings"
            body="139 ranked candidates: former officials whose lobbying is concentrated on their old agency. Filter by agency, expand any card to see the money trail."
            cta="Open findings →"
          />
          <Tile
            tone="emerald"
            badge="2. Follow the money"
            title="Money trails"
            href="/trails"
            body="USAspending awards from each agency to that lobbyist's clients, recipient-name-verified. Discretionary grants are flagged separately from routine program payments."
            cta="See trails →"
          />
          <Tile
            tone="amber"
            badge="3. Cross-reference"
            title="Press releases"
            href="/pressrel"
            body="Every time a member of Congress has named one of these clients in an official press release since 2022. Useful for finding legislators already on the record."
            cta="See press releases →"
          />
          <Tile
            tone="rose"
            badge="4. Visualize"
            title="Conflict graph"
            href="/graph"
            body="Interactive D3 force graph that composes scan + trace + pressrel. Triangles, hubs, and bridges between agencies, firms, clients, lobbyists, and legislators."
            cta="Open the graph →"
          />
        </div>

        {/* Secondary row */}
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <Tile
            tone="slate"
            badge="5. Outreach"
            title="Comment requests"
            href="/comments"
            body="Per-firm request-for-comment tracker: drafted, sent, acknowledged, replied, overdue. Powered by the comment skill — verifiable email trail before publication."
            cta="See outreach status →"
          />
          <Tile
            tone="slate"
            badge="By name"
            title="Inverse search"
            href="/search"
            body="Already working a story? Type a lobbyist, firm, client, agency, or legislator and see everything FairGuard has on them in one view."
            cta="Open search →"
          />
        </div>
      </section>

      {/* Top three findings ─────────────────────────────────────────────── */}
      {topThree.length > 0 && (
        <section className="mb-14">
          <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
            <h2>Today&apos;s top three</h2>
            <Link
              href="/findings"
              className="text-base font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
            >
              See all {findingsPayload.total_candidates} →
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {topThree.map((f) => (
              <Link
                key={`${f.rank}-${f.lobbyist_name}`}
                href={`/findings/${findingSlug(f)}`}
                className="group flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
              >
                <div className="mb-3 flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">
                    {f.rank}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-slate-700">
                    {f.agency_short}
                  </span>
                  <span className="ml-auto tabular-nums text-sm font-semibold text-rose-700">
                    {Math.round(f.concentration * 100)}%
                  </span>
                </div>
                <p className="mb-1 text-base font-bold leading-tight text-slate-900 group-hover:text-indigo-700">
                  {f.lobbyist_name}
                </p>
                <p className="mb-3 text-sm text-slate-600">{f.registrant_name}</p>
                <p className="line-clamp-3 text-sm leading-relaxed text-slate-700">
                  {f.covered_position}
                </p>
                <p className="mt-3 text-sm font-semibold text-indigo-600">
                  Open full case →
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Two columns: reporter vs judge ─────────────────────────────────── */}
      <section className="mb-14 grid gap-6 md:grid-cols-2">
        <Path
          icon="🗞"
          title="If you're a reporter"
          body={
            <>
              <p className="mb-3">
                Three-minute path to a story lead:
              </p>
              <ol className="ml-5 list-decimal space-y-2">
                <li>
                  Open <Link href="/findings" className="font-semibold text-indigo-700 underline decoration-dotted">Findings</Link>{" "}
                  and skim Tier A candidates (high concentration + money trail attached).
                </li>
                <li>
                  Pick one, click <em>Open full case</em>, read the four gates on one page.
                </li>
                <li>
                  Use <Link href="/pressrel" className="font-semibold text-indigo-700 underline decoration-dotted">Press releases</Link>{" "}
                  to find legislators already on the record about the client.
                </li>
                <li>
                  Send the drafted comment request via{" "}
                  <Link href="/comments" className="font-semibold text-indigo-700 underline decoration-dotted">Comments</Link>{" "}
                  and log the response.
                </li>
              </ol>
              <p className="mt-4 text-sm text-slate-600">
                Every finding has a download button (CSV / Markdown / JSON) and a stable
                permalink. Citation lines pre-attribute to{" "}
                <code className="rounded bg-slate-100 px-1 font-mono text-xs">lda.senate.gov</code>{" "}
                with a filing UUID.
              </p>
            </>
          }
        />
        <Path
          icon="⚖"
          title="If you're a judge"
          body={
            <>
              <p className="mb-3">
                Reproducibility-first walkthrough:
              </p>
              <ol className="ml-5 list-decimal space-y-2">
                <li>
                  Read <Link href="/methods" className="font-semibold text-indigo-700 underline decoration-dotted">Methods</Link>{" "}
                  — pipeline diagram, what each skill does, what it can / can&apos;t claim.
                </li>
                <li>
                  Open the #1 candidate:{" "}
                  {topThree[0] ? (
                    <Link
                      href={`/findings/${findingSlug(topThree[0])}`}
                      className="font-semibold text-indigo-700 underline decoration-dotted"
                    >
                      {topThree[0].lobbyist_name} / {topThree[0].agency_short.toUpperCase()}
                    </Link>
                  ) : (
                    <span>(no findings loaded)</span>
                  )}{" "}
                  — see all four gates on one screen.
                </li>
                <li>
                  Open <Link href="/graph" className="font-semibold text-indigo-700 underline decoration-dotted">Graph</Link>{" "}
                  for the composed conflict-of-interest visual across the top-10 cases.
                </li>
                <li>
                  See <code className="rounded bg-slate-100 px-1 font-mono text-xs">README.md</code>{" "}
                  for the clean-clone reproduction command. CI is green on Linux, macOS, Windows.
                </li>
              </ol>
            </>
          }
        />
      </section>

      {/* What this is NOT ───────────────────────────────────────────────── */}
      <aside className="mb-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">
          What FairGuard is — and what it is not
        </p>
        <p className="mb-3 text-base leading-relaxed text-amber-900">
          FairGuard surfaces <strong>conflict-of-interest structure</strong>: who
          worked where, who lobbies whom, and what federal money those clients
          received. It does not — and cannot — prove wrongdoing. Lobbying is legal,
          and so is most federal contracting.
        </p>
        <p className="text-base leading-relaxed text-amber-900">
          Before publication, you still need to (a) confirm the prior role via an
          authoritative source (agency directory, news archive), (b) check{" "}
          <Link href="/glossary#section-207" className="font-semibold underline decoration-dotted">§207 cooling-off</Link>{" "}
          status, (c) distinguish discretionary grants from routine program
          participation, and (d) seek comment from the lobbyist and their firm.
          The tools here help with all four. See{" "}
          <Link href="/methods" className="font-semibold underline decoration-dotted">Methods</Link>{" "}
          for the full caveat list.
        </p>
      </aside>

      {/* Last refreshed footer ──────────────────────────────────────────── */}
      <section className="mb-4 text-center text-sm text-slate-500">
        Data on this page generated{" "}
        <strong className="font-semibold text-slate-700">
          {new Date(findingsPayload.generated_at).toLocaleString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit", timeZoneName: "short",
          })}
        </strong>
        . Refresh button on each subpage re-reads from disk without a page reload.
      </section>
    </div>
  )
}

// ── Building blocks ──────────────────────────────────────────────────────

function HeadlineStat({
  label, value, sub,
}: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold tracking-tight tabular-nums text-slate-900">
        {value}
      </div>
      <div className="mt-1 text-sm text-slate-600">{sub}</div>
    </div>
  )
}

const TONE: Record<string, { bar: string; chip: string; cta: string }> = {
  indigo:  { bar: "bg-indigo-500",  chip: "bg-indigo-50 text-indigo-700 ring-indigo-200",   cta: "text-indigo-700"  },
  emerald: { bar: "bg-emerald-500", chip: "bg-emerald-50 text-emerald-800 ring-emerald-200", cta: "text-emerald-700" },
  amber:   { bar: "bg-amber-500",   chip: "bg-amber-50 text-amber-800 ring-amber-200",       cta: "text-amber-700"   },
  rose:    { bar: "bg-rose-500",    chip: "bg-rose-50 text-rose-800 ring-rose-200",          cta: "text-rose-700"    },
  slate:   { bar: "bg-slate-400",   chip: "bg-slate-100 text-slate-700 ring-slate-200",      cta: "text-slate-700"   },
}

function Tile({
  tone, badge, title, body, href, cta,
}: {
  tone: keyof typeof TONE
  badge: string
  title: string
  body: string
  href: string
  cta: string
}) {
  const c = TONE[tone] ?? TONE.slate
  return (
    <Link
      href={href}
      className="group flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md"
    >
      <div className={`h-1.5 ${c.bar}`} />
      <div className="flex flex-1 flex-col p-6">
        <span className={`mb-3 inline-flex w-fit rounded-full px-3 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ${c.chip}`}>
          {badge}
        </span>
        <h3 className="mb-2 text-xl font-bold text-slate-900 group-hover:text-indigo-700">
          {title}
        </h3>
        <p className="mb-4 flex-1 text-base leading-relaxed text-slate-700">{body}</p>
        <p className={`text-base font-semibold ${c.cta}`}>{cta}</p>
      </div>
    </Link>
  )
}

function Path({
  icon, title, body,
}: { icon: string; title: string; body: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-3 flex items-center gap-3">
        <span className="text-3xl" aria-hidden>{icon}</span>
        <h3 className="text-xl font-bold text-slate-900">{title}</h3>
      </div>
      <div className="text-base leading-relaxed text-slate-700">{body}</div>
    </div>
  )
}
