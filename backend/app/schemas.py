from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ExportFormat(str, Enum):
    XLSX = "xlsx"
    CSV = "csv"


class VerificationCreate(BaseModel):
    name: str | None = None


class VerificationCreateResponse(BaseModel):
    verification_id: str
    status: str
    message: str


class VerdictCounts(BaseModel):
    matched: int = 0
    name_mismatch: int = 0
    amount_mismatch: int = 0
    missing: int = 0
    parse_error: int = 0


class Summary(BaseModel):
    pf: VerdictCounts
    esic: VerdictCounts


class VerificationDetail(BaseModel):
    id: str
    name: str | None
    status: str
    wagesheet_filename: str | None
    pf_ecr_filename: str | None
    esic_ecr_filename: str | None
    employee_count: int
    summary: Summary
    parse_warnings: list[str]
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None = None


class VerificationListItem(BaseModel):
    id: str
    name: str | None
    status: str
    employee_count: int
    created_at: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class EmployeePFResult(BaseModel):
    ws_amount: float | None
    ecr_name: str | None
    ecr_amount: float | None
    amount_diff: float | None
    name_score: float | None
    verdict: str
    reason: str


class EmployeeESICResult(BaseModel):
    ws_amount: float | None
    ecr_name: str | None
    ecr_amount: float | None
    amount_diff: float | None
    name_score: float | None
    verdict: str
    reason: str


class EmployeeItem(BaseModel):
    id: str
    row_number: int
    name: str
    uan: str | None
    ip_number: str | None
    agency: str | None
    state: str | None
    pf: EmployeePFResult
    esic: EmployeeESICResult


class UnmatchedPFRecord(BaseModel):
    uan: str
    name: str
    ee_share: float


class UnmatchedESICRecord(BaseModel):
    ip_number: str
    name: str
    ip_contribution: float


class UnmatchedResponse(BaseModel):
    pf_unmatched: list[UnmatchedPFRecord]
    esic_unmatched: list[UnmatchedESICRecord]


class ConfigResponse(BaseModel):
    max_file_mb: int
    name_match_threshold: int
    name_review_threshold: int
    amount_tolerance: float


class ErrorResponse(BaseModel):
    error: str
    detail: str
