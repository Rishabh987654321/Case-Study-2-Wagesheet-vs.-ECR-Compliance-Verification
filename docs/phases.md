# Phases — Wagesheet vs ECR Compliance Verification

## Phase 0: Data Inspection & Setup (~1 hour)
- Examine sample wagesheet structure (columns, data types, quirks)
- Examine PF ECR PDF layout (table structure, column identification)
- Examine ESIC ECR PDF layout (table structure, column identification)
- Set up Python environment and test PDF parsing libraries
- Initialize repo structure with docs
- Acceptance: parser spike successfully extracts data from all 3 sample files

## Phase 1: Parsing + Matching Engine (~3 hours)
- Wagesheet parser (openpyxl, auto-detect headers, handle merged cells)
- PF ECR parser (pdfplumber, multi-page tables)
- ESIC ECR parser (pdfplumber, multi-page tables)
- Name normalization module
- Fuzzy name matching with configurable thresholds
- Verification logic (identifier → name → amount)
- CLI tool for standalone testing
- Unit tests for parsers and matching
- Acceptance: CLI produces correct verdicts on sample data

## Phase 2: Backend API (~2 hours)
- FastAPI app with all endpoints from api.md
- File upload and storage
- Background processing (asyncio task)
- SQLite persistence for verifications and results
- Excel export with formatting
- API tests
- Acceptance: full cycle works via Swagger/curl

## Phase 3: Frontend (~2 hours)
- Three-file upload page with validation
- Results page with summary cards and table
- Row detail expansion with side-by-side comparison
- Filters and search
- History page
- Download button
- Single-port serving (FastAPI serves built frontend)
- Run scripts (run.sh, run.ps1, dev.sh, dev.ps1)
- Acceptance: manual test checklist passes

## Phase 4: Hardening + README (~1.5 hours)
- Edge cases: empty files, wrong formats, missing columns, large PDFs
- README with quick start, approach, matching strategy, known limitations
- Sample outputs
- Security check (no secrets, no PII in logs)
- Acceptance: README quick start works from clean clone in <15 min

## Cut List (if time runs short)
1. ESIC ECR Unmatched sheet (nice-to-have)
2. History page (can just do single verification flow)
3. Row detail expansion (verdicts in table are enough)
4. Conditional formatting in Excel export (plain values are enough)

## Time Budget: ~9.5 hours total
