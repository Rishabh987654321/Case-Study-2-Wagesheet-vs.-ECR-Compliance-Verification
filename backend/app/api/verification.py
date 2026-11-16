import csv
import io
import json
from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import (
    AlreadyProcessingError,
    InvalidFileError,
    NotFoundError,
    ProcessingError,
)
from app.models import EmployeeRecord, VerificationRecord
from app.schemas import (
    EmployeeESICResult,
    EmployeeItem,
    EmployeePFResult,
    PaginatedResponse,
    Summary,
    UnmatchedESICRecord,
    UnmatchedPFRecord,
    UnmatchedResponse,
    VerdictCounts,
    VerificationCreateResponse,
    VerificationDetail,
    VerificationListItem,
)
from app.services import storage
from app.services.processor import export_path, process_verification, unmatched_path

router = APIRouter(tags=["verification"])

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


def _require_completed(verification: VerificationRecord) -> None:
    if verification.status == "failed":
        raise ProcessingError(verification.error_message or "Verification processing failed")
    if verification.status != "completed":
        raise AlreadyProcessingError("Verification is still processing")


def _to_summary(v: VerificationRecord) -> Summary:
    return Summary(
        pf=VerdictCounts(
            matched=v.pf_matched,
            name_mismatch=v.pf_name_mismatch,
            amount_mismatch=v.pf_amount_mismatch,
            missing=v.pf_missing,
            parse_error=v.pf_parse_error,
        ),
        esic=VerdictCounts(
            matched=v.esic_matched,
            name_mismatch=v.esic_name_mismatch,
            amount_mismatch=v.esic_amount_mismatch,
            missing=v.esic_missing,
            parse_error=v.esic_parse_error,
        ),
    )


def _to_detail(v: VerificationRecord) -> VerificationDetail:
    return VerificationDetail(
        id=v.id,
        name=v.name,
        status=v.status,
        wagesheet_filename=v.wagesheet_filename,
        pf_ecr_filename=v.pf_ecr_filename,
        esic_ecr_filename=v.esic_ecr_filename,
        employee_count=v.employee_count,
        summary=_to_summary(v),
        parse_warnings=json.loads(v.parse_warnings) if v.parse_warnings else [],
        created_at=v.created_at,
        completed_at=v.completed_at,
        error_message=v.error_message,
    )


def _to_employee_item(e: EmployeeRecord) -> EmployeeItem:
    return EmployeeItem(
        id=e.id,
        row_number=e.row_number,
        name=e.name,
        uan=e.uan,
        ip_number=e.ip_number,
        agency=e.agency,
        state=e.state,
        pf=EmployeePFResult(
            ws_amount=e.ws_pf_amount,
            ecr_name=e.pf_ecr_name,
            ecr_amount=e.pf_ecr_amount,
            amount_diff=e.pf_amount_diff,
            name_score=e.pf_name_score,
            verdict=e.pf_verdict,
            reason=e.pf_reason,
        ),
        esic=EmployeeESICResult(
            ws_amount=e.ws_esic_amount,
            ecr_name=e.esic_ecr_name,
            ecr_amount=e.esic_ecr_amount,
            amount_diff=e.esic_amount_diff,
            name_score=e.esic_name_score,
            verdict=e.esic_verdict,
            reason=e.esic_reason,
        ),
    )


def _get_verification_or_404(db: Session, verification_id: str) -> VerificationRecord:
    verification = db.get(VerificationRecord, verification_id)
    if verification is None:
        raise NotFoundError(f"Verification {verification_id} not found")
    return verification


@router.post("/verify", response_model=VerificationCreateResponse, status_code=201)
async def create_verification(
    background_tasks: BackgroundTasks,
    wagesheet: UploadFile | None = File(None),
    pf_ecr: UploadFile | None = File(None),
    esic_ecr: UploadFile | None = File(None),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
) -> VerificationCreateResponse:
    if wagesheet is None or pf_ecr is None or esic_ecr is None:
        raise InvalidFileError("All three files (wagesheet, pf_ecr, esic_ecr) are required")

    storage.validate_extension(wagesheet.filename, "wagesheet")
    storage.validate_extension(pf_ecr.filename, "pf_ecr")
    storage.validate_extension(esic_ecr.filename, "esic_ecr")

    settings = get_settings()
    data_dir = Path(settings.data_dir)
    verification_id = uuid4().hex

    try:
        await storage.save_upload(data_dir, verification_id, "wagesheet", wagesheet, settings.max_file_mb)
        await storage.save_upload(data_dir, verification_id, "pf_ecr", pf_ecr, settings.max_file_mb)
        await storage.save_upload(data_dir, verification_id, "esic_ecr", esic_ecr, settings.max_file_mb)
    except Exception:
        storage.delete_verification_files(data_dir, verification_id)
        raise

    verification = VerificationRecord(
        id=verification_id,
        name=name,
        status="processing",
        wagesheet_filename=wagesheet.filename,
        pf_ecr_filename=pf_ecr.filename,
        esic_ecr_filename=esic_ecr.filename,
        created_at=datetime.now(UTC),
    )
    db.add(verification)
    db.commit()

    background_tasks.add_task(process_verification, verification_id)

    return VerificationCreateResponse(
        verification_id=verification_id,
        status="processing",
        message="Verification started. 3 files uploaded.",
    )


