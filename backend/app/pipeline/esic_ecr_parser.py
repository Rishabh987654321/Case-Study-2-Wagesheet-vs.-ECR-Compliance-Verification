"""Parser for ESIC Contribution History PDFs.

Like the PF ECR, the reference sample has no ruled table borders, so
`extract_tables()` is tried first (for ESIC exports that do render grid lines) and we
fall back to regex parsing of `extract_text()`.
"""

import re

import pdfplumber

from app.pipeline.name_matcher import normalize_name
from app.pipeline.types import ESICECRRecord

_IP_HINTS = ("ip number", "ip no")
_NAME_HINTS = ("ip name", "name")
_CONTRIBUTION_HINTS = ("ip contribution", "contribution")

_MEMBER_LINE_RE = re.compile(
    r"^(?P<sno>\d+)\s+(?P<disable>\S+)\s+(?P<ip>\d{6,})\s+(?P<name>.+?)\s+"
    r"(?P<days>\d+)\s+(?P<wages>[\d,.]+)\s+(?P<contrib>[\d,.]+)\s+(?P<reason>\S+)$"
)
_TOTAL_CONTRIBUTION_RE = re.compile(
    r"Total IP Contribution.*?\n\s*(?P<total>[\d,.]+)", re.DOTALL
)


def _clean_number(text: str) -> float:
    return float(str(text).replace(",", "").strip())


def _classify_header(text: str) -> str | None:
    text = text.lower().strip()
    if any(h in text for h in _IP_HINTS):
        return "ip_number"
    if any(h in text for h in _CONTRIBUTION_HINTS):
        return "ip_contribution"
    if any(h in text for h in _NAME_HINTS):
        return "name"
    return None


def _parse_from_tables(tables: list[list[list]]) -> tuple[list[ESICECRRecord], list[str]]:
    records: list[ESICECRRecord] = []
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
            if "ip_number" in candidate and "ip_contribution" in candidate:
                col_map = candidate
                header_row_idx = row_idx
                break
        if header_row_idx is None:
            continue
        for row in table[header_row_idx + 1 :]:
            ip_cell = row[col_map["ip_number"]] if col_map["ip_number"] < len(row) else None
            if not ip_cell or not re.match(r"^\d{6,}$", str(ip_cell).strip()):
                continue
            name_cell = row[col_map["name"]] if "name" in col_map and col_map["name"] < len(row) else ""
            contrib_cell = (
                row[col_map["ip_contribution"]] if col_map["ip_contribution"] < len(row) else None
            )
            try:
                contribution = _clean_number(contrib_cell)
            except (ValueError, TypeError):
                warnings.append(
                    f"IP {ip_cell}: could not parse IP Contribution value '{contrib_cell}'"
                )
                continue
            name = str(name_cell).strip() if name_cell else ""
            records.append(
                ESICECRRecord(
                    ip_number=str(ip_cell).strip(),
                    name=name,
                    name_normalized=normalize_name(name),
                    ip_contribution=contribution,
                )
            )
    return records, warnings


def _parse_from_text(text: str) -> tuple[list[ESICECRRecord], list[str]]:
    records: list[ESICECRRecord] = []
    for line in text.splitlines():
        m = _MEMBER_LINE_RE.match(line.strip())
        if not m:
            continue
        name = m["name"].strip()
        records.append(
            ESICECRRecord(
                ip_number=m["ip"],
                name=name,
                name_normalized=normalize_name(name),
                ip_contribution=_clean_number(m["contrib"]),
            )
        )
    return records, []


def parse_esic_ecr(file_path: str) -> tuple[list[ESICECRRecord], list[str]]:
    """Parse an ESIC ECR PDF. Returns (records, warnings)."""
    records: list[ESICECRRecord] = []
    warnings: list[str] = []
    full_text_parts: list[str] = []

    try:
        pdf = pdfplumber.open(file_path)
    except Exception as exc:  # noqa: BLE001 — any malformed/corrupt/non-PDF file
        return [], [f"Could not open ESIC ECR PDF: {exc}"]

    with pdf:
        if len(pdf.pages) == 0:
            return [], ["ESIC ECR PDF has no pages"]

        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text_parts.append(text)

            tables = page.extract_tables()
            if tables:
                page_records, page_warnings = _parse_from_tables(tables)
                if not page_records:
                    page_records, page_warnings = _parse_from_text(text)
            else:
                page_records, page_warnings = _parse_from_text(text)

            records.extend(page_records)
            warnings.extend(page_warnings)

    if not records:
        warnings.append("No insured-person rows could be extracted from the ESIC ECR PDF")

    seen: dict[str, int] = {}
    deduped: list[ESICECRRecord] = []
    for rec in records:
        if rec.ip_number in seen:
            warnings.append(f"Duplicate IP Number {rec.ip_number} in ESIC ECR — using first occurrence")
            continue
        seen[rec.ip_number] = 1
        deduped.append(rec)

    full_text = "\n".join(full_text_parts)
    m = _TOTAL_CONTRIBUTION_RE.search(full_text)
    if m:
        stated_total = _clean_number(m["total"])
        parsed_total = sum(r.ip_contribution for r in deduped)
        if abs(stated_total - parsed_total) > 1.0:
            warnings.append(
                f"ESIC ECR header states Total IP Contribution = {stated_total} but parsed "
                f"rows sum to {parsed_total} — some rows may not have been extracted correctly"
            )

    return deduped, warnings
