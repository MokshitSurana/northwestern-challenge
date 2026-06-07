export interface TrailClient {
  label: string
  total: number
  n_awards: number
  routine_amount: number
  discretionary_amount: number
  recipients: string[]
}

export interface TrailMatch {
  lobbyist_name: string
  agency_short: string
}

export interface Trail {
  case_id: string
  lobbyist_label: string
  agency: string
  award_groups: string[]
  time_period?: { start?: string; end?: string }
  match?: TrailMatch[]
  generated_at: string
  total: number
  routine_total: number
  discretionary_total: number
  n_clients_with_awards: number
  n_clients_total: number
  clients: TrailClient[]
  misses: string[]
}

export interface Finding {
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
  sample_uuid: string | null
  sample_source: string
  senate_lda_url: string | null
  verification_status?: "verified" | "partial" | "unverified" | null
  trail?: Trail
}

export interface FindingsPayload {
  generated_at: string
  total_candidates: number
  findings: Finding[]
}

export interface TrailsPayload {
  generated_at: string
  total_trails: number
  trails: Trail[]
}

// ── Press releases (separate /pressrel feed) ───────────────────────────────────

export interface PressrelMatch {
  client?: string
  date: string
  bioguide_id?: string
  member_name: string
  party?: string
  state?: string
  chamber?: string
  title: string
  url: string
  snippet?: string
}

export interface PressrelPerClient {
  client: string
  aliases?: string[]
  n_matches: number
  n_distinct_members: number
  first_date: string | null
  last_date: string | null
}

export interface PressrelReport {
  case_id: string
  label: string
  generated_at: string
  filters?: Record<string, string | null>
  match?: { lobbyist_name: string; agency_short: string }[]
  n_clients: number
  n_matches: number
  n_distinct_members: number
  per_client: PressrelPerClient[]
  matches: PressrelMatch[]
}

export interface PressrelPayload {
  generated_at: string
  total_reports: number
  reports: PressrelReport[]
}

// ── COI graph (composes scan + trace + pressrel) ───────────────────────────────

export interface CoiNode {
  id: string
  // Backed by the script's `NODE_COLORS` keys but typed widely so the JSON
  // import (which loses the literal narrowing) round-trips cleanly:
  type: string
  label: string
  x: number
  y: number
  color: string
  radius: number
  // The JSON serializer writes null for unset optionals; accept both shapes.
  rank?: number | null
  score?: number | null
  concentration?: number | null
  prior_role?: string | null
  party?: string | null
  state?: string | null
  chamber?: string | null
}

export interface CoiLink {
  source: string | CoiNode
  target: string | CoiNode
  type: string
  types?: string[]
  weight: number
  weights?: Partial<Record<string, number>>
  color: string
  width: number
  dash?: string | null
  latest_title?: string | null
  latest_url?: string | null
  latest_date?: string | null
}

export interface CoiTriangle {
  legislator: string
  client: string
  agency: string
  lobbyists: string[]
  n_mentions: number
  agency_to_client_dollars: number
}

export interface CoiHub {
  client: string
  dollars: number
  n_mentions: number
  agencies: string[]
  score: number
}

export interface CoiBridge {
  client: string
  n_lobbyists: number
  lobbyists: string[]
}

export interface CoiGraphPayload {
  generated_at: string
  n_findings_included: number
  stats: {
    n_nodes: number
    n_edges: number
    nodes_by_type: Record<string, number>
    edges_by_type: Record<string, number>
  }
  bridges: CoiBridge[]
  triangles: CoiTriangle[]
  hubs: CoiHub[]
  legend: { type: string; color: string }[]
  nodes: CoiNode[]
  links: CoiLink[]
}
