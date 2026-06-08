/**
 * /search — name-first inverse lookup.
 *
 * Reporters usually start from a name, not a structural pattern. This page
 * builds a flat searchable index of every named entity FairGuard knows about
 * (lobbyist, firm, client, agency, legislator) at build time, then hands it
 * to a client component that does the fuzzy filtering live.
 */

import findingsData from "../../../public/findings.json"
import trailsData from "../../../public/trails.json"
import pressrelData from "../../../public/press_releases.json"
import commentData from "../../../public/comment_log.json"
import SearchClient, { type SearchEntry } from "./SearchClient"
import { findingSlug } from "../lib/exports"
import type {
  CommentLogPayload,
  Finding,
  FindingsPayload,
  PressrelPayload,
  TrailsPayload,
} from "../types"

export const metadata = {
  title: "Search — FairGuard",
  description:
    "Type a lobbyist, firm, client, agency, or legislator and see everything " +
    "FairGuard has on them in one view.",
}

const slug = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")

function buildIndex(): SearchEntry[] {
  const findings: Finding[] = (findingsData as FindingsPayload).findings ?? []
  const trails = (trailsData as TrailsPayload).trails ?? []
  const reports = (pressrelData as PressrelPayload).reports ?? []
  const comments = (commentData as CommentLogPayload).entries ?? []

  const entries: SearchEntry[] = []
  const seen = new Set<string>()

  const push = (e: SearchEntry) => {
    if (!e.name || typeof e.name !== "string") return
    const k = `${e.type}::${e.name.toUpperCase()}`
    if (seen.has(k)) return
    seen.add(k)
    entries.push(e)
  }

  // Lobbyists + firms from findings (each finding is one lobbyist@agency pair).
  for (const f of findings) {
    push({
      type: "lobbyist",
      name: f.lobbyist_name,
      hint: `${f.registrant_name} → ${f.agency_short.toUpperCase()}`,
      summary: `Rank #${f.rank} · ${Math.round(f.concentration * 100)}% concentration · ${f.n_clients} clients · ${(f.total_income / 1_000_000).toFixed(1)}M income`,
      href: `/findings/${findingSlug(f)}`,
      tags: [f.agency_short, f.registrant_name],
    })
    push({
      type: "firm",
      name: f.registrant_name,
      hint: `Registrant · ${f.agency_short.toUpperCase()}`,
      summary: `Filed for ${f.lobbyist_name} (rank #${f.rank}, ${f.agency_filings} agency-targeting filings)`,
      href: `/findings/${findingSlug(f)}`,
      tags: [f.agency_short, f.lobbyist_name],
    })
    // Top clients from each finding.
    if (f.top_clients_str) {
      for (const c of f.top_clients_str.split("|").map((s) => s.trim()).filter(Boolean)) {
        push({
          type: "client",
          name: c,
          hint: `Lobbying client · ${f.agency_short.toUpperCase()}`,
          summary: `Represented by ${f.registrant_name} (${f.lobbyist_name})`,
          href: `/findings/${findingSlug(f)}`,
          tags: [f.agency_short, f.lobbyist_name, f.registrant_name],
        })
      }
    }
    push({
      type: "agency",
      name: f.agency_short.toUpperCase(),
      hint: "Federal agency",
      summary: "See all findings for this agency",
      href: `/findings?agency=${encodeURIComponent(f.agency_short)}`,
      tags: [],
    })
  }

  // Trail recipients (these are USAspending-verified subsidiaries / spinouts).
  for (const t of trails) {
    for (const c of t.clients) {
      push({
        type: "client",
        name: c.label,
        hint: `Award recipient · ${t.agency}`,
        summary: `$${c.total.toLocaleString()} traced ($${c.discretionary_amount.toLocaleString()} discretionary) — ${c.n_awards} awards`,
        href: `/trails#trail-${slug(t.case_id)}`,
        tags: [t.case_id, t.agency],
      })
    }
  }

  // Pressrel: legislators + per-client mentions.
  for (const r of reports) {
    for (const pc of r.per_client) {
      push({
        type: "client",
        name: pc.client,
        hint: `Press-release client · ${pc.n_matches} mentions`,
        summary: `${pc.n_distinct_members} legislators, ${pc.first_date ?? "?"}–${pc.last_date ?? "?"}`,
        href: `/pressrel#${slug(r.case_id)}`,
        tags: [r.case_id],
      })
    }
    for (const m of r.matches) {
      push({
        type: "legislator",
        name: m.member_name,
        hint: m.party && m.state ? `${m.party}-${m.state} · ${m.chamber ?? ""}`.trim() : "Member of Congress",
        summary: `Mentioned "${m.client ?? "—"}" on ${m.date}`,
        href: m.url,
        external: true,
        tags: [m.client ?? "", r.case_id],
      })
    }
  }

  // Comment-tracker firms (some are not in scan findings yet).
  for (const e of comments) {
    push({
      type: "firm",
      name: e.firm,
      hint: `Comment request · ${e.status_label}`,
      summary: e.case,
      href: `/comments#${e.key}`,
      tags: [e.case],
    })
  }

  // Sort: most actionable types first (findings/lobbyists), then alpha.
  const order: Record<SearchEntry["type"], number> = {
    lobbyist: 0, firm: 1, agency: 2, client: 3, legislator: 4,
  }
  entries.sort((a, b) => {
    const t = order[a.type] - order[b.type]
    if (t !== 0) return t
    return a.name.localeCompare(b.name)
  })
  return entries
}

export default function Page() {
  const entries = buildIndex()
  const counts = entries.reduce<Record<string, number>>((acc, e) => {
    acc[e.type] = (acc[e.type] ?? 0) + 1
    return acc
  }, {})
  return (
    <div>
      <section className="mb-8">
        <h1 className="mb-3">Look up a name</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          Already working a story? Type a lobbyist, firm, client, agency, or legislator
          and see everything FairGuard has on them. Results link directly to the relevant
          finding, money trail, press release, or comment request.
        </p>
        <p className="mt-3 text-base text-slate-600">
          Index built from <strong>{entries.length.toLocaleString()}</strong> named
          entities across all four data sources.
        </p>
      </section>
      <SearchClient entries={entries} counts={counts} />
    </div>
  )
}
