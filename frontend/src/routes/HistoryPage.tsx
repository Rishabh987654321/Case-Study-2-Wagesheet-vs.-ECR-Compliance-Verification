import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Link } from "react-router-dom"
import { deleteVerification, listVerifications } from "../api/verification"
import { useToast } from "../components/ToastProvider"

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  processing: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  uploading: "bg-gray-100 text-gray-800",
}

export function HistoryPage() {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)

  const query = useQuery({
    queryKey: ["verifications"],
    queryFn: () => listVerifications(1, 50),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteVerification,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["verifications"] })
      showToast("Verification deleted", "success")
    },
    onError: () => showToast("Failed to delete verification", "error"),
    onSettled: () => setPendingDeleteId(null),
  })

  if (query.isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700">Cannot connect to server</p>
        <button
          type="button"
          onClick={() => query.refetch()}
          className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (query.isLoading) {
    return <p className="text-gray-500">Loading…</p>
  }

  const items = query.data?.items ?? []

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
        No verifications yet.{" "}
        <Link to="/upload" className="text-blue-600 underline">
          Start one
        </Link>
        .
      </div>
    )
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Verification History</h2>
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-600">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Employees</th>
              <th className="px-4 py-2 font-medium">Created</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {items.map((v) => (
              <tr key={v.id} className="border-t border-gray-100">
                <td className="px-4 py-2">
                  <Link to={`/verify/${v.id}`} className="font-medium text-blue-600 hover:underline">
                    {v.name || v.id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      STATUS_STYLES[v.status] ?? "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {v.status}
                  </span>
                </td>
                <td className="px-4 py-2">{v.employee_count}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(v.created_at).toLocaleString()}</td>
                <td className="px-4 py-2 text-right">
                  {pendingDeleteId === v.id ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="text-xs text-gray-500">Delete?</span>
                      <button
                        type="button"
                        onClick={() => deleteMutation.mutate(v.id)}
                        disabled={deleteMutation.isPending}
                        className="rounded-md bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700"
                      >
                        Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() => setPendingDeleteId(null)}
                        className="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setPendingDeleteId(v.id)}
                      className="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
