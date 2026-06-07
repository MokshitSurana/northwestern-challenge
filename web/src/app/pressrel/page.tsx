import rawData from "../../../public/press_releases.json"
import PressrelClient from "./PressrelClient"
import type { PressrelPayload } from "../types"

export default function PressrelPage() {
  const data = rawData as PressrelPayload
  const reports = data.reports ?? []

  return (
    <div>
      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800 ring-1 ring-amber-200">
            Press-release cross-ref
          </span>
          <a
            href="/"
            className="text-sm font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            ← Back to findings
          </a>
        </div>
        <h1 className="mb-4">Congressional press releases</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          Verified mentions of revolving-door clients in 141K House and Senate
          press releases (2022–Q1 2026). Each card is one cross-ref run, showing
          which members of Congress have publicly named the lobbying clients
          surfaced by <strong>scan</strong>.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-base text-slate-700">
          <span className="font-semibold text-slate-900">To add a report:</span>
          <code className="rounded-md bg-amber-50 px-2 py-1 font-mono text-sm text-amber-700 ring-1 ring-amber-100">
            /fair-guard pressrel
          </code>
          <span>with a case file, then click ↻ Refresh below.</span>
        </div>
      </section>

      <PressrelClient initialReports={reports} />

      <aside className="mt-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">Editorial note</p>
        <p className="text-base leading-relaxed text-amber-900">
          A verified mention is <em>not</em> an accusation — it&apos;s an
          alignment signal. Members of Congress name companies for many
          legitimate reasons (praising a constituent employer, listing hearing
          witnesses, citing a Supreme Court case caption). The snippet column
          exists so a reporter can triage on sight. The story is in the{" "}
          <em>intersection</em>: a member who praises a company AND sits on a
          committee whose jurisdiction covers that company AND has a current
          or former staffer registered to lobby for that company. See the{" "}
          <a href="/graph" className="font-semibold text-indigo-700 underline decoration-dotted hover:text-indigo-900">
            conflict-of-interest graph
          </a>{" "}
          for the cross-source view.
        </p>
      </aside>
    </div>
  )
}
