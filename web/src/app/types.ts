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
