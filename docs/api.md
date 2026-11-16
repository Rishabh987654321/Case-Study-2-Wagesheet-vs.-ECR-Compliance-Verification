# API Specification

Base URL: `/api`

## Verification Endpoints

### POST /api/verify
Upload three files and start verification.

**Request:** multipart/form-data
- `wagesheet` (file, required): .xlsx/.xls file
- `pf_ecr` (file, required): .pdf file
- `esic_ecr` (file, required): .pdf file
- `name` (string, optional): user-given name for this verification

**Response 201:**
```json
{
  "verification_id": "uuid",
  "status": "processing",
  "message": "Verification started. 3 files uploaded."
}
```

**Response 400:**
```json
{
  "error": "INVALID_FILE",
  "detail": "Wagesheet must be .xlsx or .xls format"
}
```

### GET /api/verify/{id}
Get verification status and summary.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "October 2026 Verification",
  "status": "completed",
  "wagesheet_filename": "wagesheet_oct.xlsx",
  "pf_ecr_filename": "pf_ecr_oct.pdf",
  "esic_ecr_filename": "esic_ecr_oct.pdf",
  "employee_count": 150,
  "summary": {
    "pf": {
      "matched": 140,
      "name_mismatch": 3,
      "amount_mismatch": 5,
      "missing": 2,
      "parse_error": 0
    },
    "esic": {
      "matched": 138,
      "name_mismatch": 4,
      "amount_mismatch": 6,
      "missing": 2,
      "parse_error": 0
    }
  },
  "parse_warnings": ["Row 45: duplicate UAN 100123456789"],
  "created_at": "2026-11-15T10:00:00Z",
  "completed_at": "2026-11-15T10:00:12Z"
}
```

### GET /api/verify/{id}/employees
Get per-employee verification results.

**Query params:**
- `pf_verdict` (string, optional): filter by PF verdict
- `esic_verdict` (string, optional): filter by ESIC verdict
- `q` (string, optional): search by name, UAN, or IP Number
- `page` (int, default 1)
- `page_size` (int, default 50)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "row_number": 1,
      "name": "RAJESH KUMAR",
      "uan": "100123456789",
      "ip_number": "1234567890",
      "agency": "ABC Staffing",
      "state": "Delhi",
      "pf": {
        "ws_amount": 1800.00,
        "ecr_name": "RAJESH KUMAR",
        "ecr_amount": 1800.00,
        "amount_diff": null,
        "name_score": 100.0,
        "verdict": "MATCHED",
        "reason": "UAN found, name matches (100%), amount matches"
      },
      "esic": {
        "ws_amount": 112.50,
        "ecr_name": "RAJESH KUMR",
        "ecr_amount": 112.50,
        "amount_diff": null,
        "name_score": 92.3,
        "verdict": "MATCHED",
        "reason": "IP found, name matches (92.3%), amount matches"
      }
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "pages": 3
}
```

### GET /api/verify/{id}/export
Download verification report as Excel (.xlsx).

**Query params:**
- `format` (string, default "xlsx"): "xlsx" or "csv"

**Response 200:** File download (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)

### GET /api/verify/{id}/unmatched
Get ECR records that don't match any wagesheet employee.

**Response 200:**
```json
{
  "pf_unmatched": [
    {"uan": "100999888777", "name": "UNKNOWN PERSON", "ee_share": 500.00}
  ],
  "esic_unmatched": [
    {"ip_number": "9876543210", "name": "EXTRA PERSON", "ip_contribution": 75.00}
  ]
}
```

### GET /api/verifications
List all verifications.

**Query params:**
- `page` (int, default 1)
- `page_size` (int, default 20)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "October 2026",
      "status": "completed",
      "employee_count": 150,
      "created_at": "2026-11-15T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1
}
```

### DELETE /api/verify/{id}
Delete a verification and its files.

**Response 204:** No content

## System Endpoints

### GET /api/health
**Response 200:** `{"status": "ok"}`

### GET /api/config
**Response 200:**
```json
{
  "max_file_mb": 50,
  "name_match_threshold": 90,
  "name_review_threshold": 70,
  "amount_tolerance": 1.0
}
```

## Error Shape
All errors:
```json
{
  "error": "ERROR_CODE",
  "detail": "Human-readable message"
}
```

Error codes: INVALID_FILE, FILE_TOO_LARGE, NOT_FOUND, PARSE_FAILED, PROCESSING_ERROR, ALREADY_PROCESSING
