from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VerificationRecord(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="uploading")  # uploading|processing|completed|failed

    wagesheet_filename: Mapped[str | None] = mapped_column(default=None)
    pf_ecr_filename: Mapped[str | None] = mapped_column(default=None)
    esic_ecr_filename: Mapped[str | None] = mapped_column(default=None)

    employee_count: Mapped[int] = mapped_column(default=0)

    pf_matched: Mapped[int] = mapped_column(default=0)
    pf_name_mismatch: Mapped[int] = mapped_column(default=0)
    pf_amount_mismatch: Mapped[int] = mapped_column(default=0)
    pf_missing: Mapped[int] = mapped_column(default=0)
    pf_parse_error: Mapped[int] = mapped_column(default=0)

    esic_matched: Mapped[int] = mapped_column(default=0)
    esic_name_mismatch: Mapped[int] = mapped_column(default=0)
    esic_amount_mismatch: Mapped[int] = mapped_column(default=0)
    esic_missing: Mapped[int] = mapped_column(default=0)
    esic_parse_error: Mapped[int] = mapped_column(default=0)

    parse_warnings: Mapped[str | None] = mapped_column(default=None)  # JSON array string
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)

    employees: Mapped[list["EmployeeRecord"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )


class EmployeeRecord(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(primary_key=True)
    verification_id: Mapped[str] = mapped_column(ForeignKey("verifications.id", ondelete="CASCADE"))

    row_number: Mapped[int]
    name: Mapped[str]
    name_normalized: Mapped[str]
    uan: Mapped[str | None] = mapped_column(default=None)
    ip_number: Mapped[str | None] = mapped_column(default=None)
    agency: Mapped[str | None] = mapped_column(default=None)
    state: Mapped[str | None] = mapped_column(default=None)

    ws_pf_amount: Mapped[float | None] = mapped_column(default=None)
    ws_esic_amount: Mapped[float | None] = mapped_column(default=None)

    pf_verdict: Mapped[str]
    pf_ecr_name: Mapped[str | None] = mapped_column(default=None)
    pf_ecr_amount: Mapped[float | None] = mapped_column(default=None)
    pf_amount_diff: Mapped[float | None] = mapped_column(default=None)
    pf_name_score: Mapped[float | None] = mapped_column(default=None)
    pf_reason: Mapped[str]

    esic_verdict: Mapped[str]
    esic_ecr_name: Mapped[str | None] = mapped_column(default=None)
    esic_ecr_amount: Mapped[float | None] = mapped_column(default=None)
    esic_amount_diff: Mapped[float | None] = mapped_column(default=None)
    esic_name_score: Mapped[float | None] = mapped_column(default=None)
    esic_reason: Mapped[str]

    verification: Mapped["VerificationRecord"] = relationship(back_populates="employees")
