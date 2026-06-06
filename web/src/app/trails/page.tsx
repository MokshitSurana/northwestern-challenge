import rawData from "../../../public/trails.json"
import TrailsClient from "./TrailsClient"
import type { TrailsPayload } from "../types"

export default function TrailsPage() {
  const data = rawData as TrailsPayload
  const trails = data.trails ?? []

  return (
    <div>
      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200">
            Money trails
          </span>
          <a
            href="/"
            className="text-sm font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            ← Back to findings
          </a>
        </div>
        <h1 className="mb-4">USAspending money trails</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          Federal awards traced from a lobbyist&apos;s former agency to their current
          clients, verified by recipient name against USAspending.gov. Each card is one
          trace run; re-running a case overwrites that card in place.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-base text-slate-700">
          <span className="font-semibold text-slate-900">To add a trail:</span>
          <code className="rounded-md bg-emerald-50 px-2 py-1 font-mono text-sm text-emerald-700 ring-1 ring-emerald-100">
            /fair-guard trace
          </code>
          <span>with a case file, then click ↻ Refresh below.</span>
        </div>
      </section>

      <TrailsClient initialTrails={trails} />

      <aside className="mt-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">Editorial note</p>
        <p className="text-base leading-relaxed text-amber-900">
          A money trail is conflict-of-interest <em>structure</em>, not proven
          wrongdoing. Discretionary, competitively-awarded grants from the former
          official&apos;s agency to that official&apos;s clients are the newsworthy
          core; routine program participation (commodity purchases, food aid, formula
          financing) is context. Confirm program type, §207 cooling-off status, and
          seek comment before publishing a causal claim.
        </p>
      </aside>
    </div>
  )
}
