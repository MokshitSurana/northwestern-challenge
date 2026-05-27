"use client"

import { useState } from "react"
import { clsx } from "clsx"

// ── Types (duplicated here so this file is self-contained) ─────────────────────

interface Finding {
  rank: number
  score: number
  agency_short: string
  lobbyist_name: string
  registrant_name: string
  covered_position: string
  concentration: number
  agency_filings: number
  total_filings: number
  n_clients: number
  total_income: number
  first_year: number
  last_year: number
  top_clients_str: string
  sample_uuid: string
  sample_source: string
  senate_lda_url: string | null
  verification_status?: "verified" | "partial" | "unverified" | null
}

// ── Agency color map ───────────────────────────────────────────────────────────

const AGENCY_COLORS: Record<string, string> = {
  nasa:     "bg-blue-100 text-blue-800 ring-blue-300",
  epa:      "bg-green-100 text-green-800 ring-green-300",
  fda:      "bg-purple-100 text-purple-800 ring-purple-300",
  sec:      "bg-orange-100 text-orange-800 ring-orange-300",
  fcc:      "bg-pink-100 text-pink-800 ring-pink-300",
  dod:      "bg-red-100 text-red-800 ring-red-300",
  treasury: "bg-yellow-100 text-yellow-800 ring-yellow-300",
  hhs:      "bg-rose-100 text-rose-800 ring-rose-300",
  dhs:      "bg-slate-100 text-slate-800 ring-slate-300",
  usda:     "bg-lime-100 text-lime-800 ring-lime-300",
  energy:   "bg-amber-100 text-amber-800 ring-amber-300",
  interior: "bg-teal-100 text-teal-800 ring-teal-300",
  dot:      "bg-cyan-100 text-cyan-800 ring-cyan-300",
  faa:      "bg-sky-100 text-sky-800 ring-sky-300",
  state:    "bg-indigo-100 text-indigo-800 ring-indigo-300",
  cftc:     "bg-violet-100 text-violet-800 ring-violet-300",
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AgencyBadge({ code }: { code: string }) {
  return (
    <span
      className={clsx(
        "rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ring-1",
        AGENCY_COLORS[code] ?? "bg-slate-100 text-slate-700 ring-slate-300"
      )}
    >
      {code}
    </span>
  )
}

function VerificationBadge({ status }: { status: Finding["verification_status"] }) {
  if (!status) return null
  const map: Record<string, { label: string; cls: string }> = {
    verified:   { label: "✓ Verified",          cls: "bg-emerald-100 text-emerald-800 ring-emerald-300" },
    partial:    { label: "~ Partially verified", cls: "bg-yellow-100 text-yellow-800 ring-yellow-300" },
    unverified: { label: "⚠ Unverified",         cls: "bg-red-100 text-red-800 ring-red-300" },
  }
  const { label, cls } = map[status] ?? map.unverified
  return (
    <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-medium ring-1", cls)}>
      {label}
    </span>
  )
}

function ConcentrationBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const bar =
    pct >= 70 ? "bg-red-500" :
    pct >= 40 ? "bg-orange-400" :
    pct >= 20 ? "bg-amber-400" :
    "bg-yellow-300"
  return (
    <div className="flex items-center gap-3">
      <div className="h-2.5 w-40 overflow-hidden rounded-full bg-slate-200">
        <div className={clsx("h-full rounded-full transition-all", bar)} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="tabular-nums text-sm font-bold text-slate-800">{pct}%</span>
    </div>
  )
}

function SenateLink({ uuid, url }: { uuid: string; url: string | null }) {
  const href = url ?? `https://lda.senate.gov/filings/public/filing/${uuid}/print/`
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-mono text-xs text-blue-600 underline decoration-dotted hover:text-blue-800"
      title="Open on Senate LDA public site"
    >
      {uuid.slice(0, 8)}…
    </a>
  )
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</div>
      <div className="mt-0.5 text-sm font-semibold text-slate-800">{value}</div>
    </div>
  )
}

