/**
 * /findings/[id] — single-screen "four gates" view for a candidate.
 *
 * The gates a reporter has to clear before publication:
 *   1. Prior agency role (LDA self-disclosure → confirm independently)
 *   2. Money trail        (USAspending awards from agency to clients)
 *   3. §207 cooling-off   (was the timing legal?)
 *   4. Request for comment (have we asked the firm to respond?)
 *
 * This page lays out all four side-by-side so an editor can scan in 30 seconds.
 */

import Link from "next/link"
import { notFound } from "next/navigation"
import findingsData from "../../../../public/findings.json"
import pressrelData from "../../../../public/press_releases.json"
import commentData from "../../../../public/comment_log.json"
import { findingSlug, findingToMarkdown, findingCitation } from "../../lib/exports"
import { CopyButton, DownloadButton } from "./DetailButtons"
import type {
  CommentEntry,
  CommentLogPayload,
  Finding,
  FindingsPayload,
  PressrelMatch,
  PressrelPayload,
  PressrelReport,
  Trail,
  TrailClient,
} from "../../types"

const fmtUSD = (n: number) =>
  n >= 1_000_000_000
    ? `$${(n / 1_000_000_000).toFixed(2)}B`
    : n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(1)}M`
      : `$${n.toLocaleString()}`

const fmtDate = (s: string) =>
  new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })

// ── Static params: pre-render every finding's permalink at build time ────

export function generateStaticParams() {
  const data = findingsData as FindingsPayload
  return (data.findings ?? []).map((f) => ({ id: findingSlug(f) }))
}

export function generateMetadata({ params }: { params: { id: string } }) {
  const finding = lookup(params.id)
  if (!finding) return { title: "Finding not found — FairGuard" }
  return {
    title: `${finding.lobbyist_name} → ${finding.agency_short.toUpperCase()} — FairGuard`,
    description: `Full case file: ${finding.lobbyist_name} (${finding.registrant_name}) directing ${Math.round(finding.concentration * 100)}% of lobbying filings at the ${finding.agency_short.toUpperCase()}.`,
  }
}

function lookup(id: string): Finding | null {
  const data = findingsData as FindingsPayload
  return (data.findings ?? []).find((f) => findingSlug(f) === id) ?? null
}

function findPressrelMatches(finding: Finding): PressrelMatch[] {
  const data = pressrelData as PressrelPayload
  const lobbyistKey = finding.lobbyist_name.toUpperCase()
  const agencyKey = finding.agency_short.toLowerCase()
  // Reports linked via `match` block, plus any clients overlapping top_clients_str.
  const tops = finding.top_clients_str
    ? finding.top_clients_str.split("|").map((s) => s.trim().toUpperCase()).filter(Boolean)
    : []
  const matches: PressrelMatch[] = []
  const seen = new Set<string>()
  for (const r of data.reports ?? []) {
    const matched = (r.match ?? []).some(
      (m) =>
        m.lobbyist_name.toUpperCase() === lobbyistKey &&
        m.agency_short.toLowerCase() === agencyKey
    )
    const clientOverlap = !matched && (r.per_client ?? []).some((pc) =>
      tops.some((tc) => tc.includes(pc.client.toUpperCase()) || pc.client.toUpperCase().includes(tc))
    )
    if (!matched && !clientOverlap) continue
    for (const m of r.matches) {
      const key = `${m.url}::${m.client ?? ""}`
      if (seen.has(key)) continue
      seen.add(key)
      matches.push(m)
    }
  }
  return matches
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .slice(0, 25)
}

function findPressrelReports(finding: Finding): PressrelReport[] {
  const data = pressrelData as PressrelPayload
  const lobbyistKey = finding.lobbyist_name.toUpperCase()
  const agencyKey = finding.agency_short.toLowerCase()
  return (data.reports ?? []).filter((r) =>
    (r.match ?? []).some(
      (m) =>
        m.lobbyist_name.toUpperCase() === lobbyistKey &&
        m.agency_short.toLowerCase() === agencyKey
    )
  )
}

function findCommentEntry(finding: Finding): CommentEntry | null {
  const data = commentData as CommentLogPayload
  const firmKey = finding.registrant_name.toUpperCase().trim()
  // Strict firm match first, then by scan_rank.
  let entry =
    (data.entries ?? []).find((e) => e.firm.toUpperCase().trim() === firmKey) ?? null
  if (!entry) {
    entry =
      (data.entries ?? []).find((e) => {
        const ranks = Array.isArray(e.scan_rank) ? e.scan_rank : e.scan_rank ? [e.scan_rank] : []
        return ranks.includes(finding.rank)
      }) ?? null
  }
  return entry
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const finding = lookup(params.id)
  if (!finding) notFound()

  const pct = Math.round(finding.concentration * 100)
  const trail = finding.trail
  const pressMatches = findPressrelMatches(finding)
  const pressReports = findPressrelReports(finding)
  const comment = findCommentEntry(finding)

  // Gate states — used for the badges at the top.
  const gates = [
    {
      n: 1,
      key: "role",
      label: "Prior agency role",
      status: "self_disclosed" as const,
      summary: finding.covered_position || "(no covered_position on file)",
    },
    {
      n: 2,
      key: "money",
      label: "Money trail",
      status: (trail ? "present" : "missing") as "present" | "missing",
      summary: trail
        ? `${fmtUSD(trail.total)} traced (${fmtUSD(trail.discretionary_total)} discretionary)`
        : "No USAspending trace run yet — see suggestion below",
    },
    {
      n: 3,
      key: "section207",
      label: "§207 cooling-off",
      status: "manual_review" as const,
      summary: "Confirm last federal day; LDA does not record the exact departure date",
    },
    {
      n: 4,
      key: "comment",
      label: "Request for comment",
      status: comment?.status ?? ("not_drafted" as const),
      summary: comment?.status_label ?? "⚪ Not drafted",
    },
  ]

  const slug = findingSlug(finding)

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="mb-5 text-sm text-slate-500 print:hidden">
        <Link href="/" className="hover:text-indigo-700">Home</Link>
        <span className="mx-2">/</span>
        <Link href="/findings" className="hover:text-indigo-700">Findings</Link>
        <span className="mx-2">/</span>
        <span className="font-semibold text-slate-700">{finding.lobbyist_name}</span>
      </nav>

      {/* Header ────────────────────────────────────────────────────────── */}
      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-rose-100 px-3 py-1 text-sm font-semibold text-rose-800 ring-1 ring-rose-200">
            Track 2 — Structural candidate
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold uppercase tracking-wide text-slate-700 ring-1 ring-slate-200">
            {finding.agency_short}
          </span>
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-bold text-indigo-800 ring-1 ring-indigo-200">
            Rank #{finding.rank}
          </span>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800 ring-1 ring-amber-200">
            Not for publication — verification view
          </span>
        </div>
        <h1 className="mb-2">{finding.lobbyist_name}</h1>
        <p className="mb-4 text-xl text-slate-600">
          {finding.registrant_name}{" "}
          <span className="text-slate-400">·</span>{" "}
          targets the <strong className="text-slate-800">{finding.agency_short.toUpperCase()}</strong> in{" "}
          <strong className="text-slate-800">{pct}%</strong> of filings
        </p>
        <div className="flex flex-wrap items-center gap-3 text-base text-slate-600 print:hidden">
          <CopyButton text={findingCitation(finding)} label="Copy citation" />
          <CopyButton text={`${slug}`} label="Copy slug" />
          <DownloadButton
            content={findingToMarkdown(finding)}
            filename={`fairguard-${slug}.md`}
            mime="text/markdown"
            label="Download Markdown"
          />
          <DownloadButton
            content={JSON.stringify(finding, null, 2)}
            filename={`fairguard-${slug}.json`}
            mime="application/json"
            label="Download JSON"
          />
        </div>
      </header>

      {/* Four-gate dashboard ────────────────────────────────────────────── */}
      <section className="mb-10">
        <h2 className="mb-4">The four gates</h2>
        <p className="mb-5 max-w-3xl text-base text-slate-700">
          Before publishing a causal claim about this candidate, you need to clear each
          of the four gates below. FairGuard surfaces what it can; the rest is human
          editorial judgment. <Link href="/methods#gates" className="font-semibold text-indigo-700 underline decoration-dotted">Read the full criteria →</Link>
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {gates.map(({ key, ...rest }) => (
            <GateCard key={key} {...rest} />
          ))}
        </div>
      </section>

      {/* Gate 1: Prior role ─────────────────────────────────────────────── */}
      <SectionAnchor id="gate-1" tone="indigo">
        <SectionHeader
          number={1}
          title="Prior agency role"
          subtitle="As self-disclosed in the LDA filing. The Senate does not verify these — you must."
        />
        <blockquote className="mb-4 rounded-lg border-l-4 border-indigo-400 bg-slate-50 px-5 py-4 text-lg leading-relaxed text-slate-800">
          {finding.covered_position || "(no covered_position on file)"}
        </blockquote>
        <div className="rounded-lg border border-slate-200 bg-white p-5 text-base text-slate-700">
          <p className="mb-2 font-semibold text-slate-900">How to verify:</p>
          <ul className="ml-5 list-disc space-y-1">
            <li>Search the agency&apos;s staff directory or historical{" "}
              <code className="rounded bg-slate-100 px-1 font-mono text-sm">/leadership</code>{" "}
              page (Internet Archive helps if the role has ended).</li>
            <li>Look for confirmation hearings, press releases, or LinkedIn (treat LinkedIn
              as a lead, not a citation).</li>
            <li>Check news archives — major personnel moves are usually covered by trade
              press at the time.</li>
          </ul>
        </div>
      </SectionAnchor>

      {/* Gate 2: Money trail ─────────────────────────────────────────────── */}
      <SectionAnchor id="gate-2" tone="emerald">
        <SectionHeader
          number={2}
          title="Money trail"
          subtitle="Federal awards from this agency to this lobbyist's clients, verified by recipient name on USAspending.gov."
        />
        {trail ? <TrailFull trail={trail} /> : (
          <EmptyState
            heading="No trace run for this finding yet"
            body={
              <>
                <p className="mb-2">
                  Run the trace skill to generate a money trail for this candidate:
                </p>
                <pre className="overflow-x-auto rounded-lg bg-slate-900 px-4 py-3 font-mono text-sm text-emerald-200">
                  /fair-guard trace --case &lt;case-file.json&gt;
                </pre>
                <p className="mt-3">
                  See <Link href="/methods#trace" className="font-semibold text-indigo-700 underline decoration-dotted">methods/trace</Link> for the case-file schema, or open{" "}
                  <Link href="/trails" className="font-semibold text-indigo-700 underline decoration-dotted">existing trails</Link>{" "}
                  for examples.
                </p>
              </>
            }
          />
        )}
      </SectionAnchor>

      {/* Gate 3: §207 cooling-off ───────────────────────────────────────── */}
      <SectionAnchor id="gate-3" tone="amber">
        <SectionHeader
          number={3}
          title="§207 cooling-off period"
          subtitle="Was the timing legal? 18 U.S.C. §207 bans certain forms of post-employment lobbying for one to two years."
        />
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-base text-slate-800">
          <p className="mb-2 font-semibold text-amber-900">FairGuard can&apos;t close this gate automatically.</p>
          <p className="mb-3 leading-relaxed">
            The LDA <strong>does not record</strong> the exact day a lobbyist&apos;s
            federal employment ended, only the title. The window between leaving
            government and filing the first lobbying contact is therefore a manual
            check — usually via the agency&apos;s OIG report, a press release, or
            news coverage of the personnel move.
          </p>
          <p className="font-semibold text-amber-900">What to look for:</p>
          <ul className="ml-5 list-disc space-y-1">
            <li>
              <strong>Senior officials</strong> (covered under §207(c)/(d)) — 1-year
              cooling-off bar on contacts with their former agency, regardless of issue.
            </li>
            <li>
              <strong>Trade-rep / treasury negotiators</strong> — additional restrictions
              under §207(b), (f).
            </li>
            <li>
              First filing date for this lobbyist on this agency:{" "}
              <strong className="tabular-nums text-slate-900">{finding.first_year}</strong>
              {" "}— if the departure was within a year of that, dig deeper.
            </li>
          </ul>
          <p className="mt-3 text-sm text-amber-900">
            See <Link href="/glossary#section-207" className="font-semibold underline decoration-dotted">glossary: §207</Link>{" "}
            and <code className="rounded bg-white px-1 font-mono text-xs">notes/09_reportability_gates_207_and_comment.md</code>{" "}
            for the per-case timing analysis already done on the top candidates.
          </p>
        </div>
      </SectionAnchor>

      {/* Gate 4: Comment ─────────────────────────────────────────────────── */}
      <SectionAnchor id="gate-4" tone="rose">
        <SectionHeader
          number={4}
          title="Request for comment"
          subtitle="A drafted request and a documented response — or a documented refusal — closes this gate."
        />
        {comment ? <CommentSummary entry={comment} /> : (
          <EmptyState
            heading="No comment request drafted for this firm yet"
            body={
              <>
                <p className="mb-3">
                  Use the comment-tracker skill to draft, send, and log responses:
                </p>
                <pre className="overflow-x-auto rounded-lg bg-slate-900 px-4 py-3 font-mono text-sm text-rose-200">
                  /fair-guard comment
                </pre>
                <p className="mt-3 text-sm text-slate-600">
                  Drafts are written to{" "}
                  <code className="rounded bg-slate-100 px-1 font-mono text-xs">notes/comment_requests/&lt;firm&gt;.md</code>{" "}
                  and mirrored to <Link href="/comments" className="font-semibold text-indigo-700 underline decoration-dotted">/comments</Link>.
                </p>
              </>
            }
          />
        )}
      </SectionAnchor>

      {/* Press releases attached ────────────────────────────────────────── */}
      <section className="mb-12">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2>Legislators already on the record</h2>
          {pressMatches.length > 0 && (
            <Link
              href="/pressrel"
              className="text-base font-semibold text-indigo-700 underline decoration-dotted hover:text-indigo-900"
            >
              See full press-release report →
            </Link>
          )}
        </div>
        {pressMatches.length === 0 ? (
          <EmptyState
            heading="No congressional press releases matched yet"
            body={
              <p>
                Run{" "}
                <code className="rounded bg-slate-100 px-1 font-mono text-sm">/fair-guard pressrel</code>{" "}
                with a case file linked to this lobbyist&apos;s clients to surface mentions.
              </p>
            }
          />
        ) : (
          <>
            <p className="mb-4 text-base text-slate-700">
              <strong>{pressMatches.length}</strong> congressional press release
              {pressMatches.length === 1 ? "" : "s"} mentioning this lobbyist&apos;s clients
              {pressReports.length > 0 &&
                ` (across ${new Set(pressMatches.map((m) => m.member_name)).size} distinct legislators).`}
            </p>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-base">
                <thead className="bg-slate-50">
                  <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
                    <th className="px-4 py-2 font-semibold">Date</th>
                    <th className="px-4 py-2 font-semibold">Legislator</th>
                    <th className="px-4 py-2 font-semibold">Client mentioned</th>
                    <th className="px-4 py-2 font-semibold">Title</th>
                  </tr>
                </thead>
                <tbody>
                  {pressMatches.map((m) => (
                    <tr key={m.url} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2 tabular-nums text-slate-600">{fmtDate(m.date)}</td>
                      <td className="px-4 py-2">
                        <span className="font-semibold text-slate-900">{m.member_name}</span>
                        {m.party && m.state && (
                          <span className="ml-1 text-sm text-slate-500">
                            ({m.party}-{m.state})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 font-mono text-sm text-slate-700">{m.client ?? "—"}</td>
                      <td className="px-4 py-2">
                        <a
                          href={m.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-700 underline decoration-dotted hover:text-indigo-900"
                        >
                          {m.title}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {/* Full filing context ───────────────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="mb-4">Filing context</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatBox label="Agency-targeting filings" value={finding.agency_filings} />
          <StatBox label="Total filings" value={finding.total_filings} />
          <StatBox label="Clients" value={finding.n_clients} />
          <StatBox label="Disclosed income" value={fmtUSD(finding.total_income)} />
          <StatBox label="Active years" value={`${finding.first_year}–${finding.last_year}`} />
          <StatBox label="FairGuard score" value={finding.score.toFixed(2)} />
          <StatBox label="Concentration" value={`${pct}%`} />
          <StatBox label="Source dataset" value="Senate LDA" />
        </div>
        {finding.top_clients_str && (
          <>
            <h3 className="mt-6 mb-2">Top agency-targeting clients</h3>
            <p className="text-base leading-relaxed text-slate-700">
              {finding.top_clients_str.split("|").map((s, i, arr) => (
                <span key={i}>
                  <span className="font-mono">{s.trim()}</span>
                  {i < arr.length - 1 && <span className="mx-2 text-slate-400">·</span>}
                </span>
              ))}
            </p>
          </>
        )}
      </section>

      {/* Provenance ─────────────────────────────────────────────────────── */}
      <section className="mb-10 rounded-xl border border-slate-200 bg-slate-900 p-6 text-slate-300">
        <h3 className="mb-3 text-base font-bold uppercase tracking-wider text-slate-400">
          Provenance
        </h3>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Provenance label="Sample filing UUID">
            {finding.sample_uuid ? (
              <a
                href={finding.senate_lda_url ?? `https://lda.senate.gov/filings/public/filing/${finding.sample_uuid}/print/`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-indigo-300 underline decoration-dotted hover:text-indigo-200"
              >
                {finding.sample_uuid}
              </a>
            ) : "—"}
          </Provenance>
          <Provenance label="Source file">
            <code className="break-all font-mono text-slate-400">{finding.sample_source}</code>
          </Provenance>
          <Provenance label="Source dataset">U.S. Senate Lobbying Disclosure Act filings, 2022–2026</Provenance>
          <Provenance label="Permalink">
            <code className="font-mono text-slate-400">/findings/{slug}</code>
          </Provenance>
        </dl>
      </section>

      <aside className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="text-base leading-relaxed text-amber-900">
          <strong>Reminder.</strong> Structural concentration plus a money trail is a{" "}
          <em>conflict-of-interest pattern</em>, not proof of any wrongdoing. Lobbying is
          legal. Most federal contracting is routine. Before publication, clear all four
          gates above and run the AP-style lint over your draft (see{" "}
          <Link href="/methods" className="font-semibold underline decoration-dotted">methods</Link>).
        </p>
      </aside>
    </div>
  )
}

