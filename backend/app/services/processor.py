"""Background processing: parse all 3 files, verify, persist results, write exports.

Runs as a plain sync function dispatched via FastAPI BackgroundTasks, which executes
sync callables in a thread pool — keeps the event loop free while pdfplumber/openpyxl
do their (CPU/IO bound) work.
"""

import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.db import SessionLocal
from app.models import EmployeeRecord, VerificationRecord
from app.pipeline.esic_ecr_parser import parse_esic_ecr
from app.pipeline.pf_ecr_parser import parse_pf_ecr
from app.pipeline.report_writer import write_verification_report
from app.pipeline.verifier import verify_employees
from app.pipeline.wagesheet_parser import parse_wagesheet
from app.services import storage

logger = logging.getLogger(__name__)


def unmatched_path(data_dir: Path, verification_id: str) -> Path:
    return data_dir / "exports" / f"{verification_id}_unmatched.json"


def export_path(data_dir: Path, verification_id: str) -> Path:
    return data_dir / "exports" / f"{verification_id}.xlsx"


def process_verification(verification_id: str) -> None:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    db = SessionLocal()
    try:
        verification = db.get(VerificationRecord, verification_id)
        if verification is None:
            logger.warning("process_verification: verification %s not found", verification_id)
            return

        wagesheet_path = storage.get_file_path(data_dir, verification_id, "wagesheet")
        pf_path = storage.get_file_path(data_dir, verification_id, "pf_ecr")
        esic_path = storage.get_file_path(data_dir, verification_id, "esic_ecr")
        if not (wagesheet_path and pf_path and esic_path):
            raise RuntimeError("One or more uploaded files are missing from storage")

        employees, ws_warnings = parse_wagesheet(str(wagesheet_path))
        pf_records, pf_warnings = parse_pf_ecr(str(pf_path))
        esic_records, esic_warnings = parse_esic_ecr(str(esic_path))

        if not employees:
            raise RuntimeError("No employee records found in the wagesheet")

        results = verify_employees(employees, pf_records, esic_records, settings)

        db.query(EmployeeRecord).filter_by(verification_id=verification_id).delete()
        for r in results:
            db.add(
                EmployeeRecord(
                    id=uuid4().hex,
                    verification_id=verification_id,
                    row_number=r.row_number,
                    name=r.name,
                    name_normalized=r.name.lower(),
                    uan=r.uan,
                    ip_number=r.ip_number,
                    agency=r.agency,
                    state=r.state,
                    ws_pf_amount=r.ws_pf_amount,
                    ws_esic_amount=r.ws_esic_amount,
                    pf_verdict=r.pf.verdict.value,
                    pf_ecr_name=r.pf.ecr_name,
                    pf_ecr_amount=r.pf.ecr_amount,
                    pf_amount_diff=r.pf.amount_diff,
                    pf_name_score=r.pf.name_score,
                    pf_reason=r.pf.reason,
                    esic_verdict=r.esic.verdict.value,
                    esic_ecr_name=r.esic.ecr_name,
                    esic_ecr_amount=r.esic.ecr_amount,
                    esic_amount_diff=r.esic.amount_diff,
                    esic_name_score=r.esic.name_score,
                    esic_reason=r.esic.reason,
                )
            )

        pf_counts = Counter(r.pf.verdict.value for r in results)
        esic_counts = Counter(r.esic.verdict.value for r in results)

        verification.employee_count = len(results)
        verification.pf_matched = pf_counts.get("MATCHED", 0)
        verification.pf_name_mismatch = pf_counts.get("NAME_MISMATCH", 0)
        verification.pf_amount_mismatch = pf_counts.get("AMOUNT_MISMATCH", 0)
        verification.pf_missing = pf_counts.get("MISSING", 0)
        verification.pf_parse_error = pf_counts.get("PARSE_ERROR", 0)
        verification.esic_matched = esic_counts.get("MATCHED", 0)
        verification.esic_name_mismatch = esic_counts.get("NAME_MISMATCH", 0)
        verification.esic_amount_mismatch = esic_counts.get("AMOUNT_MISMATCH", 0)
        verification.esic_missing = esic_counts.get("MISSING", 0)
        verification.esic_parse_error = esic_counts.get("PARSE_ERROR", 0)
        verification.parse_warnings = json.dumps(ws_warnings + pf_warnings + esic_warnings)
        verification.status = "completed"
        verification.completed_at = datetime.now(UTC)
        db.commit()

        ws_uans = {e.uan for e in employees if e.uan}
        ws_ips = {e.ip_number for e in employees if e.ip_number}
        pf_unmatched = [r for r in pf_records if r.uan not in ws_uans]
        esic_unmatched = [r for r in esic_records if r.ip_number not in ws_ips]

        export_dir = data_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        write_verification_report(
            results, pf_unmatched, esic_unmatched, str(export_path(data_dir, verification_id))
        )

        with open(unmatched_path(data_dir, verification_id), "w") as f:
            json.dump(
                {
                    "pf_unmatched": [r.model_dump() for r in pf_unmatched],
                    "esic_unmatched": [r.model_dump() for r in esic_unmatched],
                },
                f,
            )

    except Exception as exc:
        logger.exception("Verification %s failed", verification_id)
        db.rollback()
        verification = db.get(VerificationRecord, verification_id)
        if verification is not None:
            verification.status = "failed"
            verification.error_message = str(exc)
            db.commit()
    finally:
        db.close()
