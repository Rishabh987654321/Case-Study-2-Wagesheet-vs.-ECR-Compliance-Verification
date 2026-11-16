# Architecture — Wagesheet vs ECR Compliance Verification

## Goal
Upload three documents (wagesheet Excel + PF ECR PDF + ESIC ECR PDF), automatically cross-match every employee across all three, and produce a downloadable verification report showing per-employee status with reasons.

## Principles
1. **Correct matching over speed** — a false "Matched" is worse than a conservative "Name mismatch"
2. **Scale to hundreds of pages** — the sample is small; real ECRs have hundreds of employees
3. **Configurable thresholds** — name similarity cutoffs are tunable via config, not buried in code
4. **Transparent verdicts** — every verdict includes the raw values from both sides so a human can verify

## System Flow

```
User uploads 3 files (wagesheet.xlsx, pf_ecr.pdf, esic_ecr.pdf)
        │
        ▼
   ┌─────────┐
   │  Parse   │  ← Three parallel parsers
   └────┬────┘
        │
   ┌────▼──────────────┐
   │  Normalize & Link │  ← Clean names, match by identifier
   └────┬──────────────┘
        │
   ┌────▼──────┐
   │  Verify   │  ← Name match? Amount match? → Verdict
   └────┬──────┘
        │
   ┌────▼──────┐
   │  Report   │  ← Excel with per-employee rows + summary sheet
   └───────────┘
```

## Parsing Pipeline

### 1. Wagesheet Parser (Excel)
- Read with openpyxl
- Auto-detect header row (find row containing "UAN" or "Name")
- Extract: Name, UAN, IP Number, Agency, State, ESIC amount, PF amount
- Normalize UAN (strip spaces, ensure numeric), IP Number (strip spaces)
- Handle merged cells, skip empty rows

### 2. PF ECR Parser (PDF)
- Extract tables with pdfplumber
- Identify columns: UAN, Member Name, EE Share (employee's PF contribution)
- Handle multi-page tables (headers repeat per page)
- Skip summary/footer rows
- Normalize UAN to match wagesheet format

### 3. ESIC ECR Parser (PDF)
- Extract tables with pdfplumber
- Identify columns: IP Number, Insured Person Name, IP Contribution (employee's ESIC)
- Handle multi-page tables
- Skip summary/footer rows
- Normalize IP Number to match wagesheet format

## Matching Engine

### Identifier Matching
- **PF:** Match wagesheet UAN → PF ECR UAN (exact string match after normalization)
- **ESIC:** Match wagesheet IP Number → ESIC ECR IP Number (exact string match after normalization)

### Name Matching (the hard part)
Name variations in Indian payroll documents:
- Spelling: RAJESH vs RAJSH, KUMAR vs KUMR
- Word order: KUMAR RAJESH vs RAJESH KUMAR
- Titles: MR. RAJESH KUMAR vs RAJESH KUMAR, SHRI/SMT prefixes
- Initials: R. KUMAR vs RAJESH KUMAR
- Father's name included in one but not the other
- Hindi transliteration differences

**Algorithm:**
1. Normalize: lowercase → remove titles (mr/mrs/ms/dr/shri/smt/sh) → remove special chars → collapse whitespace
2. Token-sort: split into tokens, sort alphabetically, rejoin
3. Similarity score: rapidfuzz token_sort_ratio (0–100)
4. Thresholds (configurable in config.py):
   - ≥ 90: **Name match** (MATCHED or AMOUNT_MISMATCH depending on amounts)
   - 70–89: **Possible name mismatch** — flag for human review with both names shown
   - < 70: **Name mismatch** — genuinely different person or severe data entry error

### Amount Matching
- **PF:** Compare wagesheet "PF @ 12%" column with PF ECR "EE Share" column
- **ESIC:** Compare wagesheet "ESIC @ 0.75%" column with ESIC ECR "IP Contribution" column
- Amounts compared as floats with ₹1 tolerance (rounding differences)
- If amounts differ: show wagesheet amount, ECR amount, and difference

## Verdict Assignment

For each employee in the wagesheet, TWO verdicts (one PF, one ESIC):

| Verdict | Condition |
|---|---|
| MATCHED | Identifier found + name matches (≥90) + amount matches (within ₹1) |
| NAME_MISMATCH | Identifier found + name doesn't match (<90) |
| AMOUNT_MISMATCH | Identifier found + name matches + amount differs (>₹1) |
| MISSING | Identifier not found in ECR at all |
| PARSE_ERROR | Could not extract data for this employee (PDF parsing failed on their row) |

## Tech Stack
- **Backend:** FastAPI + Pydantic v2 + SQLAlchemy 2.0 + SQLite (WAL)
- **PDF parsing:** pdfplumber
- **Excel read:** openpyxl
- **Excel write:** openpyxl (with conditional formatting for verdicts)
- **Name matching:** rapidfuzz
- **Frontend:** React 18 + TypeScript + Vite + TanStack Query + Tailwind CSS
- **Single port:** Port 8000 (FastAPI serves built frontend + API)

## Repo Layout
```
case2-wagesheet-ecr/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   ├── matching.md
│   ├── api.md
│   ├── design.md
│   └── phases.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── errors.py
│   │   ├── api/
│   │   │   ├── verification.py
│   │   │   ├── export.py
│   │   │   └── system.py
│   │   ├── services/
│   │   │   ├── storage.py
│   │   │   └── processor.py
│   │   └── pipeline/
│   │       ├── wagesheet_parser.py
│   │       ├── pf_ecr_parser.py
│   │       ├── esic_ecr_parser.py
│   │       ├── name_matcher.py
│   │       ├── verifier.py
│   │       └── report_writer.py
│   └── tests/
├── frontend/
│   └── (React app)
├── sample_data/
│   ├── input/          ← sample wagesheet + ECR PDFs
│   └── output/         ← sample verification report
└── scripts/
    ├── run.sh
    ├── run.ps1
    ├── dev.sh
    └── dev.ps1
```

## Security Limits
- Max file size: 50 MB per file
- Accepted formats: .xlsx/.xls (wagesheet), .pdf (ECRs)
- No secrets in repo
- No PII logged beyond what's needed for matching (names + identifiers only in debug logs)