// ── Components ───────────────────────────────────────────────────────────

function GateCard({
  n, label, status, summary,
}: {
  n: number
  label: string
  status: string
  summary: string
}) {
  const map: Record<string, { tone: string; chip: string; icon: string }> = {
    self_disclosed: { tone: "border-indigo-200 bg-indigo-50",  chip: "bg-indigo-200 text-indigo-900",  icon: "i" },
    present:        { tone: "border-emerald-200 bg-emerald-50", chip: "bg-emerald-200 text-emerald-900", icon: "✓" },
    missing:        { tone: "border-slate-200 bg-slate-50",     chip: "bg-slate-200 text-slate-700",     icon: "○" },
    manual_review:  { tone: "border-amber-200 bg-amber-50",     chip: "bg-amber-200 text-amber-900",     icon: "?" },
    not_drafted:    { tone: "border-slate-200 bg-slate-50",     chip: "bg-slate-200 text-slate-700",     icon: "○" },
    not_sent:       { tone: "border-slate-200 bg-slate-50",     chip: "bg-slate-200 text-slate-700",     icon: "□" },
    sent:           { tone: "border-indigo-200 bg-indigo-50",   chip: "bg-indigo-200 text-indigo-900",   icon: "→" },
    acknowledged:   { tone: "border-indigo-200 bg-indigo-50",   chip: "bg-indigo-200 text-indigo-900",   icon: "✓" },
    awaiting_substantive: { tone: "border-amber-200 bg-amber-50", chip: "bg-amber-200 text-amber-900",  icon: "⋯" },
    responded:      { tone: "border-emerald-200 bg-emerald-50", chip: "bg-emerald-200 text-emerald-900", icon: "✓" },
    no_response_by_deadline: { tone: "border-rose-200 bg-rose-50", chip: "bg-rose-200 text-rose-900",   icon: "!" },
    closed_response: { tone: "border-emerald-200 bg-emerald-50", chip: "bg-emerald-200 text-emerald-900", icon: "✓" },
    closed_no_response: { tone: "border-slate-200 bg-slate-50",  chip: "bg-slate-200 text-slate-700",     icon: "×" },
    escalated_to_counsel: { tone: "border-rose-200 bg-rose-50", chip: "bg-rose-200 text-rose-900",       icon: "!" },
  }
  const s = map[status] ?? map.missing
  return (
    <Link
      href={`#gate-${n}`}
      className={`rounded-xl border p-5 transition hover:shadow-md ${s.tone}`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-base font-bold ${s.chip}`}>
          {s.icon}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Gate {n}
        </span>
      </div>
      <p className="text-base font-bold text-slate-900">{label}</p>
      <p className="mt-1 text-sm leading-snug text-slate-700">{summary}</p>
    </Link>
  )
}

function SectionAnchor({
  id, tone, children,
}: { id: string; tone: "indigo" | "emerald" | "amber" | "rose"; children: React.ReactNode }) {
  const map = {
    indigo: "border-l-indigo-500",
    emerald: "border-l-emerald-500",
    amber: "border-l-amber-500",
    rose: "border-l-rose-500",
  }
  return (
    <section id={id} className={`mb-10 scroll-mt-32 border-l-4 pl-6 ${map[tone]}`}>
      {children}
    </section>
  )
}

function SectionHeader({
  number, title, subtitle,
}: { number: number; title: string; subtitle: string }) {
  return (
    <div className="mb-4">
      <p className="mb-1 text-sm font-semibold uppercase tracking-wider text-slate-500">
        Gate {number}
      </p>
      <h2 className="mb-2">{title}</h2>
      <p className="max-w-3xl text-base text-slate-600">{subtitle}</p>
    </div>
  )
}

function TrailFull({ trail }: { trail: Trail }) {
  const pctDisc =
    trail.total > 0 ? Math.round((trail.discretionary_total / trail.total) * 100) : 0
  return (
    <div className="overflow-hidden rounded-xl border border-emerald-200 bg-white">
      <div className="border-b border-emerald-200 bg-emerald-50 px-5 py-4">
        <p className="text-lg font-bold text-emerald-900">
          {fmtUSD(trail.total)} traced · {fmtUSD(trail.discretionary_total)} discretionary ({pctDisc}%)
        </p>
        <p className="mt-1 text-base text-emerald-800">
          Federal <strong>{trail.award_groups.join(", ")}</strong> awarded by{" "}
          <strong>{trail.agency}</strong> to {trail.lobbyist_label}&apos;s clients
          {" "}({trail.n_clients_with_awards} of {trail.n_clients_total} clients with awards).
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead className="bg-slate-50">
            <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
              <th className="px-4 py-2 font-semibold">Client</th>
              <th className="px-4 py-2 text-right font-semibold">Total</th>
              <th className="px-4 py-2 text-right font-semibold">Awards</th>
              <th className="px-4 py-2 text-right font-semibold">Discretionary</th>
              <th className="px-4 py-2 text-right font-semibold">Routine</th>
            </tr>
          </thead>
          <tbody>
            {trail.clients.map((c: TrailClient) => (
              <tr key={c.label} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-900">
                  <span className="font-semibold">{c.label}</span>
                  {c.recipients.length > 0 && (
                    <span className="ml-2 text-sm text-slate-500">
                      ({c.recipients.slice(0, 2).join("; ")}
                      {c.recipients.length > 2 && ` …+${c.recipients.length - 2}`})
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums font-semibold text-slate-900">
                  {fmtUSD(c.total)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-600">{c.n_awards}</td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-emerald-700">
                  {fmtUSD(c.discretionary_amount)}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-600">
                  {fmtUSD(c.routine_amount)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t-2 border-slate-300 bg-slate-50">
            <tr>
              <td className="px-4 py-2 font-bold text-slate-900">Total</td>
              <td className="px-4 py-2 text-right font-mono font-bold tabular-nums text-slate-900">
                {fmtUSD(trail.total)}
              </td>
              <td />
              <td className="px-4 py-2 text-right font-mono font-bold tabular-nums text-emerald-800">
                {fmtUSD(trail.discretionary_total)}
              </td>
              <td className="px-4 py-2 text-right font-mono font-bold tabular-nums text-slate-700">
                {fmtUSD(trail.routine_total)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      {trail.misses.length > 0 && (
        <p className="border-t border-slate-200 bg-slate-50 px-5 py-3 text-sm italic text-slate-500">
          No verified {trail.agency} {trail.award_groups.join(", ")} found for:{" "}
          {trail.misses.join(", ")}.
        </p>
      )}
      <p className="border-t border-amber-200 bg-amber-50 px-5 py-3 text-base text-amber-900">
        <strong>Framing:</strong> conflict-of-interest <em>structure</em>, not proven
        wrongdoing. Discretionary, competitively-awarded grants are the newsworthy core;
        routine program participation is context. See{" "}
        <Link href="/glossary#discretionary" className="font-semibold underline decoration-dotted">glossary: discretionary vs routine</Link>.
      </p>
    </div>
  )
}

function CommentSummary({ entry }: { entry: CommentEntry }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-slate-200 px-3 py-1 text-sm font-bold text-slate-800">
            {entry.status_label}
          </span>
          <span className="text-lg font-bold text-slate-900">{entry.firm}</span>
          {entry.deadline && (
            <span className="text-sm text-slate-600">
              Deadline: <strong className="text-slate-900">{fmtDate(entry.deadline)}</strong>
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-600">{entry.case}</p>
      </div>
      <div className="px-5 py-4">
        <p className="mb-2 text-base text-slate-700">
          Drafted at{" "}
          <code className="rounded bg-slate-100 px-1 font-mono text-sm">{entry.draft_path}</code>.
        </p>
        {entry.events.length === 0 ? (
          <p className="text-base italic text-slate-500">No events logged yet.</p>
        ) : (
          <ol className="space-y-2">
            {entry.events.map((ev, i) => (
              <li key={i} className="flex gap-3 text-base">
                <span className="w-32 shrink-0 font-mono tabular-nums text-sm text-slate-500">
                  {fmtDate(ev.at)}
                </span>
                <span className="font-semibold text-slate-900">{ev.kind.replace(/_/g, " ")}</span>
                {ev.summary && <span className="text-slate-700">— {ev.summary}</span>}
              </li>
            ))}
          </ol>
        )}
        <p className="mt-3">
          <Link href="/comments" className="font-semibold text-indigo-700 underline decoration-dotted">
            Open the full comment dashboard →
          </Link>
        </p>
      </div>
    </div>
  )
}

function EmptyState({
  heading, body,
}: { heading: string; body: React.ReactNode }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-6">
      <p className="mb-2 text-lg font-semibold text-slate-700">{heading}</p>
      <div className="text-base text-slate-700">{body}</div>
    </div>
  )
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-bold text-slate-900">{value}</div>
    </div>
  )
}

function Provenance({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  )
}

