"""Excel export for a completed verification: details + summary + unmatched-ECR sheets."""

from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.pipeline.types import EmployeeVerification, ESICECRRecord, PFECRRecord

_VERDICT_FILLS = {
    "MATCHED": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
    "NAME_MISMATCH": PatternFill(start_color="FFD8A8", end_color="FFD8A8", fill_type="solid"),
    "AMOUNT_MISMATCH": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
    "MISSING": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    "PARSE_ERROR": PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid"),
}

_DETAIL_HEADERS = [
    "S.No",
    "Employee Name",
    "UAN",
    "IP Number",
    "Agency",
    "State",
    "WS PF Amount",
    "PF ECR Name",
    "PF ECR Amount",
    "PF Difference",
    "PF Name Score",
    "PF Verdict",
    "PF Reason",
    "WS ESIC Amount",
    "ESIC ECR Name",
    "ESIC ECR Amount",
    "ESIC Difference",
    "ESIC Name Score",
    "ESIC Verdict",
    "ESIC Reason",
]
_PF_VERDICT_COL = 12
_ESIC_VERDICT_COL = 19


def _autosize_columns(ws: Worksheet, num_columns: int) -> None:
    for col_idx in range(1, num_columns + 1):
        letter = ws.cell(row=1, column=col_idx).column_letter
        max_len = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
            default=10,
        )
        ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 50)


def _write_details_sheet(wb: Workbook, employees: list[EmployeeVerification]) -> None:
    ws = wb.active
    ws.title = "Verification Details"
    ws.append(_DETAIL_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"

    for i, emp in enumerate(employees, start=1):
        ws.append(
            [
                i,
                emp.name,
                emp.uan,
                emp.ip_number,
                emp.agency,
                emp.state,
                emp.ws_pf_amount,
                emp.pf.ecr_name,
                emp.pf.ecr_amount,
                emp.pf.amount_diff,
                emp.pf.name_score,
                emp.pf.verdict.value,
                emp.pf.reason,
                emp.ws_esic_amount,
                emp.esic.ecr_name,
                emp.esic.ecr_amount,
                emp.esic.amount_diff,
                emp.esic.name_score,
                emp.esic.verdict.value,
                emp.esic.reason,
            ]
        )
        row = ws.max_row
        pf_fill = _VERDICT_FILLS.get(emp.pf.verdict.value)
        if pf_fill:
            ws.cell(row=row, column=_PF_VERDICT_COL).fill = pf_fill
        esic_fill = _VERDICT_FILLS.get(emp.esic.verdict.value)
        if esic_fill:
            ws.cell(row=row, column=_ESIC_VERDICT_COL).fill = esic_fill

    _autosize_columns(ws, len(_DETAIL_HEADERS))


def _write_summary_sheet(wb: Workbook, employees: list[EmployeeVerification]) -> None:
    ws = wb.create_sheet("Summary")
    pf_counts = Counter(e.pf.verdict.value for e in employees)
    esic_counts = Counter(e.esic.verdict.value for e in employees)
    total = len(employees)

    def pct(n: int) -> str:
        return f"{n} ({(n / total * 100):.1f}%)" if total else f"{n} (0%)"

    ws.append(["Metric", "PF", "ESIC"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    ws.append(["Total Employees", total, total])
    for label, key in [
        ("Matched", "MATCHED"),
        ("Name Mismatch", "NAME_MISMATCH"),
        ("Amount Mismatch", "AMOUNT_MISMATCH"),
        ("Missing", "MISSING"),
        ("Parse Error", "PARSE_ERROR"),
    ]:
        ws.append([label, pct(pf_counts.get(key, 0)), pct(esic_counts.get(key, 0))])

    _autosize_columns(ws, 3)


def _write_unmatched_pf_sheet(wb: Workbook, pf_unmatched: list[PFECRRecord]) -> None:
    ws = wb.create_sheet("PF ECR Unmatched")
    ws.append(["UAN", "Name", "EE Share"])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for rec in pf_unmatched:
        ws.append([rec.uan, rec.name, rec.ee_share])
    _autosize_columns(ws, 3)


def _write_unmatched_esic_sheet(wb: Workbook, esic_unmatched: list[ESICECRRecord]) -> None:
    ws = wb.create_sheet("ESIC ECR Unmatched")
    ws.append(["IP Number", "Name", "IP Contribution"])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for rec in esic_unmatched:
        ws.append([rec.ip_number, rec.name, rec.ip_contribution])
    _autosize_columns(ws, 3)


def write_verification_report(
    employees: list[EmployeeVerification],
    pf_unmatched: list[PFECRRecord],
    esic_unmatched: list[ESICECRRecord],
    output_path: str,
) -> None:
    wb = Workbook()
    _write_details_sheet(wb, employees)
    _write_summary_sheet(wb, employees)
    _write_unmatched_pf_sheet(wb, pf_unmatched)
    _write_unmatched_esic_sheet(wb, esic_unmatched)
    for ws in wb.worksheets:
        for cell in ws[1]:
            cell.alignment = Alignment(horizontal="center")
    wb.save(output_path)