function FindingCard({ finding }: { finding: Finding }) {
  const incomeM = (finding.total_income / 1_000_000).toFixed(2)
  const pct = Math.round(finding.concentration * 100)
  const isHighConc = pct >= 50

  return (
    <article className={clsx(
      "rounded-xl border bg-white p-6 shadow-sm transition-shadow hover:shadow-md",
      isHighConc ? "border-orange-200" : "border-slate-200"
    )}>
      {/* Header row */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-500">
            {finding.rank}
          </div>
          <div>
            <h2 className="text-lg font-bold leading-tight text-slate-900">
              {finding.lobbyist_name}
            </h2>
            <p className="mt-0.5 text-sm text-slate-500">{finding.registrant_name}</p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <AgencyBadge code={finding.agency_short} />
          <VerificationBadge status={finding.verification_status} />
        </div>
      </div>

      {/* Concentration meter */}
      <div className="mb-5 rounded-lg border border-slate-100 bg-slate-50 p-4">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-600">Agency concentration ratio</span>
          <span className="tabular-nums text-slate-500">
            {finding.agency_filings} / {finding.total_filings} filings target {finding.agency_short.toUpperCase()}
          </span>
        </div>
        <ConcentrationBar value={finding.concentration} />
      </div>

      {/* Prior role */}
      <div className="mb-5">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Prior role (verbatim LDA disclosure)
          </span>
          <span className="text-xs text-slate-300">— self-reported, verify independently</span>
        </div>
        <p className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 font-mono text-sm leading-relaxed text-slate-700">
          {finding.covered_position}
        </p>
      </div>

      {/* Stats grid */}
      <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatBox label="Clients" value={finding.n_clients} />
        <StatBox label="Disclosed income" value={`$${incomeM}M`} />
        <StatBox label="Active years" value={`${finding.first_year}–${finding.last_year}`} />
        <StatBox label="Score" value={finding.score.toFixed(2)} />
      </div>

      {/* Top clients */}
      {finding.top_clients_str && (
        <div className="mb-5">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Top clients (agency-targeting filings)
          </p>
          <p className="text-sm text-slate-700">{finding.top_clients_str}</p>
        </div>
      )}

      {/* Provenance footer */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 rounded-lg bg-slate-900 px-4 py-3 text-xs">
        <span className="text-slate-400">Source:</span>
        <span className="text-slate-300">
          Senate LDA UUID: <SenateLink uuid={finding.sample_uuid} url={finding.senate_lda_url} />
        </span>
        <span className="max-w-xs truncate font-mono text-slate-500" title={finding.sample_source}>
          {finding.sample_source}
        </span>
      </div>
    </article>
  )
}

// ── Interactive findings list with agency filter ───────────────────────────────

export default function FindingsClient({
  findings,
  agencies,
}: {
  findings: Finding[]
  agencies: string[]
}) {
  const [selected, setSelected] = useState<string | null>(null)

  const visible = selected
    ? findings.filter((f) => f.agency_short === selected)
    : findings

  return (
    <>
      {/* Agency filter */}
      <div className="mb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Filter by agency
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelected(null)}
            className={clsx(
              "rounded-full px-3 py-1 text-xs font-semibold transition",
              selected === null
                ? "bg-slate-800 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            )}
          >
            All ({findings.length})
          </button>
          {agencies.map((a) => {
            const count = findings.filter((f) => f.agency_short === a).length
            return (
              <button
                key={a}
                onClick={() => setSelected(selected === a ? null : a)}
                className={clsx(
                  "rounded-full px-3 py-1 text-xs font-bold uppercase transition ring-1",
                  selected === a
                    ? (AGENCY_COLORS[a] ?? "bg-slate-100 text-slate-700") + " ring-2"
                    : "bg-white text-slate-500 ring-slate-200 hover:bg-slate-50"
                )}
              >
                {a} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {/* Results count */}
      {selected && (
        <p className="mb-4 text-sm text-slate-500">
          Showing {visible.length} finding{visible.length !== 1 ? "s" : ""} for{" "}
          <span className="font-semibold uppercase">{selected}</span>
          {" "}—{" "}
          <button
            onClick={() => setSelected(null)}
            className="text-blue-600 underline decoration-dotted hover:text-blue-800"
          >
            show all
          </button>
        </p>
      )}

      {/* Cards */}
      <div className="space-y-5">
        {visible.map((f) => (
          <FindingCard key={`${f.rank}-${f.lobbyist_name}-${f.agency_short}`} finding={f} />
        ))}
      </div>
    </>
  )
}
