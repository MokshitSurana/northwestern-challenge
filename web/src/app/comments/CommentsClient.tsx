"use client"

import { useMemo, useState } from "react"
import { clsx } from "clsx"
import CardMenu, { type MenuItem } from "../CardMenu"
import { copyToClipboard, downloadBlob } from "../lib/exports"
import type {
  CommentEntry,
  CommentEvent,
  CommentLogPayload,
  CommentStatus,
} from "../types"

// ── Status color scheme ───────────────────────────────────────────────────────

const STATUS_COLORS: Record<CommentStatus, string> = {
  not_drafted:             "bg-slate-100 text-slate-600 ring-slate-200",
  not_sent:                "bg-slate-100 text-slate-700 ring-slate-300",
  sent:                    "bg-blue-100 text-blue-800 ring-blue-200",
  acknowledged:            "bg-indigo-100 text-indigo-800 ring-indigo-200",
  awaiting_substantive:    "bg-amber-100 text-amber-800 ring-amber-200",
  responded:               "bg-emerald-100 text-emerald-800 ring-emerald-200",
  no_response_by_deadline: "bg-rose-100 text-rose-800 ring-rose-200",
  closed_response:         "bg-emerald-50 text-emerald-700 ring-emerald-100",
  closed_no_response:      "bg-slate-200 text-slate-700 ring-slate-300",
  escalated_to_counsel:    "bg-rose-600 text-white ring-rose-700",
}

const EVENT_KIND_LABELS: Record<string, { label: string; cls: string }> = {
  sent:              { label: "📤 Sent",              cls: "bg-blue-50 text-blue-700 ring-blue-200" },
  acknowledged:      { label: "👁 Acknowledged",      cls: "bg-indigo-50 text-indigo-700 ring-indigo-200" },
  substantive_reply: { label: "✓ Substantive reply", cls: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  followup_sent:     { label: "↻ Follow-up",          cls: "bg-amber-50 text-amber-700 ring-amber-200" },
  closed:            { label: "✅ Closed",             cls: "bg-slate-100 text-slate-700 ring-slate-300" },
  legal_threat:      { label: "🚨 Legal threat",      cls: "bg-rose-100 text-rose-800 ring-rose-300" },
}

// ── Subcomponents ─────────────────────────────────────────────────────────────

function StatusBadge({ status, label }: { status: CommentStatus; label: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1",
        STATUS_COLORS[status] || "bg-slate-100 text-slate-700 ring-slate-200"
      )}
    >
      {label}
    </span>
  )
}

function DeadlineCell({
  deadline,
  days,
}: {
  deadline: string | null | undefined
  days: number | null
}) {
  if (!deadline) return <span className="text-slate-400">—</span>
  if (days == null) return <span className="font-mono text-sm">{deadline}</span>
  const overdue = days < 0
  const urgent = days <= 2 && days >= 0
  return (
    <span
      className={clsx(
        "inline-flex items-baseline gap-1 font-mono text-sm",
        overdue ? "text-rose-700 font-bold" : urgent ? "text-amber-700 font-semibold" : "text-slate-700"
      )}
    >
      {deadline}
      <span className="text-xs">
        ({days >= 0 ? "+" : ""}
        {days}d)
      </span>
    </span>
  )
}

function Timeline({ events }: { events: CommentEvent[] }) {
  if (!events.length) {
    return (
      <p className="text-base italic text-slate-500">
        No events logged yet. The draft is ready in the linked packet.
      </p>
    )
  }
  return (
    <ol className="space-y-3">
      {events.map((ev, i) => {
        const meta = EVENT_KIND_LABELS[ev.kind] || {
          label: ev.kind,
          cls: "bg-slate-100 text-slate-700 ring-slate-200",
        }
        return (
          <li
            key={`${ev.at}-${i}`}
            className="rounded-lg border border-slate-200 bg-white px-4 py-3"
          >
            <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
              <span
                className={clsx(
                  "inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-semibold ring-1",
                  meta.cls
                )}
              >
                {meta.label}
              </span>
              <span className="font-mono text-xs text-slate-500">
                {new Date(ev.at).toLocaleString()}
              </span>
            </div>
            {ev.by && <p className="text-sm text-slate-600">by {ev.by}</p>}
            {ev.addresses && ev.addresses.length > 0 && (
              <p className="text-sm text-slate-600">
                to: <span className="font-mono">{ev.addresses.join(", ")}</span>
              </p>
            )}
            {ev.summary && <p className="mt-1 text-base text-slate-800">{ev.summary}</p>}
            {ev.pointer && (
              <a
                href={ev.pointer}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-block text-sm font-medium text-indigo-600 underline decoration-dotted hover:text-indigo-800"
              >
                Pointer → {ev.pointer}
              </a>
            )}
            {ev.response_kind && (
              <p className="mt-1 text-sm">
                <span className="font-semibold text-slate-700">Outcome:</span>{" "}
                {ev.response_kind === "response" ? "received a response" : "no response"}
              </p>
            )}
          </li>
        )
      })}
    </ol>
  )
}

