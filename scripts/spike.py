"""Phase 0 parsing spike — confirm we can extract structured data from all 3 sample files.

Not production code. Validates assumptions before writing the real pipeline parsers.
"""
import re
import sys
from pathlib import Path

import openpyxl
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "sample_data" / "input"

WAGESHEET = INPUT / "Sample_Wagesheet_Aug25.xlsx"
PF_ECR = INPUT / "PF ECR AUG-25 SAMPLE.pdf"
ESIC_ECR = INPUT / "ESIC ECR AUG-25 SAMPLE.pdf"


def parse_wagesheet(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() for h in rows[0]]
    records = []
    for i, row in enumerate(rows[1:], start=2):
        if row[0] is None:
            continue
        rec = dict(zip(header, row))
        records.append(
            {
                "row_number": i,
                "name": str(rec["Name"]).strip(),
                "uan": str(rec["UAN"]).strip(),
                "ip_number": str(rec["IP Number"]).strip(),
                "agency": rec.get("Agency"),
                "state": rec.get("State"),
                "esic_amount": float(rec["ESIC @ 0.75%"]),
                "pf_amount": float(rec["PF @ 12%"]),
            }
        )
    return records


PF_LINE_RE = re.compile(
    r"^(?P<sl>\d+)\s+(?P<uan>\d{6,})\s+(?P<rest>.+?)\s+"
    r"(?P<gross>[\d,]+)\s+(?P<epfw>[\d,]+)\s+(?P<epsw>[\d,]+)\s+(?P<edli>[\d,]+)\s+"
    r"(?P<ee>[\d,]+)\s+(?P<eps>[\d,]+)\s+(?P<er>[\d,]+)\s+(?P<ncp>\d+)$"
)


def split_duplicated_name(rest: str) -> tuple[str, str, bool]:
    """PF ECR prints 'Name as per ECR' and 'Name as per UAN Repository' back to back
    with no delimiter. When both are identical (common case) we can detect the exact
    repeated token sequence. Falls back to an even split if no exact repeat is found
    (flagged as unreliable)."""
    tokens = rest.split()
    n = len(tokens)
    for k in range(1, n // 2 + 1):
        if n == 2 * k and tokens[:k] == tokens[k:]:
            return " ".join(tokens[:k]), " ".join(tokens[k:]), True
    # no exact duplicate found — best-effort even split
    half = n // 2
    return " ".join(tokens[:half]), " ".join(tokens[half:]), False


def parse_pf_ecr(path):
    records = []
    warnings = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = PF_LINE_RE.match(line.strip())
                if not m:
                    continue
                name_ecr, name_uan, clean_split = split_duplicated_name(m["rest"])
                if not clean_split:
                    warnings.append(
                        f"page {page_num}: could not cleanly split duplicated name "
                        f"for UAN {m['uan']} (text: '{m['rest']}')"
                    )
                records.append(
                    {
                        "uan": m["uan"],
                        "name": name_ecr,
                        "ee_share": float(m["ee"].replace(",", "")),
                        "eps_share": float(m["eps"].replace(",", "")),
                    }
                )
    return records, warnings


ESIC_LINE_RE = re.compile(
    r"^(?P<sno>\d+)\s+(?P<disable>\S+)\s+(?P<ip>\d{6,})\s+(?P<name>.+?)\s+"
    r"(?P<days>\d+)\s+(?P<wages>[\d,.]+)\s+(?P<contrib>[\d,.]+)\s+(?P<reason>\S+)$"
)


def parse_esic_ecr(path):
    records = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = ESIC_LINE_RE.match(line.strip())
                if not m:
                    continue
                records.append(
                    {
                        "ip_number": m["ip"],
                        "name": m["name"].strip(),
                        "wages": float(m["wages"].replace(",", "")),
                        "ip_contribution": float(m["contrib"].replace(",", "")),
                    }
                )
    return records


def main():
    ws_records = parse_wagesheet(WAGESHEET)
    print(f"[Wagesheet] {len(ws_records)} employees")
    for r in ws_records[:5]:
        print("  ", r)

    pf_records, pf_warnings = parse_pf_ecr(PF_ECR)
    print(f"\n[PF ECR] {len(pf_records)} members")
    for r in pf_records[:5]:
        print("  ", r)
    for w in pf_warnings:
        print("  WARNING:", w)

    esic_records = parse_esic_ecr(ESIC_ECR)
    print(f"\n[ESIC ECR] {len(esic_records)} insured persons")
    for r in esic_records[:5]:
        print("  ", r)

    pf_by_uan = {r["uan"]: r for r in pf_records}
    esic_by_ip = {r["ip_number"]: r for r in esic_records}

    print("\n[Cross-match]")
    pf_found = esic_found = 0
    name_diffs = []
    for emp in ws_records:
        pf_rec = pf_by_uan.get(emp["uan"])
        esic_rec = esic_by_ip.get(emp["ip_number"])
        if pf_rec:
            pf_found += 1
            if pf_rec["name"].strip().upper() != emp["name"].strip().upper():
                name_diffs.append(("PF", emp["name"], pf_rec["name"], emp["uan"]))
        if esic_rec:
            esic_found += 1
            if esic_rec["name"].strip().upper() != emp["name"].strip().upper():
                name_diffs.append(("ESIC", emp["name"], esic_rec["name"], emp["ip_number"]))

    print(f"Found {pf_found}/{len(ws_records)} in PF ECR, {esic_found}/{len(ws_records)} in ESIC ECR")
    print("\nName differences found (for calibrating fuzzy threshold):")
    for kind, ws_name, ecr_name, ident in name_diffs:
        print(f"  [{kind}] wagesheet='{ws_name}' vs ecr='{ecr_name}' (id={ident})")

    print("\nMissing from PF ECR:")
    for emp in ws_records:
        if emp["uan"] not in pf_by_uan:
            print(f"  {emp['name']} (UAN {emp['uan']})")

    print("\nMissing from ESIC ECR:")
    for emp in ws_records:
        if emp["ip_number"] not in esic_by_ip:
            print(f"  {emp['name']} (IP {emp['ip_number']})")

    print("\nAmount comparison (wagesheet vs ECR):")
    for emp in ws_records:
        pf_rec = pf_by_uan.get(emp["uan"])
        esic_rec = esic_by_ip.get(emp["ip_number"])
        if pf_rec and abs(pf_rec["ee_share"] - emp["pf_amount"]) > 1.0:
            print(f"  [PF] {emp['name']}: wagesheet={emp['pf_amount']} ecr={pf_rec['ee_share']}")
        if esic_rec and abs(esic_rec["ip_contribution"] - emp["esic_amount"]) > 1.0:
            print(f"  [ESIC] {emp['name']}: wagesheet={emp['esic_amount']} ecr={esic_rec['ip_contribution']}")


if __name__ == "__main__":
    sys.exit(main())
