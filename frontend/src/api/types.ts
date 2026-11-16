export type Verdict = "MATCHED" | "NAME_MISMATCH" | "AMOUNT_MISMATCH" | "MISSING" | "PARSE_ERROR"

export type VerificationStatus = "uploading" | "processing" | "completed" | "failed"

export interface VerdictCounts {
  matched: number
  name_mismatch: number
  amount_mismatch: number
  missing: number
  parse_error: number
}

export interface VerificationSummary {
  pf: VerdictCounts
  esic: VerdictCounts
}

export interface Verification {
  id: string
  name: string | null
  status: VerificationStatus
  wagesheet_filename: string | null
  pf_ecr_filename: string | null
  esic_ecr_filename: string | null
  employee_count: number
  summary: VerificationSummary
  parse_warnings: string[]
  created_at: string
  completed_at: string | null
  error_message: string | null
}

export interface VerificationListItem {
  id: string
  name: string | null
  status: VerificationStatus
  employee_count: number
  created_at: string
}

export interface PFResult {
  ws_amount: number | null
  ecr_name: string | null
  ecr_amount: number | null
  amount_diff: number | null
  name_score: number | null
  verdict: Verdict
  reason: string
}

export interface ESICResult {
  ws_amount: number | null
  ecr_name: string | null
  ecr_amount: number | null
  amount_diff: number | null
  name_score: number | null
  verdict: Verdict
  reason: string
}

export interface EmployeeRecord {
  id: string
  row_number: number
  name: string
  uan: string | null
  ip_number: string | null
  agency: string | null
  state: string | null
  pf: PFResult
  esic: ESICResult
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface UnmatchedPFRecord {
  uan: string
  name: string
  ee_share: number
}

export interface UnmatchedESICRecord {
  ip_number: string
  name: string
  ip_contribution: number
}

export interface UnmatchedResponse {
  pf_unmatched: UnmatchedPFRecord[]
  esic_unmatched: UnmatchedESICRecord[]
}

export interface ConfigResponse {
  max_file_mb: number
  name_match_threshold: number
  name_review_threshold: number
  amount_tolerance: number
}

export interface ApiErrorResponse {
  error: string
  detail: string
}