function EntryCard({ entry }: { entry: CommentEntry }) {
  const [open, setOpen] = useState(false)
  const slugBase = `fairguard-comments-${entry.key}`

  const cliCommands = [
    `# Log that you sent the request to ${entry.firm}:`,
    `uv run scripts/07_comment_tracker.py log ${entry.key} sent --addresses "press@firm.com,contact@firm.com"`,
    "",
    `# After a reply:`,
    `uv run scripts/07_comment_tracker.py log ${entry.key} substantive_reply --pointer URL --summary "..."`,
    "",
    `# Close out:`,
    `uv run scripts/07_comment_tracker.py log ${entry.key} closed --kind response --summary "..."`,
  ].join("\n")

  const menu: MenuItem[] = [
    {
      type: "action",
      label: "Copy CLI commands for this firm",
      hint: "Pastes the log invocations for sent / replied / closed",
      onClick: () =>
        copyToClipboard(cliCommands).then((ok) => {
          if (!ok) throw new Error("clipboard blocked")
        }),
    },
    {
      type: "action",
      label: "Copy firm key",
      hint: entry.key,
      onClick: () =>
        copyToClipboard(entry.key).then((ok) => {
          if (!ok) throw new Error("clipboard blocked")
        }),
    },
    { type: "divider" },
    {
      type: "action",
      label: "Download timeline JSON",
      hint: `${slugBase}.json — full event timeline`,
      onClick: () =>
        downloadBlob(JSON.stringify(entry, null, 2), `${slugBase}.json`, "application/json"),
    },
    {
      type: "action",
      label: "Print this entry",
      hint: "Opens the browser print dialog",
      onClick: () => window.print(),
    },
  ]

  return (
    <article
      id={`entry-${entry.key}`}
      className="scroll-mt-32 rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:break-inside-avoid"
    >
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={entry.status} label={entry.status_label} />
            {Array.isArray(entry.scan_rank) ? (
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-700">
                scan rank #{entry.scan_rank.join(", #")}
              </span>
            ) : entry.scan_rank != null ? (
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-700">
                scan rank #{entry.scan_rank}
              </span>
            ) : null}
          </div>
          <h2 className="leading-tight">{entry.firm}</h2>
          <p className="mt-1 text-base text-slate-600">{entry.case}</p>
        </div>
        <CardMenu items={menu} label={`Actions for ${entry.firm}`} />
      </header>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Events
          </div>
          <div className="mt-1 text-lg font-bold text-slate-900">{entry.metrics.n_events}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Days since send
          </div>
          <div className="mt-1 text-lg font-bold text-slate-900">
            {entry.metrics.days_since_send != null ? entry.metrics.days_since_send : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Deadline
          </div>
          <div className="mt-1">
            <DeadlineCell
              deadline={entry.deadline ?? null}
              days={entry.metrics.days_until_deadline}
            />
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Substantive?
          </div>
          <div className="mt-1 text-lg font-bold text-slate-900">
            {entry.metrics.has_substantive ? "Yes" : "—"}
          </div>
        </div>
      </div>

      {entry.addresses_used && entry.addresses_used.length > 0 && (
        <p className="mb-3 text-sm text-slate-600">
          <span className="font-semibold">Addresses used:</span>{" "}
          <span className="font-mono">{entry.addresses_used.join(", ")}</span>
        </p>
      )}

      <p className="mb-4 text-sm text-slate-500">
        Draft packet:{" "}
        <span className="font-mono text-slate-700">{entry.draft_path}</span>
      </p>

      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-base font-semibold text-slate-700 hover:bg-slate-200"
        aria-expanded={open}
      >
        {open ? "▾ Hide" : "▸ Show"} timeline ({entry.metrics.n_events} event
        {entry.metrics.n_events !== 1 ? "s" : ""})
      </button>
      {open && (
        <div className="mt-4">
          <Timeline events={entry.events} />
        </div>
      )}
    </article>
  )
}

// ── Status filter chips ───────────────────────────────────────────────────────

const STATUS_GROUPS: {
  id: string
  statuses: CommentStatus[]
  label: string
  cls: string
}[] = [
  {
    id: "urgent",
    statuses: ["escalated_to_counsel", "no_response_by_deadline"],
    label: "⚠ Urgent",
    cls: "bg-rose-100 text-rose-800 ring-rose-300",
  },
  {
    id: "active",
    statuses: ["sent", "acknowledged", "awaiting_substantive"],
    label: "⏳ Active",
    cls: "bg-amber-100 text-amber-800 ring-amber-300",
  },
  {
    id: "replied",
    statuses: ["responded", "closed_response"],
    label: "✓ Replied",
    cls: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  },
  {
    id: "closed",
    statuses: ["closed_no_response"],
    label: "❌ No reply",
    cls: "bg-slate-200 text-slate-700 ring-slate-300",
  },
  {
    id: "todo",
    statuses: ["not_drafted", "not_sent"],
    label: "⬜ Not sent",
    cls: "bg-slate-100 text-slate-700 ring-slate-200",
  },
]

export default function CommentsClient({ initialData }: { initialData: CommentLogPayload }) {
  const [data, setData] = useState<CommentLogPayload>(initialData)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeGroup, setActiveGroup] = useState<string | null>(null)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`/comment_log.json?ts=${Date.now()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const next = (await res.json()) as CommentLogPayload
      setData(next)
      setRefreshedAt(new Date())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const visible = useMemo(() => {
    if (!activeGroup) return data.entries
    const group = STATUS_GROUPS.find((g) => g.id === activeGroup)
    if (!group) return data.entries
    return data.entries.filter((e) => group.statuses.includes(e.status))
  }, [data.entries, activeGroup])

  const groupCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const g of STATUS_GROUPS) {
      counts[g.id] = data.entries.filter((e) => g.statuses.includes(e.status)).length
    }
    return counts
  }, [data.entries])

  return (
    <>
      {/* Refresh strip */}
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
          {refreshing ? "Refreshing…" : "↻ Refresh"}
        </button>
        <div className="text-sm text-slate-500">
          {error && (
            <span className="font-semibold text-rose-700">refresh failed: {error}</span>
          )}
          {!error && refreshedAt && <span>Last refresh: {refreshedAt.toLocaleTimeString()}</span>}
          {!error && !refreshedAt && (
            <span>
              <strong className="text-slate-900">{data.n_entries}</strong> firm
              {data.n_entries !== 1 ? "s" : ""} tracked
              {data.n_warnings > 0 && (
                <span className="ml-3 rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                  {data.n_warnings} validation warning{data.n_warnings !== 1 ? "s" : ""}
                </span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* Status filter chips */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Filter
        </span>
        <button
          onClick={() => setActiveGroup(null)}
          className={clsx(
            "rounded-full px-4 py-2 text-sm font-semibold transition ring-1",
            activeGroup === null
              ? "bg-slate-900 text-white ring-slate-900"
              : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-100"
          )}
        >
          All ({data.entries.length})
        </button>
        {STATUS_GROUPS.map((g) => (
          <button
            key={g.id}
            onClick={() => setActiveGroup(activeGroup === g.id ? null : g.id)}
            disabled={groupCounts[g.id] === 0}
            className={clsx(
              "rounded-full px-4 py-2 text-sm font-semibold transition ring-1",
              activeGroup === g.id
                ? g.cls + " ring-2"
                : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-100",
              groupCounts[g.id] === 0 && "opacity-50 cursor-not-allowed"
            )}
          >
            {g.label} ({groupCounts[g.id]})
          </button>
        ))}
      </div>

      {/* Validation warnings (rare; only if comment_log.json is malformed) */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="mb-6 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <p className="mb-2 text-sm font-bold text-amber-900">Schema warnings</p>
          <ul className="space-y-1 text-sm text-amber-800">
            {data.warnings.map((w, i) => (
              <li key={i} className="font-mono">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Entry list */}
      {visible.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-16 text-center">
          <p className="mb-3 text-xl font-semibold text-slate-600">
            No entries match the current filter
          </p>
          <p className="text-base text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-sm">
              uv run scripts/07_comment_tracker.py export
            </code>{" "}
            to regenerate the feed.
          </p>
        </div>
      ) : (
        <div id="comments-list" className="space-y-5 scroll-mt-32">
          {visible.map((entry) => (
            <EntryCard key={entry.key} entry={entry} />
          ))}
        </div>
      )}
    </>
  )
}
