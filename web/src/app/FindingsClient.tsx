"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { clsx } from "clsx"
import Pagination from "./Pagination"
import CardMenu, { type MenuItem } from "./CardMenu"
import {
  copyToClipboard,
  downloadBlob,
  findingAnchorId,
  findingCitation,
  findingSlug,
  findingToMarkdown,
  findingsToCsv,
} from "./lib/exports"
import type { Finding, FindingsPayload, Trail, TrailClient } from "./types"

const PAGE_SIZE = 8

const fmtUSD = (n: number) =>
  n >= 1_000_000_000
    ? `$${(n / 1_000_000_000).toFixed(2)}B`
    : n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(1)}M`
      : `$${n.toLocaleString()}`

// ── Building blocks ────────────────────────────────────────────────────────────

function AgencyBadge({ code }: { code: string }) {
  // Uniform neutral chip across all 24 agencies — the agency name is the data;
  // color was decorative noise.
  return (
    <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold uppercase tracking-wide text-slate-700 ring-1 ring-slate-200">
      {code}
    </span>
  )
}

function VerificationBadge({ status }: { status: Finding["verification_status"] }) {
  if (!status) return null
  const map: Record<string, { label: string; cls: string }> = {
    verified:   { label: "✓ Verified",          cls: "bg-emerald-100 text-emerald-800 ring-emerald-200" },
    partial:    { label: "~ Partially verified", cls: "bg-amber-100 text-amber-800 ring-amber-200" },
    unverified: { label: "⚠ Unverified",         cls: "bg-rose-100 text-rose-800 ring-rose-200" },
  }
  const { label, cls } = map[status] ?? map.unverified
  return (
    <span className={clsx("rounded-full px-3 py-1 text-sm font-semibold ring-1", cls)}>
      {label}
    </span>
  )
}

function ConcentrationBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  // Single coherent severity scale: indigo → amber → rose (cool→hot).
  const bar =
    pct >= 70 ? "bg-rose-500" :
    pct >= 40 ? "bg-amber-500" :
    "bg-indigo-500"
  const label =
    pct >= 70 ? "Very high" :
    pct >= 40 ? "High" :
    "Moderate"
  return (
    <div className="flex items-center gap-4">
      <div className="h-3 w-48 overflow-hidden rounded-full bg-slate-200">
        <div
          className={clsx("h-full rounded-full transition-all", bar)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="tabular-nums text-xl font-bold text-slate-900">{pct}%</span>
        <span className="text-sm font-medium text-slate-500">{label}</span>
      </div>
    </div>
  )
}

function SenateLink({ uuid, url }: { uuid: string | null; url: string | null }) {
  if (!uuid) return <span className="font-mono text-sm text-slate-400">—</span>
  const href = url ?? `https://lda.senate.gov/filings/public/filing/${uuid}/print/`
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-mono text-sm text-indigo-300 underline decoration-dotted hover:text-indigo-200"
      title="Open on Senate LDA public site"
    >
      {uuid.slice(0, 8)}…
    </a>
  )
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-bold text-slate-900">{value}</div>
    </div>
  )
}

// ── Money trail (inline panel on a finding) ───────────────────────────────────

