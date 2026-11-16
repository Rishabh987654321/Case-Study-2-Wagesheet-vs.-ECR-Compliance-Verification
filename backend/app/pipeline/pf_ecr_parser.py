"""Parser for EPFO Electronic Challan cum Return (ECR) member-detail PDFs.

The official EPFO "Member Details" table has a fixed national template:
Sl.No, UAN, Name as per ECR, Name as per UAN Repository, Gross/EPF/EPS/EDLI Wages,
EE share, EPS share, ER share, NCP Days. Establishment-specific data varies but this
column schema is the government template, not a sample-specific assumption.

Real ECR PDFs are not guaranteed to have ruled table borders (the reference sample does
not), so pdfplumber's line-based `extract_tables()` is tried first and we fall back to
regex parsing of `extract_text()` when it finds nothing.
"""

import re

import pdfplumber

from app.pipeline.name_matcher import normalize_name
from app.pipeline.types import PFECRRecord

_UAN_HINTS = ("uan",)
_NAME_HINTS = ("name",)
_EE_HINTS = ("ee share", "ee", "employee share")

_MEMBER_LINE_RE = re.compile(
    r"^(?P<sl>\d+)\s+(?P<uan>\d{6,})\s+(?P<rest>.+?)\s+"
    r"(?P<gross>[\d,]+)\s+(?P<epfw>[\d,]+)\s+(?P<epsw>[\d,]+)\s+(?P<edli>[\d,]+)\s+"
    r"(?P<ee>[\d,]+)\s+(?P<eps>[\d,]+)\s+(?P<er>[\d,]+)\s+(?P<ncp>\d+)$"
)
_TOTAL_MEMBERS_RE = re.compile(r"Total Members\s+(\d+)")


def _clean_number(text: str) -> float:
    return float(text.replace(",", "").strip())


def _split_duplicated_name(rest: str) -> tuple[str, bool]:
    """EPFO prints 'Name as per ECR' and 'Name as per UAN Repository' back-to-back
    with no delimiter. Detect an exact repeated token sequence (the common case where
    both are identical); fall back to an even split and flag it as unreliable."""
    tokens = rest.split()
    n = len(tokens)
    for k in range(1, n // 2 + 1):
        if n == 2 * k and tokens[:k] == tokens[k:]:
            return " ".join(tokens[:k]), True
    half = max(n // 2, 1)
    return " ".join(tokens[:half]), False


def _classify_header(text: str) -> str | None:
    text = text.lower().strip()
    if any(h in text for h in _UAN_HINTS):
        return "uan"
    if any(h == text or h in text for h in _EE_HINTS):
        return "ee_share"
    if any(h in text for h in _NAME_HINTS):
        return "name"
    return None


def _parse_from_tables(tables: list[list[list]]) -> tuple[list[PFECRRecord], list[str]]:
    records: list[PFECRRecord] = []
    warnings: list[str] = []
    for table in tables:
        col_map: dict[str, int] = {}
        header_row_idx = None
        for row_idx, row in enumerate(table):
            candidate: dict[str, int] = {}
            for col_idx, cell in enumerate(row):
                field = _classify_header(str(cell) if cell else "")
                if field and field not in candidate:
                    candidate[field] = col_idx
            if "uan" in candidate and "ee_share" in candidate:
                col_map = candidate
                header_row_idx = row_idx
                break
        if header_row_idx is None:
            continue
        for row in table[header_row_idx + 1 :]:
            uan_cell = row[col_map["uan"]] if col_map["uan"] < len(row) else None
            if not uan_cell or not re.match(r"^\d{6,}$", str(uan_cell).strip()):
                continue
            name_cell = row[col_map["name"]] if "name" in col_map and col_map["name"] < len(row) else ""
            ee_cell = row[col_map["ee_share"]] if col_map["ee_share"] < len(row) else None
            try:
                ee_share = _clean_number(str(ee_cell))
            except (ValueError, AttributeError):
                warnings.append(f"UAN {uan_cell}: could not parse EE share value '{ee_cell}'")
                continue
            name = str(name_cell).strip() if name_cell else ""
            records.append(
                PFECRRecord(
                    uan=str(uan_cell).strip(),
                    name=name,
                    name_normalized=normalize_name(name),
                    ee_share=ee_share,
                )
            )
    return records, warnings


def _parse_from_text(text: str, page_num: int) -> tuple[list[PFECRRecord], list[str]]:
    records: list[PFECRRecord] = []
    warnings: list[str] = []
    for line in text.splitlines():
        m = _MEMBER_LINE_RE.match(line.strip())
        if not m:
            continue
        name, clean_split = _split_duplicated_name(m["rest"])
        if not clean_split:
            warnings.append(
                f"Page {page_num}: could not cleanly split duplicated name for UAN "
                f"{m['uan']} (raw: '{m['rest']}') — name may be inaccurate"
            )
        records.append(
            PFECRRecord(
                uan=m["uan"],
                name=name,
                name_normalized=normalize_name(name),
                ee_share=_clean_number(m["ee"]),
            )
        )
    return records, warnings


def parse_pf_ecr(file_path: str) -> tuple[list[PFECRRecord], list[str]]:
    """Parse a PF ECR PDF. Returns (records, warnings)."""
    records: list[PFECRRecord] = []
    warnings: list[str] = []
    stated_total: int | None = None

    try:
        pdf = pdfplumber.open(file_path)
    except Exception as exc:  # noqa: BLE001 — any malformed/corrupt/non-PDF file
        return [], [f"Could not open PF ECR PDF: {exc}"]

    with pdf:
        if len(pdf.pages) == 0:
            return [], ["PF ECR PDF has no pages"]

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if stated_total is None:
                m = _TOTAL_MEMBERS_RE.search(text)
                if m:
                    stated_total = int(m.group(1))

            tables = page.extract_tables()
            if tables:
                page_records, page_warnings = _parse_from_tables(tables)
                if not page_records:
                    # Ruled tables existed but didn't look like the member table —
                    # fall back to text parsing for this page.
                    page_records, page_warnings = _parse_from_text(text, page_num)
            else:
                page_records, page_warnings = _parse_from_text(text, page_num)

            records.extend(page_records)
            warnings.extend(page_warnings)

    if not records:
        warnings.append("No member rows could be extracted from the PF ECR PDF")

    seen: dict[str, int] = {}
    deduped: list[PFECRRecord] = []
    for rec in records:
        if rec.uan in seen:
            warnings.append(f"Duplicate UAN {rec.uan} in PF ECR — using first occurrence")
            continue
        seen[rec.uan] = 1
        deduped.append(rec)

    if stated_total is not None and stated_total != len(deduped):
        warnings.append(
            f"PF ECR header states Total Members = {stated_total} but {len(deduped)} "
            "member rows were parsed — some rows may not have been extracted"
        )

    return deduped, warnings
