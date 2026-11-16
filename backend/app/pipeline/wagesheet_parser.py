import re

import openpyxl

from app.pipeline.name_matcher import normalize_name
from app.pipeline.types import WagesheetEmployee

_MAX_HEADER_SCAN_ROWS = 20

# Field -> substrings that identify a header cell as that field, checked in
# priority order (agency/state/esic/pf/ip before the generic "name" catch-all,
# so "Agency Name" doesn't get claimed by the name field).
_UAN_HINTS = ("uan",)
_IP_HINTS = ("ip number", "ip no", "insurance number", "ip num")
_AGENCY_HINTS = ("agency", "vendor", "contractor")
_STATE_HINTS = ("state",)
_ESIC_HINTS = ("esic",)
_PF_HINTS = ("pf",)
_NAME_HINTS = ("name",)

_TOTAL_ROW_RE = re.compile(r"\b(total|grand total|subtotal|sub-total)\b", re.IGNORECASE)


def _normalize_header(value) -> str:
    if value is None:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9%./ ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _classify_header(text: str) -> str | None:
    if any(h in text for h in _UAN_HINTS):
        return "uan"
    if any(h in text for h in _IP_HINTS):
        return "ip_number"
    if any(h in text for h in _AGENCY_HINTS):
        return "agency"
    if any(h in text for h in _STATE_HINTS):
        return "state"
    if any(h in text for h in _ESIC_HINTS):
        return "esic_amount"
    if any(h in text for h in _PF_HINTS):
        return "pf_amount"
    if any(h in text for h in _NAME_HINTS):
        return "name"
    return None


def _find_header_row(rows: list[tuple]) -> tuple[int, dict[str, int]]:
    """Scan the first N rows for one that yields both a UAN/IP identifier column
    and a Name column. Returns (row_index_0_based, {field: col_index})."""
    for row_idx, row in enumerate(rows[:_MAX_HEADER_SCAN_ROWS]):
        col_map: dict[str, int] = {}
        for col_idx, cell in enumerate(row):
            field = _classify_header(_normalize_header(cell))
            if field and field not in col_map:
                col_map[field] = col_idx
        has_identifier = "uan" in col_map or "ip_number" in col_map
        if has_identifier and "name" in col_map:
            return row_idx, col_map
    raise ValueError(
        "Could not find a header row with Name + UAN/IP Number columns "
        f"in the first {_MAX_HEADER_SCAN_ROWS} rows"
    )


def _cell_to_identifier(value) -> str | None:
    """Normalize a UAN/IP Number cell to a clean string, handling Excel's habit
    of storing long digit strings as floats (scientific notation risk)."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    text = text.removesuffix(".0")
    return text or None


def _cell_to_amount(value, row_number: int, field_name: str, warnings: list[str]) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        warnings.append(f"Row {row_number}: could not parse {field_name} value '{value}' as a number")
        return None


def _is_blank_row(row: tuple) -> bool:
    return all(cell is None or str(cell).strip() == "" for cell in row)


def _is_total_row(row: tuple) -> bool:
    return any(cell is not None and _TOTAL_ROW_RE.search(str(cell)) for cell in row)


def _get_field(row: tuple, col_map: dict[str, int], field: str):
    idx = col_map.get(field)
    return row[idx] if idx is not None and idx < len(row) else None


def parse_wagesheet(file_path: str) -> tuple[list[WagesheetEmployee], list[str]]:
    """Parse an Excel wagesheet into employee records.

    Returns (employees, warnings). Auto-detects the header row and maps columns
    by header text so vendor files with different column names/order still work.
    """
    warnings: list[str] = []
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as exc:
        raise ValueError(
            "Could not read the wagesheet. The file may be corrupted, empty, or not a valid Excel file."
        ) from exc
    ws = wb[wb.sheetnames[0]]
    if len(wb.sheetnames) > 1:
        warnings.append(
            f"Workbook has {len(wb.sheetnames)} sheets; using first sheet '{wb.sheetnames[0]}'"
        )

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["Wagesheet is empty"]

    header_row_idx, col_map = _find_header_row(rows)

    employees: list[WagesheetEmployee] = []
    seen_uans: dict[str, int] = {}
    seen_ips: dict[str, int] = {}

    for offset, row in enumerate(rows[header_row_idx + 1 :]):
        excel_row_number = header_row_idx + 2 + offset  # 1-based Excel row number
        if _is_blank_row(row):
            continue
        if _is_total_row(row):
            continue

        name_raw = _get_field(row, col_map, "name")
        if name_raw is None or str(name_raw).strip() == "":
            warnings.append(f"Row {excel_row_number}: skipped — no name found")
            continue
        name = str(name_raw).strip()

        uan = _cell_to_identifier(_get_field(row, col_map, "uan"))
        ip_number = _cell_to_identifier(_get_field(row, col_map, "ip_number"))
        agency = _get_field(row, col_map, "agency")
        state = _get_field(row, col_map, "state")
        pf_amount = _cell_to_amount(
            _get_field(row, col_map, "pf_amount"), excel_row_number, "PF amount", warnings
        )
        esic_amount = _cell_to_amount(
            _get_field(row, col_map, "esic_amount"), excel_row_number, "ESIC amount", warnings
        )

        if uan:
            if uan in seen_uans:
                warnings.append(
                    f"Row {excel_row_number}: duplicate UAN {uan} (also seen on row {seen_uans[uan]})"
                )
            else:
                seen_uans[uan] = excel_row_number
        if ip_number:
            if ip_number in seen_ips:
                warnings.append(
                    f"Row {excel_row_number}: duplicate IP Number {ip_number} "
                    f"(also seen on row {seen_ips[ip_number]})"
                )
            else:
                seen_ips[ip_number] = excel_row_number

        employees.append(
            WagesheetEmployee(
                row_number=excel_row_number,
                name=name,
                name_normalized=normalize_name(name),
                uan=uan,
                ip_number=ip_number,
                agency=str(agency).strip() if agency is not None else None,
                state=str(state).strip() if state is not None else None,
                pf_amount=pf_amount,
                esic_amount=esic_amount,
            )
        )

    if not employees:
        warnings.append("No employee rows found below the header")

    return employees, warnings
