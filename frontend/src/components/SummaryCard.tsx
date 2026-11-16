import type { VerdictCounts } from "../api/types"

const ROWS: Array<{ key: keyof VerdictCounts; label: string; dot: string; bar: string }> = [
  { key: "matched", label: "Matched", dot: "bg-green-500", bar: "bg-green-500" },
  { key: "name_mismatch", label: "Name Mismatch", dot: "bg-orange-500", bar: "bg-orange-500" },
  { key: "amount_mismatch", label: "Amount Mismatch", dot: "bg-yellow-500", bar: "bg-yellow-500" },
  { key: "missing", label: "Missing", dot: "bg-red-500", bar: "bg-red-500" },
]

export function SummaryCard({ title, counts }: { title: string; counts: VerdictCounts }) {
  const total =
    counts.matched + counts.name_mismatch + counts.amount_mismatch + counts.missing + counts.parse_error

  return (
    <div className="flex-1 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 font-semibold text-gray-900">{title}</h3>
      <div className="space-y-2">
        {ROWS.map(({ key, label, dot, bar }) => {
          const value = counts[key]
          const pct = total ? (value / total) * 100 : 0
          return (
            <div key={key} className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dot}`} />
              <span className="w-32 shrink-0 text-sm text-gray-700">{label}</span>
              <div className="h-2 flex-1 rounded bg-gray-100">
                <div className={`h-2 rounded ${bar}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="w-8 shrink-0 text-right text-sm font-medium text-gray-900">{value}</span>
            </div>
          )
        })}
        {counts.parse_error > 0 && (
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-gray-400" />
            <span className="w-32 shrink-0 text-sm text-gray-700">Parse Error</span>
            <div className="h-2 flex-1 rounded bg-gray-100">
              <div
                className="h-2 rounded bg-gray-400"
                style={{ width: `${total ? (counts.parse_error / total) * 100 : 0}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right text-sm font-medium text-gray-900">
              {counts.parse_error}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
