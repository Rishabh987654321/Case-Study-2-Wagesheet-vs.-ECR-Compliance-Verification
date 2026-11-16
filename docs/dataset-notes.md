# Dataset Notes — Phase 0 Findings

Findings from inspecting `sample_data/input/` with `scripts/spike.py`. These drive the
Phase 1 parser design. Everything here is from the one sample set — parsers must not
hard-code assumptions that only hold for this file (see "Risks for unseen data" below).

## 1. Wagesheet (`Sample_Wagesheet_Aug25.xlsx`)

- Single sheet (`Sheet1`), no merged cells, no blank rows, no extra header rows.
- Header is row 1, exact columns: `Name, UAN, IP Number, Agency, State, ESIC @ 0.75%, PF @ 12%`.
- 12 employee rows (rows 2–13).
- UAN stored as **text**, 12 digits, e.g. `999912340001`.
- IP Number stored as **text**, 10 digits, e.g. `9912340001`.
- ESIC/PF amount columns stored as **numbers** (`int` in the sample, but treat as float).
- No quirks: no formulas, no hidden rows, no multi-row headers in this sample.

**Parser implication:** auto-detect header row by scanning for a row containing both
"UAN" and "Name" (don't assume row 1) — real vendor files may add title rows above the
header. Cast UAN/IP Number to string and strip whitespace regardless of underlying
Excel type (could be numeric in other files, which drops leading formatting / causes
float display like `999912340001.0`).

## 2. PF ECR PDF (`PF ECR AUG-25 SAMPLE.pdf`)

- 1 page, 11 member rows. Header says "Total Members 11" — matches row count, useful
  sanity check.
- **No ruled table lines** — `page.extract_tables()` returns zero tables.
  `page.extract_text()` and line-based regex parsing is required, not `extract_table`.
- Column layout per member line (space-separated, no delimiters):
  `Sl.No | UAN | Name as per ECR | Name as per UAN Repository | Gross Wages | EPF Wages | EPS Wages | EDLI Wages | EE share | EPS share | ER share | NCP Days`
- **The name appears twice back-to-back with no separator** ("Name as per ECR" and
  "Name as per UAN Repository"). In this sample the two are always identical, so the
  split can be detected by finding an exact repeated token subsequence
  (`tokens[:k] == tokens[k:2k]`). This is the field we use for fuzzy matching (EE share
  is the employee's PF contribution — matches wagesheet "PF @ 12%").
- Footer lines ("Total Members", "Contribution and Remittance Details", establishment
  metadata) do not match the member-row regex and are naturally skipped.
- UAN format matches wagesheet exactly (12-digit string) — no normalization needed
  beyond strip/zero-pad safety.

**Parsing challenge:** if a real ECR has "Name as per ECR" genuinely different from
"Name as per UAN Repository" (this is exactly the kind of discrepancy ECRs are meant to
expose), the exact-repeat heuristic fails and we fall back to an even token split, which
can misalign if the two names have different word counts. `spike.py` flags this case as
a warning (`clean_split=False`) rather than silently producing a garbled name — Phase 1
parser must propagate this as a `parse_warning` on the affected row rather than guessing
silently (per "honest over pretty").

## 3. ESIC ECR PDF (`ESIC ECR AUG-25 SAMPLE.pdf`)

- 1 page, 10 insured-person rows (wagesheet has 12 — 2 are absent from this ECR entirely).
- No ruled table lines either — same text + regex approach as PF ECR.
- Column layout: `SNo | Is Disable | IP Number | IP Name | No. Of Days | Total Wages | IP Contribution | Reason`
  (`Is Disable` and `Reason` are literal `-` placeholders in the sample; not used for matching).
- Only **one** name field here (unlike PF ECR's duplicated name) — simpler to parse.
- IP Number format matches wagesheet exactly (10-digit string).
- `IP Contribution` is the employee's ESIC share — matches wagesheet "ESIC @ 0.75%".

## 4. Deliberate test cases baked into the sample data

The sample set is clearly constructed to exercise every verdict type:

| Employee | UAN/IP | Case |
|---|---|---|
| DINESH PRASAD (wagesheet) vs DEVENDRA PRASAD (PF ECR) | 999912340007 | PF **NAME_MISMATCH** — token_sort_ratio = 64.3 (below review floor of 70) |
| REKHA SHARMA (wagesheet) vs RENU SHARMA (ESIC ECR) | 9912340008 | ESIC **NAME_MISMATCH** — token_sort_ratio = 78.3 (in 70–89 review band) |
| VIKRAM THAKUR | 999912340011 | PF **AMOUNT_MISMATCH** — wagesheet ₹1654 vs ECR EE share ₹1354 |
| NEHA MISHRA | 9912340012 | ESIC **AMOUNT_MISMATCH** — wagesheet ₹86 vs ECR IP contribution ₹66 |
| SANJAY PASWAN | 999912340009 / 9912340009 | **MISSING** from both PF ECR and ESIC ECR |
| POOJA GUPTA | 9912340010 | ESIC **MISSING** only (present in PF ECR) |

This confirms the default thresholds (`NAME_MATCH_THRESHOLD=90`, `NAME_REVIEW_THRESHOLD=70`)
correctly separate the two injected name-mismatch cases without needing adjustment.

## 5. Spike results (full run in `scripts/spike.py`)

```
Found 11/12 in PF ECR, 10/12 in ESIC ECR
Name differences found:
  [PF] wagesheet='DINESH PRASAD' vs ecr='DEVENDRA PRASAD' (id=999912340007)
  [ESIC] wagesheet='REKHA SHARMA' vs ecr='RENU SHARMA' (id=9912340008)
Missing from PF ECR: SANJAY PASWAN (UAN 999912340009)
Missing from ESIC ECR: SANJAY PASWAN (IP 9912340009), POOJA GUPTA (IP 9912340010)
Amount mismatches: PF VIKRAM THAKUR (1654 vs 1354), ESIC NEHA MISHRA (86 vs 66)
```
All match the manual PDF read exactly — no parser warnings triggered on this sample.

## 6. Risks when parsing unseen/real data (hundreds of pages)

- **No ruled tables is assumed, not guaranteed.** A different EPFO/ESIC export (or a
  scanned/re-printed PDF) might render actual grid lines, in which case
  `extract_tables()` would work and should be preferred when available. Phase 1 parser
  should try `extract_tables()` first and fall back to the regex/line approach — don't
  assume text-only layout universally.
- **Multi-page tables:** this sample is single-page so we haven't observed repeated
  headers across pages. Real files will have header text (e.g. "Member Details",
  column header row) reprinted per page — the line regex already skips non-matching
  lines, so repeated headers are naturally ignored, but this is unverified at scale.
- **Name field word-count mismatch** (see PF ECR section) — needs explicit
  parse-warning handling, not silent guessing.
- **Numeric formatting:** sample uses comma thousands separators (`13,520`) and no
  decimals for PF, but ESIC uses `.00` decimals (`13520.00`). Both are handled by the
  current regexes (`[\d,]+` vs `[\d,.]+`) but a real file mixing styles or using Cr/DR
  markers, negative adjustments, or `NIL` placeholders would need extra handling.
- **UAN/IP leading zeros or alphanumeric establishment-coded formats** — not present in
  sample (all 12 wagesheet). Normalize by stripping whitespace, keep as string (never
  cast to int) to avoid leading-zero loss.

## 7. Column mapping summary (for Phase 1 parsers)

| Concept | Wagesheet column | PF ECR field | ESIC ECR field |
|---|---|---|---|
| Identifier | UAN | UAN | IP Number |
| Name | Name | Name as per ECR (first of duplicated pair) | IP Name |
| Employee contribution amount | PF @ 12% | EE share | IP Contribution |
