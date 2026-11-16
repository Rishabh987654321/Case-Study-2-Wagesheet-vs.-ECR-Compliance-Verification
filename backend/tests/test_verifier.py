from app.config import Settings
from app.pipeline.types import ESICECRRecord, PFECRRecord, Verdict, WagesheetEmployee
from app.pipeline.verifier import verify_employees


def make_employee(**overrides):
    defaults = {
        "row_number": 1,
        "name": "RAJESH KUMAR",
        "name_normalized": "rajesh kumar",
        "uan": "999900000001",
        "ip_number": "9900000001",
        "agency": "Agency X",
        "state": "Delhi",
        "pf_amount": 1200.0,
        "esic_amount": 75.0,
    }
    defaults.update(overrides)
    return WagesheetEmployee(**defaults)


def make_settings(**overrides):
    defaults = {"name_match_threshold": 90, "name_review_threshold": 70, "amount_tolerance": 1.0}
    defaults.update(overrides)
    return Settings(**defaults)


def test_matched_case():
    emp = make_employee()
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1200.0)]
    esic = [
        ESICECRRecord(ip_number="9900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ip_contribution=75.0)
    ]
    result = verify_employees([emp], pf, esic, make_settings())[0]
    assert result.pf.verdict == Verdict.MATCHED
    assert result.esic.verdict == Verdict.MATCHED
    assert result.pf.name_score == 100.0
    assert "name matches" in result.pf.reason


def test_name_mismatch_case():
    emp = make_employee()
    pf = [PFECRRecord(uan="999900000001", name="SUNIL SHARMA", name_normalized="sunil sharma", ee_share=1200.0)]
    esic = []
    result = verify_employees([emp], pf, esic, make_settings())[0]
    assert result.pf.verdict == Verdict.NAME_MISMATCH
    assert result.pf.ecr_name == "SUNIL SHARMA"
    assert result.pf.name_score < 70
    assert "Name mismatch" in result.pf.reason


def test_name_review_band_is_name_mismatch():
    emp = make_employee(name="REKHA SHARMA")
    pf = []
    esic = [
        ESICECRRecord(ip_number="9900000001", name="RENU SHARMA", name_normalized="renu sharma", ip_contribution=75.0)
    ]
    result = verify_employees([emp], pf, esic, make_settings())[0]
    assert result.esic.verdict == Verdict.NAME_MISMATCH
    assert 70 <= result.esic.name_score < 90
    assert "review suggested" in result.esic.reason


def test_amount_mismatch_case():
    emp = make_employee(pf_amount=1200.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1350.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.AMOUNT_MISMATCH
    assert result.pf.amount_diff == 150.0
    assert "Amount mismatch" in result.pf.reason


def test_missing_case_identifier_not_in_ecr():
    emp = make_employee(uan="999900000099")
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1200.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.MISSING
    assert "not found in PF ECR" in result.pf.reason


def test_employee_with_no_uan_is_pf_missing():
    emp = make_employee(uan=None)
    result = verify_employees([emp], [], [], make_settings())[0]
    assert result.pf.verdict == Verdict.MISSING
    assert result.pf.reason == "No UAN in wagesheet"


def test_employee_with_no_ip_number_is_esic_missing():
    emp = make_employee(ip_number=None)
    result = verify_employees([emp], [], [], make_settings())[0]
    assert result.esic.verdict == Verdict.MISSING
    assert result.esic.reason == "No IP Number in wagesheet"


def test_amount_within_tolerance_is_matched():
    emp = make_employee(pf_amount=1200.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1200.9)]
    result = verify_employees([emp], pf, [], make_settings(amount_tolerance=1.0))[0]
    assert result.pf.verdict == Verdict.MATCHED


def test_amount_just_outside_tolerance_is_mismatch():
    emp = make_employee(pf_amount=1200.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1201.1)]
    result = verify_employees([emp], pf, [], make_settings(amount_tolerance=1.0))[0]
    assert result.pf.verdict == Verdict.AMOUNT_MISMATCH


def test_zero_amount_both_sides_is_matched():
    emp = make_employee(pf_amount=0.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=0.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.MATCHED


def test_zero_amount_wagesheet_nonzero_ecr_is_mismatch():
    emp = make_employee(pf_amount=0.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=500.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.AMOUNT_MISMATCH


def test_missing_wagesheet_amount_skips_amount_check():
    emp = make_employee(pf_amount=None)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=500.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.MATCHED
    assert "amount check skipped" in result.pf.reason


def test_empty_ecr_name_is_name_mismatch():
    emp = make_employee()
    pf = [PFECRRecord(uan="999900000001", name="", name_normalized="", ee_share=1200.0)]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.NAME_MISMATCH
    assert result.pf.reason == "Name empty in ECR"


def test_duplicate_ecr_uan_matches_first_occurrence():
    emp = make_employee()
    pf = [
        PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1200.0),
        PFECRRecord(uan="999900000001", name="SOMEONE ELSE", name_normalized="someone else", ee_share=999.0),
    ]
    result = verify_employees([emp], pf, [], make_settings())[0]
    assert result.pf.verdict == Verdict.MATCHED
    assert result.pf.ecr_name == "RAJESH KUMAR"


def test_pf_and_esic_verdicts_are_independent():
    emp = make_employee(pf_amount=1200.0, esic_amount=75.0)
    pf = [PFECRRecord(uan="999900000001", name="RAJESH KUMAR", name_normalized="rajesh kumar", ee_share=1200.0)]
    esic = [
        ESICECRRecord(ip_number="9900000001", name="WRONG PERSON", name_normalized="wrong person", ip_contribution=75.0)
    ]
    result = verify_employees([emp], pf, esic, make_settings())[0]
    assert result.pf.verdict == Verdict.MATCHED
    assert result.esic.verdict == Verdict.NAME_MISMATCH
