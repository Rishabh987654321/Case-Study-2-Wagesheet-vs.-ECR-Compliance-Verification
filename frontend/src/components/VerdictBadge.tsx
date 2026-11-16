import type { Verdict } from "../api/types"

const STYLES: Record<Verdict, string> = {
  MATCHED: "bg-green-100 text-green-800 border-green-300",
  NAME_MISMATCH: "bg-orange-100 text-orange-800 border-orange-300",
  AMOUNT_MISMATCH: "bg-yellow-100 text-yellow-800 border-yellow-300",
  MISSING: "bg-red-100 text-red-800 border-red-300",
  PARSE_ERROR: "bg-gray-200 text-gray-800 border-gray-400",
}

const LABELS: Record<Verdict, string> = {
  MATCHED: "Matched",
  NAME_MISMATCH: "Name Mismatch",
  AMOUNT_MISMATCH: "Amount Mismatch",
  MISSING: "Missing",
  PARSE_ERROR: "Parse Error",
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[verdict]}`}
    >
      {LABELS[verdict]}
    </span>
  )
}
