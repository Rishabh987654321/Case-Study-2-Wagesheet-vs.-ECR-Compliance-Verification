import { useRef, useState, type DragEvent } from "react"

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DropZone({
  label,
  accept,
  file,
  error,
  onFileSelected,
}: {
  label: string
  accept: string
  file: File | null
  error: string | null
  onFileSelected: (file: File) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) onFileSelected(dropped)
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
          error
            ? "border-red-400 bg-red-50"
            : isDragOver
              ? "border-blue-400 bg-blue-50"
              : file
                ? "border-green-400 bg-green-50"
                : "border-gray-300 bg-white hover:border-gray-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0]
            if (selected) onFileSelected(selected)
          }}
        />
        {file ? (
          <div className="flex items-center gap-2 text-sm text-gray-800">
            <span aria-hidden>✅</span>
            <span className="font-medium">{file.name}</span>
            <span className="text-gray-500">({formatSize(file.size)})</span>
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            <div className="mb-1 text-2xl" aria-hidden>
              📄
            </div>
            Drop file here or click to browse
          </div>
        )}
        {file && <p className="mt-1 text-xs text-gray-400">Click or drop to replace</p>}
      </div>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  )
}
