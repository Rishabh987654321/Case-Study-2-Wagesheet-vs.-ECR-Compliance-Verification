import { apiClient } from "./client"
import type {
  ConfigResponse,
  EmployeeRecord,
  PaginatedResponse,
  UnmatchedResponse,
  Verification,
  VerificationListItem,
} from "./types"

export interface UploadAndVerifyResult {
  verification_id: string
  status: string
  message: string
}

export async function uploadAndVerify(
  wagesheet: File,
  pfEcr: File,
  esicEcr: File,
  name?: string,
  onProgress?: (percent: number) => void,
): Promise<UploadAndVerifyResult> {
  const formData = new FormData()
  formData.append("wagesheet", wagesheet)
  formData.append("pf_ecr", pfEcr)
  formData.append("esic_ecr", esicEcr)
  if (name) formData.append("name", name)

  const { data } = await apiClient.post<UploadAndVerifyResult>("/verify", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    },
  })
  return data
}

export async function getVerification(id: string): Promise<Verification> {
  const { data } = await apiClient.get<Verification>(`/verify/${id}`)
  return data
}

export interface GetEmployeesParams {
  pf_verdict?: string
  esic_verdict?: string
  q?: string
  page?: number
  page_size?: number
}

export async function getEmployees(
  id: string,
  params: GetEmployeesParams = {},
): Promise<PaginatedResponse<EmployeeRecord>> {
  const { data } = await apiClient.get<PaginatedResponse<EmployeeRecord>>(`/verify/${id}/employees`, {
    params,
  })
  return data
}

export function getExportUrl(id: string, format: "xlsx" | "csv" = "xlsx"): string {
  return `/api/verify/${id}/export?format=${format}`
}

export async function getUnmatched(id: string): Promise<UnmatchedResponse> {
  const { data } = await apiClient.get<UnmatchedResponse>(`/verify/${id}/unmatched`)
  return data
}

export async function listVerifications(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<VerificationListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<VerificationListItem>>("/verifications", {
    params: { page, page_size: pageSize },
  })
  return data
}

export async function deleteVerification(id: string): Promise<void> {
  await apiClient.delete(`/verify/${id}`)
}

export async function getConfig(): Promise<ConfigResponse> {
  const { data } = await apiClient.get<ConfigResponse>("/config")
  return data
}
