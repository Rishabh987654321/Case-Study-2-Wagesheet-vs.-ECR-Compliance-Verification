from app.config import Settings, get_settings
from app.pipeline.name_matcher import classify_name_match, match_names
from app.pipeline.types import (
    EmployeeVerification,
    ESICECRRecord,
    PFECRRecord,
    Verdict,
    VerificationResult,
    WagesheetEmployee,
)


def _verify_one(
    *,
    identifier: str | None,
    id_label: str,
    doc_label: str,
    ws_name: str,
    ws_amount: float | None,
    ecr_lookup: dict[str, tuple[str, float]],
    settings: Settings,
) -> VerificationResult:
    if not identifier:
        return VerificationResult(verdict=Verdict.MISSING, reason=f"No {id_label} in wagesheet")

    rec = ecr_lookup.get(identifier)
    if rec is None:
        return VerificationResult(
            verdict=Verdict.MISSING, reason=f"{id_label} {identifier} not found in {doc_label}"
        )

    ecr_name, ecr_amount = rec
    if not ecr_name or not ecr_name.strip():
        return VerificationResult(
            verdict=Verdict.NAME_MISMATCH,
            ecr_name=ecr_name,
            ecr_amount=ecr_amount,
            name_score=0.0,
            reason="Name empty in ECR",
        )

    score = match_names(ws_name, ecr_name)
    classification = classify_name_match(score, settings.name_match_threshold, settings.name_review_threshold)
    if classification in ("mismatch", "review"):
        prefix = "Possible name mismatch (review suggested)" if classification == "review" else "Name mismatch"
        return VerificationResult(
            verdict=Verdict.NAME_MISMATCH,
            ecr_name=ecr_name,
            ecr_amount=ecr_amount,
            name_score=round(score, 1),
            reason=f"{prefix}: '{ws_name}' vs '{ecr_name}' (score: {score:.1f})",
        )

    if ws_amount is None:
        return VerificationResult(
            verdict=Verdict.MATCHED,
            ecr_name=ecr_name,
            ecr_amount=ecr_amount,
            name_score=round(score, 1),
            reason=f"Identifier found, name matches ({score:.1f}%), wagesheet amount column "
            "missing — amount check skipped",
        )

    diff = round(ecr_amount - ws_amount, 2)
    if abs(diff) > settings.amount_tolerance:
        return VerificationResult(
            verdict=Verdict.AMOUNT_MISMATCH,
            ecr_name=ecr_name,
            ecr_amount=ecr_amount,
            amount_diff=diff,
            name_score=round(score, 1),
            reason=f"Amount mismatch: wagesheet ₹{ws_amount:.2f} vs ECR ₹{ecr_amount:.2f} (diff: ₹{diff:.2f})",
        )

    return VerificationResult(
        verdict=Verdict.MATCHED,
        ecr_name=ecr_name,
        ecr_amount=ecr_amount,
        name_score=round(score, 1),
        reason=f"Identifier found, name matches ({score:.1f}%), amount matches",
    )


def verify_employees(
    employees: list[WagesheetEmployee],
    pf_records: list[PFECRRecord],
    esic_records: list[ESICECRRecord],
    settings: Settings | None = None,
) -> list[EmployeeVerification]:
    """For each wagesheet employee, look up UAN in PF ECR and IP Number in ESIC ECR,
    then check name + amount. Returns one EmployeeVerification per wagesheet row."""
    settings = settings or get_settings()

    pf_by_uan: dict[str, tuple[str, float]] = {}
    for r in pf_records:
        pf_by_uan.setdefault(r.uan, (r.name, r.ee_share))

    esic_by_ip: dict[str, tuple[str, float]] = {}
    for r in esic_records:
        esic_by_ip.setdefault(r.ip_number, (r.name, r.ip_contribution))

    results: list[EmployeeVerification] = []
    for emp in employees:
        pf_result = _verify_one(
            identifier=emp.uan,
            id_label="UAN",
            doc_label="PF ECR",
            ws_name=emp.name,
            ws_amount=emp.pf_amount,
            ecr_lookup=pf_by_uan,
            settings=settings,
        )
        esic_result = _verify_one(
            identifier=emp.ip_number,
            id_label="IP Number",
            doc_label="ESIC ECR",
            ws_name=emp.name,
            ws_amount=emp.esic_amount,
            ecr_lookup=esic_by_ip,
            settings=settings,
        )
        results.append(
            EmployeeVerification(
                row_number=emp.row_number,
                name=emp.name,
                uan=emp.uan,
                ip_number=emp.ip_number,
                agency=emp.agency,
                state=emp.state,
                ws_pf_amount=emp.pf_amount,
                ws_esic_amount=emp.esic_amount,
                pf=pf_result,
                esic=esic_result,
            )
        )
    return results