function TrailPanel({ trail }: { trail: Trail }) {
  const [open, setOpen] = useState(false)
  const pctDisc =
    trail.total > 0 ? Math.round((trail.discretionary_total / trail.total) * 100) : 0
  const generated = new Date(trail.generated_at).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
  return (
    <div className="mb-6 overflow-hidden rounded-xl border border-emerald-300 bg-emerald-50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left hover:bg-emerald-100/60"
        aria-expanded={open}
      >
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-emerald-700 px-3 py-1 text-sm font-bold uppercase tracking-wide text-white">
            Money trail
          </span>
          <span className="text-lg font-bold text-emerald-900">
            {fmtUSD(trail.total)} traced
          </span>
          <span className="text-base text-emerald-800">
            {trail.n_clients_with_awards}/{trail.n_clients_total} clients · {fmtUSD(trail.discretionary_total)} discretionary ({pctDisc}%)
          </span>
        </div>
        <span className="text-2xl font-bold text-emerald-700" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div className="border-t border-emerald-300 bg-white px-5 py-5">
          <p className="mb-4 text-base text-slate-700">
            Federal <strong>{trail.award_groups.join(", ")}</strong> awarded by{" "}
            <strong>{trail.agency}</strong> to {trail.lobbyist_label}&apos;s lobbying
            clients, verified by recipient name against USAspending.gov.{" "}
            <span className="text-slate-500">Generated {generated}.</span>
          </p>
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
                {trail.clients.map((c: TrailClient) => (
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
                </tr>
              </tfoot>
            </table>
          </div>
          {trail.misses.length > 0 && (
            <p className="mt-3 text-sm italic text-slate-500">
              No verified {trail.agency} {trail.award_groups.join(", ")} found for:{" "}
              {trail.misses.join(", ")}.
            </p>
          )}
          <p className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-base text-amber-900 ring-1 ring-amber-200">
            <strong>Framing:</strong> conflict-of-interest <em>structure</em>, not proven
            wrongdoing. Discretionary, competitively-awarded grants are the newsworthy
            core; routine program participation is context. Confirm program type, §207
            cooling-off status, and seek comment before publishing a causal claim.
          </p>
        </div>
      )}
    </div>
  )
}

// ── Finding card ───────────────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: Finding }) {
  const incomeM = (finding.total_income / 1_000_000).toFixed(2)
  const pct = Math.round(finding.concentration * 100)
  const isHighConc = pct >= 50
  const anchorId = findingAnchorId(finding)
  const slugBase = `fairguard-${finding.agency_short}-${finding.lobbyist_name
    .toLowerCase()
    .replace(/\s+/g, "-")}`

  const detailHref = `/findings/${findingSlug(finding)}`
  const menu: MenuItem[] = [
    {
      type: "link",
      label: "Open full case →",
      hint: "Single-screen view with all four gates",
      href: detailHref,
    },
    {
      type: "action",
      label: "Copy citation",
      hint: "Plain-text attribution for a story or email",
      onClick: () => copyToClipboard(findingCitation(finding)).then((ok) => {
        if (!ok) throw new Error("clipboard blocked")
      }),
    },
    {
      type: "action",
      label: "Copy link to this finding",
      hint: "Permalink to the full case view",
      onClick: () => {
        const url = `${window.location.origin}${detailHref}`
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
      onClick: () => downloadBlob(findingToMarkdown(finding), `${slugBase}.md`, "text/markdown"),
    },
    {
      type: "action",
      label: "Download CSV",
      hint: `${slugBase}.csv — single row, opens in Excel`,
      onClick: () => downloadBlob(findingsToCsv([finding]), `${slugBase}.csv`, "text/csv"),
    },
    {
      type: "action",
      label: "Download JSON",
      hint: `${slugBase}.json — raw record incl. trail`,
      onClick: () => downloadBlob(JSON.stringify(finding, null, 2), `${slugBase}.json`, "application/json"),
    },
    { type: "divider" },
    {
      type: "action",
      label: "Print this card",
      hint: "Opens the browser print dialog",
      onClick: () => window.print(),
    },
    ...(finding.senate_lda_url || finding.sample_uuid
      ? [{
          type: "link" as const,
          label: "Open Senate LDA filing",
          hint: "lda.senate.gov — opens in a new tab",
          href: finding.senate_lda_url ?? `https://lda.senate.gov/filings/public/filing/${finding.sample_uuid}/print/`,
          external: true,
        }]
      : []),
  ]

  return (
    <article
      id={anchorId}
      className={clsx(
        "scroll-mt-32 rounded-xl border bg-white p-7 shadow-sm transition-shadow hover:shadow-md print:break-inside-avoid",
        isHighConc ? "border-rose-200" : "border-slate-200"
      )}
    >
      {/* Header row */}
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-lg font-bold text-white">
            {finding.rank}
          </div>
          <div>
            <h2 className="leading-tight">{finding.lobbyist_name}</h2>
            <p className="mt-1 text-base text-slate-600">{finding.registrant_name}</p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <AgencyBadge code={finding.agency_short} />
          <VerificationBadge status={finding.verification_status} />
          <CardMenu items={menu} label={`Actions for ${finding.lobbyist_name}`} />
        </div>
      </header>

      {/* Concentration meter */}
      <section className="mb-6 rounded-lg border border-slate-200 bg-slate-50 p-5">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <span className="text-base font-semibold text-slate-700">
            Agency concentration ratio
          </span>
          <span className="tabular-nums text-base text-slate-600">
            <strong className="font-semibold text-slate-900">{finding.agency_filings}</strong>{" "}
            of <strong className="font-semibold text-slate-900">{finding.total_filings}</strong> filings
            target {finding.agency_short.toUpperCase()}
          </span>
        </div>
        <ConcentrationBar value={finding.concentration} />
      </section>

      {/* Prior role */}
      <section className="mb-6">
        <div className="mb-2 flex flex-wrap items-baseline gap-2">
          <h3>Prior role (verbatim LDA disclosure)</h3>
          <span className="text-sm text-slate-500">— self-reported, verify independently</span>
        </div>
        <blockquote className="rounded-lg border-l-4 border-indigo-400 bg-slate-50 px-5 py-3 text-lg leading-relaxed text-slate-800">
          {finding.covered_position}
        </blockquote>
      </section>

      {/* Stats grid */}
      <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox label="Clients" value={finding.n_clients} />
        <StatBox label="Disclosed income" value={`$${incomeM}M`} />
        <StatBox label="Active years" value={`${finding.first_year}–${finding.last_year}`} />
        <StatBox label="Score" value={finding.score.toFixed(2)} />
      </section>

      {/* Money trail (only when a trace run has been keyed to this finding) */}
      {finding.trail && <TrailPanel trail={finding.trail} />}

      {/* Top clients */}
      {finding.top_clients_str && (
        <section className="mb-6">
          <h3 className="mb-2">Top clients (agency-targeting filings)</h3>
          <p className="text-base leading-relaxed text-slate-700">
            {finding.top_clients_str}
          </p>
        </section>
      )}

      {/* Open full case + provenance footer */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-indigo-200 bg-indigo-50 px-5 py-3 print:hidden">
        <span className="text-base text-indigo-900">
          See all four gates (role, money, §207, comment) on one page.
        </span>
        <Link
          href={detailHref}
          className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-base font-semibold text-white transition hover:bg-indigo-700"
        >
          Open full case →
        </Link>
      </div>
      <footer className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg bg-slate-900 px-5 py-3 text-sm">
        <span className="font-semibold text-slate-400">Source</span>
        <span className="text-slate-300">
          Senate LDA UUID: <SenateLink uuid={finding.sample_uuid} url={finding.senate_lda_url} />
        </span>
        <span
          className="max-w-md truncate font-mono text-slate-500"
          title={finding.sample_source}
        >
          {finding.sample_source}
        </span>
      </footer>
    </article>
  )
}

// ── Interactive list with filter, pagination, refresh ──────────────────────────

export default function FindingsClient({
  findings: initialFindings,
  agencies: initialAgencies,
}: {
  findings: Finding[]
  agencies: string[]
}) {
  const [findings, setFindings] = useState<Finding[]>(initialFindings)
  const [agencies, setAgencies] = useState<string[]>(initialAgencies)
  const [selected, setSelected] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`/findings.json?ts=${Date.now()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: FindingsPayload = await res.json()
      const next = data.findings ?? []
      setFindings(next)
      setAgencies([...new Set(next.map((f) => f.agency_short))])
      setRefreshedAt(new Date())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const visible = useMemo(
    () => (selected ? findings.filter((f) => f.agency_short === selected) : findings),
    [findings, selected]
  )
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE))

  // Reset to page 1 whenever the filter changes or the dataset shrinks below the
  // current page; also scroll to the top of the list for keyboard / older users.
  useEffect(() => {
    setPage(1)
  }, [selected, findings.length])

  useEffect(() => {
    if (page > pageCount) setPage(pageCount)
  }, [page, pageCount])

  const pageItems = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const trailCount = findings.filter((f) => f.trail).length

  const goToPage = (p: number) => {
    setPage(p)
    if (typeof window !== "undefined") {
      document.getElementById("findings-list")?.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const filterTag = selected ? `-${selected}` : ""
  const bulkMenu: MenuItem[] = [
    {
      type: "action",
      label: `Download CSV (${visible.length}${selected ? ` ${selected.toUpperCase()}` : ""} findings)`,
      hint: "Flat table — opens in Excel / Sheets",
      onClick: () => downloadBlob(findingsToCsv(visible), `fairguard-findings${filterTag}.csv`, "text/csv"),
    },
    {
      type: "action",
      label: `Download JSON (${visible.length})`,
      hint: "Full records incl. embedded trails",
      onClick: () =>
        downloadBlob(JSON.stringify(visible, null, 2), `fairguard-findings${filterTag}.json`, "application/json"),
    },
    {
      type: "action",
      label: `Download Markdown (${visible.length})`,
      hint: "Concatenated printable summaries",
      onClick: () => {
        const body = visible.map((f) => findingToMarkdown(f)).join("\n\n")
        downloadBlob(body, `fairguard-findings${filterTag}.md`, "text/markdown")
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
      {/* Refresh bar */}
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
            {refreshing ? "Refreshing…" : "↻ Refresh data"}
          </button>
          {trailCount > 0 && (
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-base font-semibold text-emerald-800 ring-1 ring-emerald-200">
              {trailCount} money trail{trailCount !== 1 ? "s" : ""} attached
            </span>
          )}
          <CardMenu items={bulkMenu} label="Export all visible findings" />
        </div>
        <div className="text-sm text-slate-500">
          {error && <span className="font-semibold text-rose-700">refresh failed: {error}</span>}
          {!error && refreshedAt && <span>Last refresh: {refreshedAt.toLocaleTimeString()}</span>}
          {!error && !refreshedAt && (
            <a
              href="/trails"
              className="font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
            >
              View all money trails →
            </a>
          )}
        </div>
      </div>

      {/* Agency filter */}
      <div className="mb-8">
        <p className="mb-3 text-base font-semibold uppercase tracking-wider text-slate-500">
          Filter by agency
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelected(null)}
            className={clsx(
              "rounded-full px-4 py-2 text-base font-semibold transition ring-1",
              selected === null
                ? "bg-slate-900 text-white ring-slate-900"
                : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-100"
            )}
          >
            All ({findings.length})
          </button>
          {agencies.map((a) => {
            const count = findings.filter((f) => f.agency_short === a).length
            const active = selected === a
            return (
              <button
                key={a}
                onClick={() => setSelected(active ? null : a)}
                className={clsx(
                  "rounded-full px-4 py-2 text-base font-bold uppercase tracking-wide transition ring-1",
                  active
                    ? "bg-indigo-600 text-white ring-indigo-600"
                    : "bg-white text-slate-600 ring-slate-300 hover:border-indigo-300 hover:text-indigo-700"
                )}
              >
                {a} <span className="font-normal opacity-75">({count})</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Selection summary */}
      {selected && (
        <p className="mb-5 text-base text-slate-600">
          Showing <strong className="text-slate-900">{visible.length}</strong> finding
          {visible.length !== 1 ? "s" : ""} for{" "}
          <span className="font-bold uppercase text-slate-900">{selected}</span>
          {" — "}
          <button
            onClick={() => setSelected(null)}
            className="font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            show all
          </button>
        </p>
      )}

      {/* Cards */}
      <div id="findings-list" className="space-y-6 scroll-mt-32">
        {pageItems.map((f) => (
          <FindingCard
            key={`${f.rank}-${f.lobbyist_name}-${f.agency_short}`}
            finding={f}
          />
        ))}
      </div>

      <Pagination
        page={page}
        pageCount={pageCount}
        total={visible.length}
        pageSize={PAGE_SIZE}
        onPage={goToPage}
        itemLabel="findings"
      />
    </>
  )
}
