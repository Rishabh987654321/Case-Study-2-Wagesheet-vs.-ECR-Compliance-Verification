from enum import Enum

from pydantic import BaseModel


class Verdict(str, Enum):
    MATCHED = "MATCHED"
    NAME_MISMATCH = "NAME_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING = "MISSING"
    PARSE_ERROR = "PARSE_ERROR"


class WagesheetEmployee(BaseModel):
    row_number: int
    name: str
    name_normalized: str
    uan: str | None
    ip_number: str | None
    agency: str | None
    state: str | None
    pf_amount: float | None
    esic_amount: float | None


class PFECRRecord(BaseModel):
    uan: str
    name: str
    name_normalized: str
    ee_share: float


class ESICECRRecord(BaseModel):
    ip_number: str
    name: str
    name_normalized: str
    ip_contribution: float


class VerificationResult(BaseModel):
    verdict: Verdict
    ecr_name: str | None = None
    ecr_amount: float | None = None
    amount_diff: float | None = None
    name_score: float | None = None
    reason: str


class EmployeeVerification(BaseModel):
    row_number: int
    name: str
    uan: str | None
    ip_number: str | None
    agency: str | None
    state: str | None
    ws_pf_amount: float | None
    ws_esic_amount: float | None
    pf: VerificationResult
    esic: VerificationResult
