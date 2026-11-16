# Data Model — Wagesheet vs ECR Compliance Verification

## Database Tables (SQLite)

### verifications
| Column | Type | Description |
|---|---|---|
| id | TEXT PK | UUID |
| name | TEXT | Optional user-given name |
| status | TEXT | uploading, processing, completed, failed |
| wagesheet_filename | TEXT | Original wagesheet filename |
| pf_ecr_filename | TEXT | Original PF ECR filename |
| esic_ecr_filename | TEXT | Original ESIC ECR filename |
| employee_count | INT | Total employees parsed from wagesheet |
| pf_matched | INT | Count of PF MATCHED verdicts |
| pf_name_mismatch | INT | Count of PF NAME_MISMATCH |
| pf_amount_mismatch | INT | Count of PF AMOUNT_MISMATCH |
| pf_missing | INT | Count of PF MISSING |
| esic_matched | INT | Count of ESIC MATCHED |
| esic_name_mismatch | INT | Count of ESIC NAME_MISMATCH |
| esic_amount_mismatch | INT | Count of ESIC AMOUNT_MISMATCH |
| esic_missing | INT | Count of ESIC MISSING |
| parse_warnings | TEXT | JSON array of parsing warnings |
| created_at | DATETIME | |
| completed_at | DATETIME | |
| error_message | TEXT | If status=failed |

### employees
| Column | Type | Description |
|---|---|---|
| id | TEXT PK | UUID |
| verification_id | TEXT FK | → verifications.id |
| row_number | INT | Row number in wagesheet (for ordering) |
| name | TEXT | Name from wagesheet (original) |
| name_normalized | TEXT | Normalized name |
| uan | TEXT | UAN from wagesheet |
| ip_number | TEXT | IP Number from wagesheet |
| agency | TEXT | Agency from wagesheet |
| state | TEXT | State from wagesheet |
| ws_pf_amount | REAL | PF amount from wagesheet |
| ws_esic_amount | REAL | ESIC amount from wagesheet |
| pf_verdict | TEXT | MATCHED/NAME_MISMATCH/AMOUNT_MISMATCH/MISSING/PARSE_ERROR |
| pf_ecr_name | TEXT | Name found in PF ECR (null if MISSING) |
| pf_ecr_amount | REAL | EE Share from PF ECR (null if MISSING) |
| pf_amount_diff | REAL | Difference (null if amounts match or MISSING) |
| pf_name_score | REAL | Name similarity score 0-100 (null if MISSING) |
| pf_reason | TEXT | Human-readable reason for the verdict |
| esic_verdict | TEXT | MATCHED/NAME_MISMATCH/AMOUNT_MISMATCH/MISSING/PARSE_ERROR |
| esic_ecr_name | TEXT | Name found in ESIC ECR (null if MISSING) |
| esic_ecr_amount | REAL | IP Contribution from ESIC ECR (null if MISSING) |
| esic_amount_diff | REAL | Difference (null if amounts match or MISSING) |
| esic_name_score | REAL | Name similarity score 0-100 (null if MISSING) |
| esic_reason | TEXT | Human-readable reason for the verdict |

## Parsed Data (in-memory, not persisted)

### WagesheetEmployee
```python
class WagesheetEmployee(BaseModel):
    row_number: int
    name: str
    name_normalized: str
    uan: str | None          # May be empty for some employees
    ip_number: str | None    # May be empty for some employees
    agency: str | None
    state: str | None
    pf_amount: float | None  # PF @ 12% column
    esic_amount: float | None  # ESIC @ 0.75% column
```

### PFECRRecord
```python
class PFECRRecord(BaseModel):
    uan: str
    name: str
    name_normalized: str
    ee_share: float          # Employee's PF contribution
    eps_share: float | None  # Employer's EPS (not used for matching but extracted)
```

### ESICECRRecord
```python
class ESICECRRecord(BaseModel):
    ip_number: str
    name: str
    name_normalized: str
    wages: float | None
    ip_contribution: float   # Employee's ESIC contribution
```

## Export Spreadsheet Spec

### Sheet 1: "Verification Details"
| Column | Source |
|---|---|
| S.No | Sequential |
| Employee Name | wagesheet.name |
| UAN | wagesheet.uan |
| IP Number | wagesheet.ip_number |
| Agency | wagesheet.agency |
| State | wagesheet.state |
| WS PF Amount | wagesheet.pf_amount |
| PF ECR Name | employee.pf_ecr_name |
| PF ECR Amount | employee.pf_ecr_amount |
| PF Difference | employee.pf_amount_diff |
| PF Name Score | employee.pf_name_score |
| PF Verdict | employee.pf_verdict |
| PF Reason | employee.pf_reason |
| WS ESIC Amount | wagesheet.esic_amount |
| ESIC ECR Name | employee.esic_ecr_name |
| ESIC ECR Amount | employee.esic_ecr_amount |
| ESIC Difference | employee.esic_amount_diff |
| ESIC Name Score | employee.esic_name_score |
| ESIC Verdict | employee.esic_verdict |
| ESIC Reason | employee.esic_reason |

Conditional formatting:
- MATCHED rows: green background
- NAME_MISMATCH: orange background
- AMOUNT_MISMATCH: yellow background
- MISSING: red background

### Sheet 2: "Summary"
| Metric | PF | ESIC |
|---|---|---|
| Total Employees | N | N |
| Matched | N (X%) | N (X%) |
| Name Mismatch | N (X%) | N (X%) |
| Amount Mismatch | N (X%) | N (X%) |
| Missing | N (X%) | N (X%) |
| Parse Error | N (X%) | N (X%) |

### Sheet 3: "PF ECR Unmatched"
Rows from PF ECR that have no matching UAN in the wagesheet (extra employees in ECR).

### Sheet 4: "ESIC ECR Unmatched"
Rows from ESIC ECR that have no matching IP Number in the wagesheet.

## .env.example
```
# Server
HOST=0.0.0.0
PORT=8000

# Storage
DATA_DIR=data
MAX_FILE_MB=50

# Name matching
NAME_MATCH_THRESHOLD=90      # Score >= this = names match
NAME_REVIEW_THRESHOLD=70     # Score 70-89 = possible mismatch, flag for review
AMOUNT_TOLERANCE=1.0         # ₹1 tolerance for rounding

# Processing
LOG_LEVEL=INFO
```
