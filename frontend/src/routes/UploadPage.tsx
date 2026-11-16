import { useMutation, useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ApiError } from "../api/client"
import { getConfig, uploadAndVerify } from "../api/verification"
import { DropZone } from "../components/DropZone"
import { useToast } from "../components/ToastProvider"

type FileKind = "wagesheet" | "pf_ecr" | "esic_ecr"

const ACCEPT: Record<FileKind, string> = {
  wagesheet: ".xlsx,.xls",
  pf_ecr: ".pdf",
  esic_ecr: ".pdf",
}

const ALLOWED_EXTENSIONS: Record<FileKind, string[]> = {
  wagesheet: [".xlsx", ".xls"],
  pf_ecr: [".pdf"],
  esic_ecr: [".pdf"],
}

const LABELS: Record<FileKind, string> = {
  wagesheet: "Vendor Wagesheet (.xlsx)",
  pf_ecr: "PF ECR (.pdf)",
  esic_ecr: "ESIC ECR (.pdf)",
}

function getExtension(filename: string): string {
  const idx = filename.lastIndexOf(".")
  return idx === -1 ? "" : filename.slice(idx).toLowerCase()
}

export function UploadPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [files, setFiles] = useState<Record<FileKind, File | null>>({
    wagesheet: null,
    pf_ecr: null,
    esic_ecr: null,
  })
  const [fieldErrors, setFieldErrors] = useState<Record<FileKind, string | null>>({
    wagesheet: null,
    pf_ecr: null,
    esic_ecr: null,
  })
  const [name, setName] = useState("")
  const [progress, setProgress] = useState(0)

  const configQuery = useQuery({
    queryKey: ["config"],
    queryFn: getConfig,
  })

  const mutation = useMutation({
    mutationFn: () =>
      uploadAndVerify(files.wagesheet!, files.pf_ecr!, files.esic_ecr!, name || undefined, setProgress),
    onSuccess: (data) => {
      navigate(`/verify/${data.verification_id}`)
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Upload failed. Please try again."
      showToast(message, "error")
    },
  })

  function handleFileSelected(kind: FileKind, file: File) {
    const ext = getExtension(file.name)
    if (!ALLOWED_EXTENSIONS[kind].includes(ext)) {
      setFieldErrors((prev) => ({
        ...prev,
        [kind]: `Please upload a file of type: ${ALLOWED_EXTENSIONS[kind].join(", ")}`,
      }))
      return
    }
    const maxBytes = (configQuery.data?.max_file_mb ?? 50) * 1024 * 1024
    if (file.size > maxBytes) {
      setFieldErrors((prev) => ({
        ...prev,
        [kind]: `File exceeds max size of ${configQuery.data?.max_file_mb ?? 50} MB`,
      }))
      return
    }
    setFieldErrors((prev) => ({ ...prev, [kind]: null }))
    setFiles((prev) => ({ ...prev, [kind]: file }))
  }

  const allSelected = files.wagesheet && files.pf_ecr && files.esic_ecr
  const hasErrors = Object.values(fieldErrors).some(Boolean)
  const canSubmit = allSelected && !hasErrors && !mutation.isPending

  if (configQuery.isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700">Cannot connect to server</p>
        <button
          type="button"
          onClick={() => configQuery.refetch()}
          className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="mb-6 text-xl font-semibold text-gray-900">Start a new verification</h2>

      <div className="space-y-4">
        {(["wagesheet", "pf_ecr", "esic_ecr"] as FileKind[]).map((kind) => (
          <DropZone
            key={kind}
            label={LABELS[kind]}
            accept={ACCEPT[kind]}
            file={files[kind]}
            error={fieldErrors[kind]}
            onFileSelected={(file) => handleFileSelected(kind, file)}
          />
        ))}
      </div>

      <div className="mt-6">
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="verification-name">
          Verification name (optional)
        </label>
        <input
          id="verification-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., October 2026"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:outline-none"
        />
      </div>

      {mutation.isPending && (
        <div className="mt-4">
          <div className="h-2 w-full rounded bg-gray-100">
            <div
              className="h-2 rounded bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1 text-sm text-gray-500">Uploading… {progress}%</p>
        </div>
      )}

      {mutation.isError && (
        <div className="mt-4 flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-2">
          <span className="text-sm text-red-700">
            {mutation.error instanceof ApiError ? mutation.error.message : "Upload failed."}
          </span>
          <button
            type="button"
            onClick={() => mutation.mutate()}
            className="rounded-md bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={() => mutation.mutate()}
        className="mt-6 w-full rounded-md bg-gray-900 px-4 py-2.5 font-medium text-white disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {mutation.isPending ? "Starting verification…" : "Start Verification"}
      </button>
    </div>
  )
}
