import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Fragment, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import type { Verdict } from "../api/types"
import { deleteVerification, getEmployees, getExportUrl, getVerification } from "../api/verification"
import { SummaryCard } from "../components/SummaryCard"
import { useToast } from "../components/ToastProvider"
import { VerdictBadge } from "../components/VerdictBadge"

const VERDICT_OPTIONS: Array<{ value: Verdict | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "MATCHED", label: "Matched" },
  { value: "NAME_MISMATCH", label: "Name Mismatch" },
  { value: "AMOUNT_MISMATCH", label: "Amount Mismatch" },
  { value: "MISSING", label: "Missing" },
]

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  processing: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  uploading: "bg-gray-100 text-gray-800",
}

function formatAmount(value: number | null): string {
  if (value === null) return "—"
  return `₹${value.toFixed(2)}`
}

function formatScore(value: number | null): string {
  if (value === null) return "—"
  return `${value.toFixed(1)}%`
}

const PAGE_SIZE = 50
const MISMATCH_ONLY_PAGE_SIZE = 500

export function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const [pfVerdict, setPfVerdict] = useState<Verdict | "">("")
  const [esicVerdict, setEsicVerdict] = useState<Verdict | "">("")
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [mismatchesOnly, setMismatchesOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [pfVerdict, esicVerdict, search, mismatchesOnly])

  const verificationQuery = useQuery({
    queryKey: ["verification", id],
    queryFn: () => getVerification(id!),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === "processing" ? 2000 : false),
  })

  const verification = verificationQuery.data
  const isCompleted = verification?.status === "completed"

  const employeesQuery = useQuery({
    queryKey: ["employees", id, pfVerdict, esicVerdict, search, mismatchesOnly, page],
    queryFn: () =>
      getEmployees(id!, {
        pf_verdict: pfVerdict || undefined,
        esic_verdict: esicVerdict || undefined,
        q: search || undefined,
        page: mismatchesOnly ? 1 : page,
        page_size: mismatchesOnly ? MISMATCH_ONLY_PAGE_SIZE : PAGE_SIZE,
      }),
    enabled: !!id && isCompleted,
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteVerification(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["verifications"] })
      showToast("Verification deleted", "success")
      navigate("/history")
    },
    onError: () => showToast("Failed to delete verification", "error"),
  })

  if (verificationQuery.isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700">Cannot connect to server</p>
        <button
          type="button"
          onClick={() => verificationQuery.refetch()}
          className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!verification) {
    return <p className="text-gray-500">Loading…</p>
  }

  const allItems = employeesQuery.data?.items ?? []
  const displayedItems = mismatchesOnly
    ? allItems.filter((e) => !(e.pf.verdict === "MATCHED" && e.esic.verdict === "MATCHED"))
    : allItems
  const total = mismatchesOnly ? displayedItems.length : (employeesQuery.data?.total ?? 0)
  const pages = mismatchesOnly ? 1 : (employeesQuery.data?.pages ?? 1)

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-gray-900">
              {verification.name || `Verification ${verification.id.slice(0, 8)}`}
            </h2>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                STATUS_STYLES[verification.status] ?? "bg-gray-100 text-gray-800"
              }`}
            >
              {verification.status}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {[verification.wagesheet_filename, verification.pf_ecr_filename, verification.esic_ecr_filename]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <p className="text-sm text-gray-500">
            Created {new Date(verification.created_at).toLocaleString()}
            {verification.completed_at &&
              ` · Completed ${new Date(verification.completed_at).toLocaleString()}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <a
              href={getExportUrl(verification.id)}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
            >
              Download Report (.xlsx)
            </a>
          ) : (
            <span
              title="Download will be available when verification completes"
              className="cursor-not-allowed rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-400"
            >
              Download Report (.xlsx)
            </span>
          )}
          {confirmDelete ? (
            <span className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="rounded-md bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-700"
              >
                Confirm delete
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {verification.status === "processing" && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-800">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
          Parsing documents and matching employees…
        </div>
      )}

      {verification.status === "failed" && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          Verification failed: {verification.error_message || "Unknown error"}
        </div>
      )}

      {isCompleted && (
        <>
          <div className="mb-6 flex flex-col gap-4 sm:flex-row">
            <SummaryCard title="PF Verification" counts={verification.summary.pf} />
            <SummaryCard title="ESIC Verification" counts={verification.summary.esic} />
          </div>

          {verification.parse_warnings.length > 0 && (
            <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
              <p className="mb-1 font-medium">Parse warnings:</p>
              <ul className="list-inside list-disc">
                {verification.parse_warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <select
              value={pfVerdict}
              onChange={(e) => setPfVerdict(e.target.value as Verdict | "")}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            >
              {VERDICT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  PF: {o.label}
                </option>
              ))}
            </select>
            <select
              value={esicVerdict}
              onChange={(e) => setEsicVerdict(e.target.value as Verdict | "")}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            >
              {VERDICT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  ESIC: {o.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Search by name, UAN, or IP Number"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="min-w-[240px] flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={mismatchesOnly}
                onChange={(e) => setMismatchesOnly(e.target.checked)}
              />
              Show only mismatches
            </label>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-600">
                <tr>
                  <th className="px-3 py-2 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Name</th>
                  <th className="px-3 py-2 font-medium">UAN</th>
                  <th className="px-3 py-2 font-medium">IP Number</th>
                  <th className="px-3 py-2 font-medium">PF Verdict</th>
                  <th className="px-3 py-2 font-medium">PF Reason</th>
                  <th className="px-3 py-2 font-medium">ESIC Verdict</th>
                  <th className="px-3 py-2 font-medium">ESIC Reason</th>
                </tr>
              </thead>
              <tbody>
                {displayedItems.map((emp) => (
                  <Fragment key={emp.id}>
                    <tr
                      onClick={() => setExpandedId(expandedId === emp.id ? null : emp.id)}
                      className="cursor-pointer border-t border-gray-100 hover:bg-gray-50"
                    >
                      <td className="px-3 py-2 text-gray-500">{emp.row_number}</td>
                      <td className="px-3 py-2 font-medium text-gray-900">{emp.name}</td>
                      <td className="px-3 py-2 text-gray-600">{emp.uan || "—"}</td>
                      <td className="px-3 py-2 text-gray-600">{emp.ip_number || "—"}</td>
                      <td className="px-3 py-2">
                        <VerdictBadge verdict={emp.pf.verdict} />
                      </td>
                      <td className="max-w-xs truncate px-3 py-2 text-gray-600">{emp.pf.reason}</td>
                      <td className="px-3 py-2">
                        <VerdictBadge verdict={emp.esic.verdict} />
                      </td>
                      <td className="max-w-xs truncate px-3 py-2 text-gray-600">{emp.esic.reason}</td>
                    </tr>
                    {expandedId === emp.id && (
                      <tr className="border-t border-gray-100 bg-gray-50">
                        <td colSpan={8} className="px-4 py-4">
                          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <div>
                              <p className="mb-1 text-xs font-semibold uppercase text-gray-500">
                                Wagesheet
                              </p>
                              <p className="text-sm text-gray-900">{emp.name}</p>
                              <p className="text-sm text-gray-600">PF: {formatAmount(emp.pf.ws_amount)}</p>
                              <p className="text-sm text-gray-600">
                                ESIC: {formatAmount(emp.esic.ws_amount)}
                              </p>
                            </div>
                            <div>
                              <p className="mb-1 text-xs font-semibold uppercase text-gray-500">PF ECR</p>
                              <p className="text-sm text-gray-900">{emp.pf.ecr_name || "—"}</p>
                              <p className="text-sm text-gray-600">
                                Name score: {formatScore(emp.pf.name_score)}
                              </p>
                              <p className="text-sm text-gray-600">
                                Amount: {formatAmount(emp.pf.ecr_amount)} (diff:{" "}
                                {formatAmount(emp.pf.amount_diff)})
                              </p>
                            </div>
                            <div>
                              <p className="mb-1 text-xs font-semibold uppercase text-gray-500">
                                ESIC ECR
                              </p>
                              <p className="text-sm text-gray-900">{emp.esic.ecr_name || "—"}</p>
                              <p className="text-sm text-gray-600">
                                Name score: {formatScore(emp.esic.name_score)}
                              </p>
                              <p className="text-sm text-gray-600">
                                Amount: {formatAmount(emp.esic.ecr_amount)} (diff:{" "}
                                {formatAmount(emp.esic.amount_diff)})
                              </p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
                {displayedItems.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-3 py-8 text-center text-gray-400">
                      No matching employees.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {!mismatchesOnly && pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <span>
                Page {page} of {pages} ({total} total)
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="rounded-md border border-gray-300 px-3 py-1 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={page >= pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded-md border border-gray-300 px-3 py-1 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
