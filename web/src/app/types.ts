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
}

export interface FindingsPayload {
  generated_at: string
  total_candidates: number
  findings: Finding[]
}
