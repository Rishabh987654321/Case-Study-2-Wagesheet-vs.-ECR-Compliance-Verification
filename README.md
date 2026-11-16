# Case Study 2: Wagesheet vs ECR Compliance Verification

## What it does

Vendor agencies deploy contract workers at Prozo fulfilment centres, and every month they submit a wagesheet (Excel) alongside two government compliance filings: a PF ECR and an ESIC ECR (both PDFs). Today a compliance team manually cross-checks hundreds of rows across all three documents to confirm the right person, the right identifier, and the right amount were actually deposited with the authorities. This app automates that check: upload the three files, and the system matches every employee by UAN (PF) and IP Number (ESIC), fuzzy-matches names to catch spelling/formatting noise without false-flagging trivial variations, compares deducted vs. deposited amounts, and produces a downloadable Excel report with a verdict for every employee on both PF and ESIC.

## Quick Start (under 15 minutes)

**Prerequisites:** Python 3.11+, Node.js 18+, npm

### Option A: One command

```bash
chmod +x scripts/run.sh && ./scripts/run.sh    # macOS/Linux
```
```powershell
.\scripts\run.ps1                                # Windows
```

This creates the backend virtualenv, installs Python deps, installs and builds the frontend, and starts the server at **http://localhost:8000**.

### Option B: Manual

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../frontend && npm install && npm run build
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Dev mode (hot reload, separate ports)

```bash
./scripts/dev.sh      # macOS/Linux — backend :8000 (reload) + Vite dev server
.\scripts\dev.ps1     # Windows
```

