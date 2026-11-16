"""Standalone CLI for the parsing + matching pipeline — no server required.

Usage:
    python -m app.pipeline.cli <wagesheet.xlsx> <pf_ecr.pdf> <esic_ecr.pdf> [--json output.json]
"""

import argparse
import json
import sys
from collections import Counter

from app.config import get_settings
from app.pipeline.esic_ecr_parser import parse_esic_ecr
from app.pipeline.pf_ecr_parser import parse_pf_ecr
from app.pipeline.verifier import verify_employees
from app.pipeline.wagesheet_parser import parse_wagesheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a wagesheet against PF/ESIC ECR PDFs")
    parser.add_argument("wagesheet", help="Path to wagesheet .xlsx")
    parser.add_argument("pf_ecr", help="Path to PF ECR .pdf")
    parser.add_argument("esic_ecr", help="Path to ESIC ECR .pdf")
    parser.add_argument("--json", dest="json_out", help="Write full results as JSON to this path")
    args = parser.parse_args(argv)

    settings = get_settings()

    employees, ws_warnings = parse_wagesheet(args.wagesheet)
    pf_records, pf_warnings = parse_pf_ecr(args.pf_ecr)
    esic_records, esic_warnings = parse_esic_ecr(args.esic_ecr)

    print(f"Wagesheet: {len(employees)} employees ({len(ws_warnings)} warnings)")
    print(f"PF ECR:    {len(pf_records)} members ({len(pf_warnings)} warnings)")
    print(f"ESIC ECR:  {len(esic_records)} insured persons ({len(esic_warnings)} warnings)")

    all_warnings = ws_warnings + pf_warnings + esic_warnings
    if all_warnings:
        print("\nParse warnings:")
        for w in all_warnings:
            print(f"  - {w}")

    results = verify_employees(employees, pf_records, esic_records, settings)

    pf_counts = Counter(r.pf.verdict.value for r in results)
    esic_counts = Counter(r.esic.verdict.value for r in results)

    print(f"\nPF verdicts:   {dict(pf_counts)}")
    print(f"ESIC verdicts: {dict(esic_counts)}")

    print("\nNon-MATCHED rows:")
    for r in results:
        if r.pf.verdict.value != "MATCHED":
            print(f"  [PF]   row {r.row_number} {r.name} (UAN {r.uan}): {r.pf.verdict.value} — {r.pf.reason}")
        if r.esic.verdict.value != "MATCHED":
            print(
                f"  [ESIC] row {r.row_number} {r.name} (IP {r.ip_number}): "
                f"{r.esic.verdict.value} — {r.esic.reason}"
            )

    if args.json_out:
        payload = [r.model_dump(mode="json") for r in results]
        with open(args.json_out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nWrote full results to {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
