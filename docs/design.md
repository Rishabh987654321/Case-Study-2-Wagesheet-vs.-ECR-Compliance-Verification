# UI Design — Wagesheet vs ECR Compliance Verification

## Screens

### 1. Upload Page (/)
The landing page. User uploads three files.

**Layout:**
- Header: "Compliance Verification" + nav links (Upload, History)
- Three distinct drop zones, each labeled:
  - "Vendor Wagesheet (.xlsx)" — with icon
  - "PF ECR (.pdf)" — with icon
  - "ESIC ECR (.pdf)" — with icon
- Each drop zone shows: filename + size after selection, or "Drop file here or click to browse"
- Optional text field: "Verification name (e.g., October 2026)"
- "Start Verification" button — disabled until all 3 files are selected
- File validation: check extensions before upload, show error if wrong type

**Upload flow:**
1. User selects/drops 3 files
2. Clicks "Start Verification"
3. All 3 files upload (show progress)
4. Auto-navigate to results page

### 2. Results Page (/verify/:id)

**Header section:**
- Verification name + status badge
- File names shown
- Created time
- Action buttons: Download Report, Delete

**Summary cards (always visible):**
Two side-by-side summary cards:

PF Verification:
- ✅ Matched: N (green)
- ⚠️ Name Mismatch: N (orange)
- 💰 Amount Mismatch: N (yellow)
- ❌ Missing: N (red)

ESIC Verification:
- ✅ Matched: N (green)
- ⚠️ Name Mismatch: N (orange)
- 💰 Amount Mismatch: N (yellow)
- ❌ Missing: N (red)

**Processing state:**
While status=processing, show spinner + "Parsing documents and matching employees..."
Poll every 2 seconds. When complete, show results.

**Results table:**
| # | Name | UAN | IP Number | PF Verdict | PF Reason | ESIC Verdict | ESIC Reason |
|---|---|---|---|---|---|---|---|

- PF/ESIC verdict columns show colored badges
- Click a row → expand inline detail showing:
  - Side-by-side comparison: Wagesheet values vs ECR values
  - Name similarity score
  - Amount difference (if any)
  - Both raw names

**Filters:**
- Filter by PF verdict (dropdown)
- Filter by ESIC verdict (dropdown)
- Search by name/UAN/IP Number
- "Show only mismatches" quick toggle

**Download:**
- "Download Report (.xlsx)" button → GET /api/verify/{id}/export

### 3. History Page (/history)
- List of past verifications with name, date, status, employee count
- Click → navigate to results page
- Delete button per row

## Status Badges
- MATCHED: green background, white text
- NAME_MISMATCH: orange background, white text
- AMOUNT_MISMATCH: yellow background, dark text
- MISSING: red background, white text
- PARSE_ERROR: gray background

## Responsive
Desktop-first (1280px minimum), same as Case 1.

## Error States
- Server unreachable: "Cannot connect to server" + retry
- Wrong file type: "Please upload an Excel file (.xlsx)" inline on the drop zone
- Parse failure: "Could not read the PF ECR PDF. The file may be corrupted or in an unexpected format."
- Empty wagesheet: "No employee records found in the wagesheet."
- Processing: spinner + "Matching N employees across documents..."