Open the printed Vite URL (usually http://localhost:5173) — it proxies `/api` to the backend.

## How it works

**Pipeline:** `wagesheet.xlsx` + `pf_ecr.pdf` + `esic_ecr.pdf` → three parsers → name matcher → verifier → Excel report. See `docs/architecture.md` for the full system diagram and `docs/dataset-notes.md` for what the Phase 0 inspection of the real sample files found (notably: neither ECR PDF has ruled table lines, so both parsers try `pdfplumber.extract_tables()` first and fall back to regex line-parsing).

### The matching approach (this is the heart of the system)

- **PF:** match wagesheet UAN → PF ECR UAN (exact string match), then fuzzy-match names, then compare the wagesheet's "PF @ 12%" against the ECR's EE share.
- **ESIC:** match wagesheet IP Number → ESIC ECR IP Number (exact string match), then fuzzy-match names, then compare the wagesheet's "ESIC @ 0.75%" against the ECR's IP Contribution.
- **Name matching:** normalize (lowercase → strip titles like Mr./Shri/Smt → strip patronymic clauses like "S/O Ram Kumar" → strip special characters → collapse whitespace) → `rapidfuzz.fuzz.token_sort_ratio` on the normalized strings. Token-sort means word order doesn't matter ("KUMAR RAJESH" and "RAJESH KUMAR" both score 100).
- **Thresholds:** score ≥ 90 → name matches, proceed to amount check. 70–89 → flagged as `NAME_MISMATCH` with "review suggested" in the reason (could be the same person with a significant spelling variation, or could be someone else — a human should look). < 70 → `NAME_MISMATCH`, likely a different person.
- **Amount tolerance:** ₹1 (configurable) to absorb rounding.
- All of the above are configurable via `.env` — see the Configuration table below.

**Why these thresholds, with real evidence from the sample data** (`sample_data/input/`): the sample files contain two genuinely injected name discrepancies, and the default thresholds separate them correctly without any tuning:
- Wagesheet "DINESH PRASAD" vs. PF ECR "DEVENDRA PRASAD" → `token_sort_ratio` = **64.3** → correctly lands below the 70 floor → definite `NAME_MISMATCH`.
- Wagesheet "REKHA SHARMA" vs. ESIC ECR "RENU SHARMA" → `token_sort_ratio` = **78.3** → correctly lands in the 70–89 review band → flagged, but worded as "possible mismatch, review suggested" rather than a hard fail, since the names are close enough it could be a typo on either side.
- For contrast, minor-but-harmless spelling noise like "RAJESH KUMAR" vs. "RAJSH KUMR" scores **90.9** — just above the match threshold, so trivial OCR/typing variation doesn't trigger a false mismatch.

### Verdict types

| Verdict | What it means |
|---|---|
| MATCHED | Identifier found, name matches (≥90%), amount matches (within ₹1) |
| NAME_MISMATCH | Identifier found but name similarity <90% — may be wrong person or data entry error |
| AMOUNT_MISMATCH | Identifier + name match but amounts differ by >₹1 |
| MISSING | Employee's identifier not in the ECR at all (or the wagesheet has no UAN/IP Number for them) |
| PARSE_ERROR | Could not process this employee's row (reserved for partial-row extraction failures; a fully unreadable ECR instead degrades every employee to MISSING with a parse warning — see Known Limitations) |

Every employee gets **two independent verdicts** — one for PF, one for ESIC — since the two filings are matched and checked separately.

## Results on Sample Data

Run `python -m app.pipeline.cli <wagesheet> <pf_ecr> <esic_ecr>` from `backend/` (after activating the venv) to reproduce this, or upload the files through the UI/API — both paths produce identical results:

- **Employees in wagesheet:** 12
- **PF:** 9 matched, 1 name mismatch, 1 amount mismatch, 1 missing, 0 parse error
- **ESIC:** 8 matched, 1 name mismatch, 1 amount mismatch, 2 missing, 0 parse error

Every non-MATCHED case, with the real reason:

| Employee | Side | Verdict | Why |
|---|---|---|---|
| DINESH PRASAD | PF | NAME_MISMATCH | ECR has "DEVENDRA PRASAD" for the same UAN — score 64.3, below the review floor |
| REKHA SHARMA | ESIC | NAME_MISMATCH | ECR has "RENU SHARMA" for the same IP Number — score 78.3, in the review band |
| VIKRAM THAKUR | PF | AMOUNT_MISMATCH | Wagesheet says ₹1654.00, PF ECR EE share is ₹1354.00 (diff ₹300) |
| NEHA MISHRA | ESIC | AMOUNT_MISMATCH | Wagesheet says ₹86.00, ESIC ECR contribution is ₹66.00 (diff ₹20) |
| SANJAY PASWAN | PF + ESIC | MISSING | UAN/IP Number absent from both ECRs entirely — this person's contributions were never filed |
| POOJA GUPTA | ESIC | MISSING | Present and correct in the PF ECR, but absent from the ESIC ECR specifically |

These are not synthetic — they're the actual output of the pipeline against `sample_data/input/`, and the sample set was evidently constructed to exercise exactly these cases. `sample_data/output/` contains the generated `verification_report.xlsx` and `summary.json` from this run.

## Configuration

All in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `DATA_DIR` | `data` | Where uploads, the SQLite DB, and generated exports are stored |
| `MAX_FILE_MB` | `50` | Max size per uploaded file |
| `NAME_MATCH_THRESHOLD` | `90` | Score ≥ this = name considered a match |
| `NAME_REVIEW_THRESHOLD` | `70` | Score below this = definite mismatch; between this and the match threshold = flagged for review |
| `AMOUNT_TOLERANCE` | `1.0` | ₹ tolerance when comparing wagesheet vs. ECR amounts |
| `LOG_LEVEL` | `INFO` | Python logging level |

## What I would improve with more time

1. **OCR fallback for scanned PDF ECRs** — `pdfplumber` can't extract text from an image-only PDF; a Tesseract pass would let the system handle scanned/re-photographed filings instead of degrading every employee to MISSING.
2. **Phonetic matching alongside fuzzy matching** — Soundex/Metaphone would catch transliteration variants (MOHAMMED/MUHAMMAD/MOHD) that `token_sort_ratio` alone scores inconsistently.
3. **Hindi↔English transliteration handling** — if an ECR ever carries Devanagari names against an English wagesheet, today's normalizer does nothing useful; a transliteration library would be needed.
4. **Batch/multi-month processing** — upload a whole quarter's filings at once and get one consolidated report instead of one verification per month.
5. **Trend analysis** — flag an employee who shows up as NAME_MISMATCH or AMOUNT_MISMATCH for several months running, which is a stronger compliance signal than any single month.
6. **Manual override UI** — let the compliance reviewer mark a NAME_MISMATCH as "confirmed same person," persisted so it doesn't need re-review next month.
7. **Real ruled-table PDFs** — the current PF/ESIC parsers were built against the one real sample format EPFO/ESIC actually produce (no grid lines); if a different establishment's export does have ruled lines, the `extract_tables()` first-try path handles it, but it's only been validated against synthetic fixtures, not another live sample.

## Known Limitations

- **Scanned/image-based PDFs:** no text layer means no extraction at all — every employee on that side degrades to MISSING with a parse warning, not a crash, but also not useful output. Needs OCR (not implemented, no paid APIs allowed).
- **Hindi name in one document, English transliteration in another:** may score low even if it's the same person — not handled.
- **Very short names (3–4 characters):** can produce misleadingly high fuzzy-match scores against an unrelated short name; documented in `docs/matching.md`.
- **Surnames that collide with stripped titles:** the title-removal list includes "kumari" (a common honorific prefix), which also strips it when it's someone's actual surname (e.g., "KAVITA KUMARI" normalizes to "kavita"). This is symmetric on both sides of every comparison, so it doesn't cause false matches or mismatches in practice — but it does mean the stored `name_normalized` isn't always the visually "complete" name.
- **PDF table extraction depends on structure:** the real EPFO/ESIC export format has no ruled lines and is parsed via header-aware regex; a free-form or wildly different PDF layout may fail to extract anything (degrades to a parse warning, not a crash).
- **Father's-name removal is pattern-based** (`S/O`, `D/O`, `W/O`, `C/O` only) — unusual formats won't be stripped.
- **Formula cells in the wagesheet** are read via openpyxl's cached value, which is always present in a file actually saved by Excel/Google Sheets — but a file with formulas and no cached value (e.g., written by certain non-Excel tools) will read as blank, since pure-Python readers can't evaluate formulas.

## Project Structure

```
case2-wagesheet-ecr/
├── README.md                    ← you are here
├── AGENTS.md                    ← project rules/conventions
├── .env.example
├── .gitignore
├── docs/                        ← design docs written before implementation
│   ├── architecture.md
│   ├── data_model.md
│   ├── matching.md
│   ├── api.md
│   ├── design.md
│   ├── phases.md
│   └── dataset-notes.md         ← Phase 0 findings on the real sample file formats
├── backend/
│   ├── requirements.txt
│   ├── pyproject.toml           ← ruff config
│   ├── app/
│   │   ├── main.py              ← FastAPI app, CORS, error handlers, static frontend serving
│   │   ├── config.py            ← Pydantic Settings (.env)
│   │   ├── db.py / models.py    ← SQLAlchemy (SQLite, WAL)
│   │   ├── schemas.py           ← Pydantic request/response models
│   │   ├── errors.py            ← typed API errors
│   │   ├── api/                 ← verification.py, system.py (routers)
│   │   ├── services/            ← storage.py (file I/O), processor.py (background job)
│   │   └── pipeline/             ← the actual verification engine, usable standalone via cli.py
│   │       ├── wagesheet_parser.py
│   │       ├── pf_ecr_parser.py
│   │       ├── esic_ecr_parser.py
│   │       ├── name_matcher.py
│   │       ├── verifier.py
│   │       ├── report_writer.py
│   │       └── cli.py
│   └── tests/                   ← 76 pytest tests across parsers, matcher, verifier, API
├── frontend/
│   └── src/
│       ├── api/                 ← typed API client
│       ├── components/          ← DropZone, VerdictBadge, SummaryCard, Layout, Toast, ErrorBoundary
│       └── routes/               ← UploadPage, ResultsPage, HistoryPage
├── sample_data/
│   ├── input/                   ← sample wagesheet + ECR PDFs
│   └── output/                  ← verification_report.xlsx + summary.json from a real run
└── scripts/
    ├── run.sh / run.ps1         ← build + single-port production serve
    └── dev.sh / dev.ps1         ← backend reload + Vite dev server
```

## Testing

```bash
cd backend && source .venv/bin/activate
ruff check app/ tests/
pytest tests/ -v
```

76 tests covering: name normalization/matching edge cases, all three parsers against both the real sample files and synthetic edge cases (corrupt/empty files, scanned PDFs, duplicate identifiers), the verifier's full verdict matrix, and the API end-to-end (upload → process → filter/search → export → delete).