@router.get("/verify/{verification_id}", response_model=VerificationDetail)
def get_verification(verification_id: str, db: Session = Depends(get_db)) -> VerificationDetail:
    verification = _get_verification_or_404(db, verification_id)
    return _to_detail(verification)


@router.get("/verify/{verification_id}/employees", response_model=PaginatedResponse[EmployeeItem])
def list_employees(
    verification_id: str,
    pf_verdict: str | None = None,
    esic_verdict: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> PaginatedResponse[EmployeeItem]:
    _get_verification_or_404(db, verification_id)

    query = db.query(EmployeeRecord).filter(EmployeeRecord.verification_id == verification_id)
    if pf_verdict:
        query = query.filter(EmployeeRecord.pf_verdict == pf_verdict)
    if esic_verdict:
        query = query.filter(EmployeeRecord.esic_verdict == esic_verdict)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                EmployeeRecord.name.ilike(like),
                EmployeeRecord.uan.ilike(like),
                EmployeeRecord.ip_number.ilike(like),
            )
        )

    total = query.count()
    rows = (
        query.order_by(EmployeeRecord.row_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = ceil(total / page_size) if total else 0

    return PaginatedResponse[EmployeeItem](
        items=[_to_employee_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/verify/{verification_id}/export", response_model=None)
def export_verification(
    verification_id: str, format: str = Query("xlsx"), db: Session = Depends(get_db)
) -> FileResponse | StreamingResponse:
    if format not in ("xlsx", "csv"):
        raise InvalidFileError("format must be 'xlsx' or 'csv'")

    verification = _get_verification_or_404(db, verification_id)
    _require_completed(verification)

    settings = get_settings()
    data_dir = Path(settings.data_dir)

    if format == "xlsx":
        path = export_path(data_dir, verification_id)
        if not path.exists():
            raise ProcessingError("Export file not found")
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"verification_{verification_id}.xlsx",
        )

    rows = (
        db.query(EmployeeRecord)
        .filter(EmployeeRecord.verification_id == verification_id)
        .order_by(EmployeeRecord.row_number)
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_DETAIL_HEADERS)
    for i, e in enumerate(rows, start=1):
        writer.writerow(
            [
                i,
                e.name,
                e.uan,
                e.ip_number,
                e.agency,
                e.state,
                e.ws_pf_amount,
                e.pf_ecr_name,
                e.pf_ecr_amount,
                e.pf_amount_diff,
                e.pf_name_score,
                e.pf_verdict,
                e.pf_reason,
                e.ws_esic_amount,
                e.esic_ecr_name,
                e.esic_ecr_amount,
                e.esic_amount_diff,
                e.esic_name_score,
                e.esic_verdict,
                e.esic_reason,
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=verification_{verification_id}.csv"},
    )


@router.get("/verify/{verification_id}/unmatched", response_model=UnmatchedResponse)
def get_unmatched(verification_id: str, db: Session = Depends(get_db)) -> UnmatchedResponse:
    verification = _get_verification_or_404(db, verification_id)
    _require_completed(verification)

    settings = get_settings()
    data_dir = Path(settings.data_dir)
    path = unmatched_path(data_dir, verification_id)
    if not path.exists():
        return UnmatchedResponse(pf_unmatched=[], esic_unmatched=[])

    with open(path) as f:
        payload = json.load(f)

    return UnmatchedResponse(
        pf_unmatched=[UnmatchedPFRecord(**r) for r in payload.get("pf_unmatched", [])],
        esic_unmatched=[UnmatchedESICRecord(**r) for r in payload.get("esic_unmatched", [])],
    )


@router.get("/verifications", response_model=PaginatedResponse[VerificationListItem])
def list_verifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PaginatedResponse[VerificationListItem]:
    query = db.query(VerificationRecord).order_by(VerificationRecord.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = ceil(total / page_size) if total else 0

    return PaginatedResponse[VerificationListItem](
        items=[
            VerificationListItem(
                id=v.id, name=v.name, status=v.status, employee_count=v.employee_count, created_at=v.created_at
            )
            for v in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.delete("/verify/{verification_id}", status_code=204)
def delete_verification(verification_id: str, db: Session = Depends(get_db)) -> None:
    verification = _get_verification_or_404(db, verification_id)
    db.delete(verification)
    db.commit()

    settings = get_settings()
    storage.delete_verification_files(Path(settings.data_dir), verification_id)
