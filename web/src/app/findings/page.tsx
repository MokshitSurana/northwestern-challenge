/**
 * FairGuard Reporter Verification UI — Findings list
 *
 * Data source: web/public/findings.json (written by scripts/03_agency_concentration.py)
 * Trails embedded by scripts/04_award_tracer.py when a case's `match` block resolves.
 */

import Link from "next/link"
import rawData from "../../../public/findings.json"
import FindingsClient from "../FindingsClient"
import type { Finding, FindingsPayload } from "../types"

export const metadata = {
  title: "Findings — FairGuard",
  description:
    "Ranked structural findings: former officials lobbying their old agency. " +
    "Filter by agency, refresh from disk, open any candidate's permalink.",
}

export default function Page() {
  const data = rawData as FindingsPayload
  const findings: Finding[] = data.findings ?? []
  const agencies = [...new Set(findings.map((f) => f.agency_short))]

  const generatedAt = data.generated_at
    ? new Date(data.generated_at).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZoneName: "short",
    })
    : null

  return (
    <div>
      {/* Hero */}
      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-rose-100 px-3 py-1 text-sm font-semibold text-rose-800 ring-1 ring-rose-200">
            Track 2 — Structural finding
          </span>
          {generatedAt && (
            <span className="text-sm text-slate-500">
              Data generated {generatedAt}
            </span>
          )}
        </div>
        <h1 className="mb-4">
          Former Agency Officials Lobbying Their Old Agency
        </h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          <strong className="font-semibold text-slate-900">{data.total_candidates}</strong>{" "}
          candidates identified across{" "}
          <strong className="font-semibold text-slate-900">
            {new Set(findings.map((f) => f.agency_short)).size}
          </strong>{" "}
          federal agencies, ranked by agency concentration x volume x seniority. All figures from Senate LDA 2022-2026. Prior roles are verbatim self-disclosures —
          verify independently before publishing.
        </p>

        {/* How-to strip */}
        <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-base text-slate-700 print:hidden">
          <span className="font-semibold text-slate-900">First time here?</span>
          <Link
            href="/methods"
            className="font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            Read the methods page →
          </Link>
          <span className="text-slate-400">·</span>
          <span className="font-semibold text-slate-900">To refresh data:</span>
          <code className="rounded-md bg-indigo-50 px-2 py-1 font-mono text-sm text-indigo-700 ring-1 ring-indigo-100">
            /fair-guard scan
          </code>
          <span className="text-slate-400">or</span>
          <code className="rounded-md bg-emerald-50 px-2 py-1 font-mono text-sm text-emerald-700 ring-1 ring-emerald-100">
            /fair-guard trace
          </code>
          <span>then click ↻ Refresh below.</span>
        </div>
      </section>

      {findings.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-16 text-center">
          <p className="mb-3 text-xl font-semibold text-slate-600">No findings loaded</p>
          <p className="text-base text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-sm">
              uv run scripts/03_agency_concentration.py
            </code>{" "}
            to generate <code className="font-mono text-sm">web/public/findings.json</code>.
          </p>
        </div>
      ) : (
        <FindingsClient findings={findings} agencies={agencies} />
      )}

      {/* Editorial note */}
      <aside className="mt-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">Editorial note</p>
        <p className="text-base leading-relaxed text-amber-900">
          This interface is for reporter verification, not publication. Concentration
          ratios are computed from <strong>Senate LDA only</strong> (House not yet
          included — would shift rankings). The{" "}
          <code className="font-mono text-sm">covered_position</code> field is a
          voluntary self-disclosure: lobbyists fill it in themselves. Always confirm
          prior roles against authoritative sources (agency staff directories, news
          archives) before making any public claim. See{" "}
          <Link href="/methods" className="font-semibold underline decoration-dotted">methods</Link>{" "}
          for verification methodology and what this tool can / can&apos;t claim.
        </p>
      </aside>
    </div>
  )
}
