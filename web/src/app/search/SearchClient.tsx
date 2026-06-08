"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { clsx } from "clsx"

export type SearchEntry = {
  type: "lobbyist" | "firm" | "client" | "agency" | "legislator"
  name: string
  hint: string
  summary: string
  href: string
  external?: boolean
  tags: string[]
}

const TYPE_LABEL: Record<SearchEntry["type"], string> = {
  lobbyist: "Lobbyists",
  firm: "Firms",
  agency: "Agencies",
  client: "Clients",
  legislator: "Legislators",
}

const TYPE_TONE: Record<SearchEntry["type"], string> = {
  lobbyist:   "bg-indigo-100 text-indigo-800 ring-indigo-200",
  firm:       "bg-violet-100 text-violet-800 ring-violet-200",
  agency:     "bg-slate-100 text-slate-700 ring-slate-200",
  client:     "bg-emerald-100 text-emerald-800 ring-emerald-200",
  legislator: "bg-amber-100 text-amber-800 ring-amber-200",
}

const PAGE_SIZE = 25

export default function SearchClient({
  entries, counts,
}: {
  entries: SearchEntry[]
  counts: Record<string, number>
}) {
  const [query, setQuery] = useState("")
  const [type, setType] = useState<SearchEntry["type"] | "all">("all")
  const [shown, setShown] = useState(PAGE_SIZE)

  // Sync the query with ?q= in the URL on first paint (deep-linkable searches).
  useEffect(() => {
    if (typeof window === "undefined") return
    const params = new URLSearchParams(window.location.search)
    const q = params.get("q")
    if (q) setQuery(q)
    const t = params.get("type") as SearchEntry["type"] | null
    if (t && t in TYPE_LABEL) setType(t)
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    const params = new URLSearchParams(window.location.search)
    if (query) params.set("q", query); else params.delete("q")
    if (type !== "all") params.set("type", type); else params.delete("type")
    const next = params.toString()
    const url = next ? `${window.location.pathname}?${next}` : window.location.pathname
    window.history.replaceState(null, "", url)
  }, [query, type])

  const results = useMemo(() => {
    const q = query.trim().toUpperCase()
    return entries.filter((e) => {
      if (type !== "all" && e.type !== type) return false
      if (!q) return true
      if (e.name.toUpperCase().includes(q)) return true
      if (e.hint.toUpperCase().includes(q)) return true
      if (e.summary.toUpperCase().includes(q)) return true
      if (e.tags.some((t) => t.toUpperCase().includes(q))) return true
      return false
    })
  }, [entries, query, type])

  useEffect(() => { setShown(PAGE_SIZE) }, [query, type])

  const visible = results.slice(0, shown)

  return (
    <>
      {/* Search bar ─────────────────────────────────────────────────────── */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="fg-search" className="mb-2 block text-sm font-semibold uppercase tracking-wider text-slate-500">
          Search
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            id="fg-search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Cargill, Bridenstine, USDA, Steinberg, Lummis…"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-lg text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            autoFocus
            autoComplete="off"
            spellCheck={false}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="rounded-lg border border-slate-300 px-4 py-3 text-base font-semibold text-slate-600 hover:bg-slate-50"
            >
              Clear
            </button>
          )}
        </div>
        <p className="mt-3 text-sm text-slate-500">
          Matches name, descriptor, summary, or tag (case-insensitive substring). Press
          ⌘K or focus the box and start typing.
        </p>
      </div>

      {/* Type filter ────────────────────────────────────────────────────── */}
      <div className="mb-6 flex flex-wrap gap-2">
        <Chip active={type === "all"} onClick={() => setType("all")} label={`All (${entries.length})`} tone="bg-slate-900 text-white ring-slate-900" />
        {(Object.keys(TYPE_LABEL) as SearchEntry["type"][]).map((t) => (
          <Chip
            key={t}
            active={type === t}
            onClick={() => setType(type === t ? "all" : t)}
            label={`${TYPE_LABEL[t]} (${counts[t] ?? 0})`}
            tone={TYPE_TONE[t]}
          />
        ))}
      </div>

      {/* Result summary ─────────────────────────────────────────────────── */}
      <p className="mb-4 text-base text-slate-600">
        {results.length === 0 ? (
          <span>
            <strong className="text-slate-900">No matches.</strong> Try a shorter query
            or clear the type filter.
          </span>
        ) : (
          <span>
            <strong className="text-slate-900">{results.length.toLocaleString()}</strong>{" "}
            {results.length === 1 ? "match" : "matches"}
            {query && (
              <>
                {" "}for <span className="font-semibold text-slate-900">&ldquo;{query}&rdquo;</span>
              </>
            )}
            {type !== "all" && (
              <>
                {" "}in <span className="font-semibold text-slate-900">{TYPE_LABEL[type]}</span>
              </>
            )}
          </span>
        )}
      </p>

      {/* Results ─────────────────────────────────────────────────────────── */}
      {results.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="mb-2 text-lg font-semibold text-slate-700">Nothing found.</p>
          <p className="text-base text-slate-600">
            FairGuard only indexes names it has seen in LDA, USAspending, or congressional
            press releases. A blank result doesn&apos;t mean the entity is clean — it may
            just be outside the corpus.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {visible.map((e, i) => (
            <li key={`${e.type}-${e.name}-${i}`}>
              <ResultRow entry={e} highlight={query} />
            </li>
          ))}
        </ul>
      )}

      {visible.length < results.length && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={() => setShown((n) => n + PAGE_SIZE)}
            className="rounded-lg bg-indigo-600 px-5 py-3 text-base font-semibold text-white transition hover:bg-indigo-700"
          >
            Show {Math.min(PAGE_SIZE, results.length - visible.length)} more
            <span className="ml-2 text-indigo-200">({results.length - visible.length} remaining)</span>
          </button>
        </div>
      )}
    </>
  )
}

function Chip({
  active, onClick, label, tone,
}: { active: boolean; onClick: () => void; label: string; tone: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "rounded-full px-4 py-2 text-base font-semibold ring-1 transition",
        active
          ? tone
          : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50"
      )}
    >
      {label}
    </button>
  )
}

function ResultRow({ entry, highlight }: { entry: SearchEntry; highlight: string }) {
  const isExt = entry.external
  const Wrapper: React.ElementType = isExt ? "a" : Link
  const wrapperProps = isExt
    ? { href: entry.href, target: "_blank", rel: "noopener noreferrer" }
    : { href: entry.href }
  return (
    <Wrapper
      {...wrapperProps}
      className="group flex flex-wrap items-start gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50/40"
    >
      <span className={clsx("shrink-0 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ring-1", TYPE_TONE[entry.type])}>
        {entry.type}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-lg font-bold leading-tight text-slate-900 group-hover:text-indigo-800">
          <Highlight text={entry.name} query={highlight} />
        </p>
        <p className="mt-0.5 text-sm text-slate-600">{entry.hint}</p>
        <p className="mt-1 text-sm text-slate-700">{entry.summary}</p>
      </div>
      <span className="shrink-0 self-center text-sm font-semibold text-indigo-600">
        {isExt ? "Open ↗" : "Open →"}
      </span>
    </Wrapper>
  )
}

function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim()
  if (!q) return <>{text}</>
  const idx = text.toUpperCase().indexOf(q.toUpperCase())
  if (idx < 0) return <>{text}</>
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded bg-amber-200 px-0.5 text-slate-900">
        {text.slice(idx, idx + q.length)}
      </mark>
      {text.slice(idx + q.length)}
    </>
  )
}
