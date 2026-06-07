"use client"

import { useEffect, useMemo, useState } from "react"
import { clsx } from "clsx"
import Pagination from "../Pagination"
import CardMenu, { type MenuItem } from "../CardMenu"
import { copyToClipboard, downloadBlob } from "../lib/exports"
import type { PressrelPayload, PressrelReport } from "../types"

const PAGE_SIZE = 4

function ReportCard({ report }: { report: PressrelReport }) {
  const [open, setOpen] = useState(false)
  const generated = new Date(report.generated_at).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
  const matchSummary = (report.match ?? [])
    .map((m) => `${m.lobbyist_name} (${m.agency_short.toUpperCase()})`)
    .join(", ")
  const slugBase = `fairguard-pressrel-${report.case_id}`

  const menu: MenuItem[] = [
    {
      type: "action",
      label: "Copy link to this report",
      hint: "Shareable URL with the page pre-scrolled",
      onClick: () => {
        const url = `${window.location.origin}/pressrel#report-${report.case_id}`
        return copyToClipboard(url).then((ok) => {
          if (!ok) throw new Error("clipboard blocked")
        })
      },
    },
    { type: "divider" },
    {
      type: "action",
      label: "Download JSON",
      hint: `${slugBase}.json — full report payload`,
      onClick: () => downloadBlob(JSON.stringify(report, null, 2), `${slugBase}.json`, "application/json"),
    },
    {
      type: "action",
      label: "Download CSV (per match)",
      hint: `${slugBase}.csv — one row per match`,
      onClick: () => {
        const header = ["client", "date", "member_name", "party", "state", "chamber", "title", "url"]
        const rows = report.matches.map((m) => [
          m.client ?? "", m.date ?? "", m.member_name ?? "", m.party ?? "",
          m.state ?? "", m.chamber ?? "", (m.title ?? "").replace(/"/g, '""'), m.url ?? "",
        ])
        const csv = [header, ...rows]
          .map((r) => r.map((c) => `"${c}"`).join(","))
          .join("\r\n")
        downloadBlob(csv, `${slugBase}.csv`, "text/csv")
      },
    },
    { type: "divider" },
    {
      type: "action",
      label: "Print this report",
      hint: "Opens the browser print dialog",
      onClick: () => window.print(),
    },
  ]

  return (
    <article
      id={`report-${report.case_id}`}
      className="scroll-mt-32 rounded-xl border border-amber-200 bg-white p-7 shadow-sm print:break-inside-avoid"
    >
      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h2 className="leading-tight">{report.label}</h2>
          {matchSummary && (
            <p className="mt-1 text-sm text-slate-500">
              Linked to scan finding{report.match && report.match.length > 1 ? "s" : ""}:{" "}
              <span className="font-semibold text-slate-700">{matchSummary}</span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-start gap-3">
          <div className="rounded-lg bg-amber-50 px-4 py-3 text-right ring-1 ring-amber-200">
            <div className="font-mono text-3xl font-bold tabular-nums text-amber-800">
              {report.n_matches}
            </div>
            <div className="text-sm font-medium text-amber-700">
              mentions · {report.n_distinct_members} members
            </div>
          </div>
          <CardMenu items={menu} label={`Actions for ${report.label}`} />
        </div>
      </header>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Clients searched</div>
          <div className="mt-1 text-lg font-bold text-slate-900">{report.n_clients}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Members</div>
          <div className="mt-1 text-lg font-bold text-slate-900">{report.n_distinct_members}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total matches</div>
          <div className="mt-1 text-lg font-bold text-slate-900">{report.n_matches}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Generated</div>
          <div className="mt-1 text-sm font-semibold text-slate-700">{generated}</div>
        </div>
      </div>

      {/* Per-client tally */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-base">
          <thead className="bg-slate-50">
            <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
              <th className="px-4 py-2 font-semibold">Client</th>
              <th className="px-4 py-2 text-right font-semibold">Mentions</th>
              <th className="px-4 py-2 text-right font-semibold">Members</th>
              <th className="px-4 py-2 font-semibold">First</th>
              <th className="px-4 py-2 font-semibold">Last</th>
            </tr>
          </thead>
          <tbody>
            {report.per_client.map((pc) => (
              <tr key={pc.client} className="border-t border-slate-100">
                <td className="px-4 py-2 font-semibold text-slate-900">{pc.client}</td>
                <td className="px-4 py-2 text-right tabular-nums">{pc.n_matches}</td>
                <td className="px-4 py-2 text-right tabular-nums">{pc.n_distinct_members}</td>
                <td className="px-4 py-2 tabular-nums text-slate-600">{pc.first_date || "—"}</td>
                <td className="px-4 py-2 tabular-nums text-slate-600">{pc.last_date || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Expandable match list */}
      {report.matches.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-base font-semibold text-slate-700 hover:bg-slate-200"
            aria-expanded={open}
          >
            {open ? "▾ Hide" : "▸ Show"} all {report.matches.length} matches
          </button>
          {open && (
            <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr className="text-left text-xs uppercase tracking-wider text-slate-600">
                    <th className="px-3 py-2 font-semibold">Date</th>
                    <th className="px-3 py-2 font-semibold">Member</th>
                    <th className="px-3 py-2 font-semibold">Title</th>
                    <th className="px-3 py-2 font-semibold">Snippet</th>
                  </tr>
                </thead>
                <tbody>
                  {report.matches.slice(0, 50).map((m, i) => (
                    <tr key={`${m.url}-${i}`} className="border-t border-slate-100 align-top">
                      <td className="px-3 py-2 whitespace-nowrap text-slate-600">{m.date}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className="font-semibold text-slate-900">{m.member_name}</span>
                        <span className="ml-1 text-xs text-slate-500">
                          ({(m.party ?? "?")[0]}·{m.state}·{(m.chamber ?? "?")[0]})
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <a
                          href={m.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 underline decoration-dotted hover:text-indigo-800"
                        >
                          {m.title}
                        </a>
                      </td>
                      <td
                        className="px-3 py-2 text-slate-700"
                        // Snippet is generated by the script and includes **bold**
                        // markdown around the matched phrase. Strip the asterisks
                        // for the table render but keep the wrapping marker.
                        dangerouslySetInnerHTML={{
                          __html: (m.snippet || "")
                            .replace(/&/g, "&amp;")
                            .replace(/</g, "&lt;")
                            .replace(/>/g, "&gt;")
                            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"),
                        }}
                      />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </article>
  )
}

export default function PressrelClient({ initialReports }: { initialReports: PressrelReport[] }) {
  const [reports, setReports] = useState<PressrelReport[]>(initialReports)
  const [page, setPage] = useState(1)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`/press_releases.json?ts=${Date.now()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: PressrelPayload = await res.json()
      setReports(data.reports ?? [])
      setRefreshedAt(new Date())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const pageCount = useMemo(() => Math.max(1, Math.ceil(reports.length / PAGE_SIZE)), [reports.length])
  useEffect(() => {
    if (page > pageCount) setPage(pageCount)
  }, [page, pageCount])
  const pageItems = reports.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const goToPage = (p: number) => {
    setPage(p)
    if (typeof window !== "undefined") {
      document.getElementById("pressrel-list")?.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4">
        <button
          onClick={refresh}
          disabled={refreshing}
          className={clsx(
            "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-base font-semibold transition",
            refreshing
              ? "bg-slate-100 text-slate-400"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          )}
        >
          {refreshing ? "Refreshing…" : "↻ Refresh reports"}
        </button>
        <div className="text-sm text-slate-500">
          {error && <span className="font-semibold text-rose-700">refresh failed: {error}</span>}
          {!error && refreshedAt && <span>Last refresh: {refreshedAt.toLocaleTimeString()}</span>}
          {!error && !refreshedAt && (
            <span>
              <strong className="text-slate-900">{reports.length}</strong> report{reports.length !== 1 ? "s" : ""} loaded
            </span>
          )}
        </div>
      </div>

      {reports.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-16 text-center">
          <p className="mb-3 text-xl font-semibold text-slate-600">No press-release reports yet</p>
          <p className="text-base text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-sm">
              uv run scripts/05_pressrel_search.py --case skill/press-release-cross-ref/cases/steinberg_clients.json
            </code>{" "}
            then click ↻ Refresh.
          </p>
        </div>
      ) : (
        <>
          <div id="pressrel-list" className="space-y-6 scroll-mt-32">
            {pageItems.map((r) => (
              <ReportCard key={r.case_id} report={r} />
            ))}
          </div>
          <Pagination
            page={page}
            pageCount={pageCount}
            total={reports.length}
            pageSize={PAGE_SIZE}
            onPage={goToPage}
            itemLabel="reports"
          />
        </>
      )}
    </>
  )
}
