"use client"

import { useEffect, useMemo, useState } from "react"
import { clsx } from "clsx"
import Pagination from "../Pagination"
import CardMenu, { type MenuItem } from "../CardMenu"
import {
  copyToClipboard,
  downloadBlob,
  trailAnchorId,
  trailCitation,
  trailToCsv,
  trailToMarkdown,
  trailsToCsv,
} from "../lib/exports"
import type { Trail, TrailsPayload } from "../types"

const PAGE_SIZE = 5

const fmtUSD = (n: number) =>
  n >= 1_000_000_000
    ? `$${(n / 1_000_000_000).toFixed(2)}B`
    : n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(1)}M`
      : `$${n.toLocaleString()}`

function TrailCard({ trail }: { trail: Trail }) {
  const pctDisc =
    trail.total > 0 ? Math.round((trail.discretionary_total / trail.total) * 100) : 0
  const generated = new Date(trail.generated_at).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
  const matchSummary = (trail.match ?? [])
    .map((m) => `${m.lobbyist_name} (${m.agency_short.toUpperCase()})`)
    .join(", ")
  const anchorId = trailAnchorId(trail)
  const slugBase = `fairguard-trail-${trail.case_id}`

  const menu: MenuItem[] = [
    {
      type: "action",
      label: "Copy citation",
      hint: "Plain-text attribution for a story or email",
      onClick: () => copyToClipboard(trailCitation(trail)).then((ok) => {
        if (!ok) throw new Error("clipboard blocked")
      }),
    },
    {
      type: "action",
      label: "Copy link to this trail",
      hint: "Shareable URL with this card pre-scrolled",
      onClick: () => {
        const url = `${window.location.origin}${window.location.pathname}#${anchorId}`
        return copyToClipboard(url).then((ok) => {
          if (!ok) throw new Error("clipboard blocked")
        })
      },
    },
    { type: "divider" },
    {
      type: "action",
      label: "Download Markdown",
      hint: `${slugBase}.md — printable summary`,
      onClick: () => downloadBlob(trailToMarkdown(trail), `${slugBase}.md`, "text/markdown"),
    },
    {
      type: "action",
      label: "Download CSV (per client)",
      hint: `${slugBase}.csv — one row per client`,
      onClick: () => downloadBlob(trailToCsv(trail), `${slugBase}.csv`, "text/csv"),
    },
    {
      type: "action",
      label: "Download JSON",
      hint: `${slugBase}.json — raw payload`,
      onClick: () => downloadBlob(JSON.stringify(trail, null, 2), `${slugBase}.json`, "application/json"),
    },
    { type: "divider" },
    {
      type: "action",
      label: "Print this trail",
      hint: "Opens the browser print dialog",
      onClick: () => window.print(),
    },
    {
      type: "link",
      label: "Search on USAspending.gov",
      hint: `Pre-fills agency: ${trail.agency}`,
      href: `https://www.usaspending.gov/search?hash=${encodeURIComponent(trail.agency)}`,
      external: true,
    },
  ]

  return (
    <article
      id={anchorId}
      className="scroll-mt-32 rounded-xl border border-emerald-200 bg-white p-7 shadow-sm print:break-inside-avoid"
    >
      <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h2 className="leading-tight">{trail.lobbyist_label}</h2>
          <p className="mt-1 text-base text-slate-600">
            <span className="font-semibold text-slate-900">{trail.agency}</span>{" "}
            · <span className="uppercase tracking-wide">{trail.award_groups.join(", ")}</span>
          </p>
          {matchSummary && (
            <p className="mt-1 text-sm text-slate-500">
              Linked to scan finding{trail.match && trail.match.length > 1 ? "s" : ""}:{" "}
              <span className="font-semibold text-slate-700">{matchSummary}</span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-start gap-3">
          <div className="rounded-lg bg-emerald-50 px-4 py-3 text-right ring-1 ring-emerald-200">
            <div className="font-mono text-3xl font-bold tabular-nums text-emerald-700">
              {fmtUSD(trail.total)}
            </div>
            <div className="text-sm font-medium text-emerald-800">total traced</div>
          </div>
          <CardMenu items={menu} label={`Actions for ${trail.lobbyist_label}`} />
        </div>
      </header>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Discretionary
          </div>
          <div className="mt-1 font-mono text-lg font-bold text-emerald-700">
            {fmtUSD(trail.discretionary_total)}
          </div>
          <div className="text-sm text-slate-500">{pctDisc}% of total</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Routine
          </div>
          <div className="mt-1 font-mono text-lg font-bold text-slate-700">
            {fmtUSD(trail.routine_total)}
          </div>
          <div className="text-sm text-slate-500">context, not story</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Clients
          </div>
          <div className="mt-1 text-lg font-bold text-slate-900">
            {trail.n_clients_with_awards} / {trail.n_clients_total}
          </div>
          <div className="text-sm text-slate-500">with awards</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Generated
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-700">{generated}</div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-base">
          <thead className="bg-slate-50">
            <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
              <th className="px-4 py-2 font-semibold">Client</th>
              <th className="px-4 py-2 text-right font-semibold">Total</th>
              <th className="px-4 py-2 text-right font-semibold">Awards</th>
              <th className="px-4 py-2 text-right font-semibold">Discretionary</th>
            </tr>
          </thead>
          <tbody>
            {trail.clients.map((c) => (
              <tr key={c.label} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-900">{c.label}</td>
                <td className="px-4 py-2 text-right font-mono tabular-nums font-semibold text-slate-900">
                  {fmtUSD(c.total)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                  {c.n_awards}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-emerald-700">
                  {fmtUSD(c.discretionary_amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {trail.misses.length > 0 && (
        <p className="mt-3 text-sm italic text-slate-500">
          No verified {trail.agency} {trail.award_groups.join(", ")} found for:{" "}
          {trail.misses.join(", ")}.
        </p>
      )}
    </article>
  )
}

export default function TrailsClient({ initialTrails }: { initialTrails: Trail[] }) {
  const [trails, setTrails] = useState<Trail[]>(initialTrails)
  const [page, setPage] = useState(1)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`/trails.json?ts=${Date.now()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: TrailsPayload = await res.json()
      setTrails(data.trails ?? [])
      setRefreshedAt(new Date())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const pageCount = useMemo(() => Math.max(1, Math.ceil(trails.length / PAGE_SIZE)), [trails.length])
  useEffect(() => {
    if (page > pageCount) setPage(pageCount)
  }, [page, pageCount])

  const pageItems = trails.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const goToPage = (p: number) => {
    setPage(p)
    if (typeof window !== "undefined") {
      document.getElementById("trails-list")?.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const bulkMenu: MenuItem[] = [
    {
      type: "action",
      label: `Download CSV (${trails.length} trails)`,
      hint: "One row per trail × client — pivots in Excel",
      onClick: () => downloadBlob(trailsToCsv(trails), "fairguard-trails.csv", "text/csv"),
    },
    {
      type: "action",
      label: "Download JSON",
      hint: "Raw trails.json payload",
      onClick: () => downloadBlob(JSON.stringify(trails, null, 2), "fairguard-trails.json", "application/json"),
    },
    {
      type: "action",
      label: "Download Markdown",
      hint: "Concatenated trail summaries",
      onClick: () => {
        const body = trails.map((t) => trailToMarkdown(t)).join("\n\n")
        downloadBlob(body, "fairguard-trails.md", "text/markdown")
      },
    },
    { type: "divider" },
    {
      type: "action",
      label: "Print this page",
      hint: "Browser print — paginates by card",
      onClick: () => window.print(),
    },
  ]

  return (
    <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
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
            {refreshing ? "Refreshing…" : "↻ Refresh trails"}
          </button>
          {trails.length > 0 && (
            <CardMenu items={bulkMenu} label="Export all trails" />
          )}
        </div>
        <div className="text-sm text-slate-500">
          {error && <span className="font-semibold text-rose-700">refresh failed: {error}</span>}
          {!error && refreshedAt && <span>Last refresh: {refreshedAt.toLocaleTimeString()}</span>}
          {!error && !refreshedAt && (
            <span>
              <strong className="text-slate-900">{trails.length}</strong> trail{trails.length !== 1 ? "s" : ""} loaded
            </span>
          )}
        </div>
      </div>

      {trails.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-16 text-center">
          <p className="mb-3 text-xl font-semibold text-slate-600">No money trails yet</p>
          <p className="text-base text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-sm">
              uv run scripts/04_award_tracer.py --case skill/federal-award-tracer/cases/steinberg_doe.json
            </code>{" "}
            then click ↻ Refresh.
          </p>
        </div>
      ) : (
        <>
          <div id="trails-list" className="space-y-6 scroll-mt-32">
            {pageItems.map((t) => (
              <TrailCard key={t.case_id} trail={t} />
            ))}
          </div>
          <Pagination
            page={page}
            pageCount={pageCount}
            total={trails.length}
            pageSize={PAGE_SIZE}
            onPage={goToPage}
            itemLabel="trails"
          />
        </>
      )}
    </>
  )
}
