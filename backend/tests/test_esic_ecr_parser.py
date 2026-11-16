from pathlib import Path

from app.pipeline.esic_ecr_parser import _parse_from_text, parse_esic_ecr

SAMPLE = Path(__file__).resolve().parent.parent.parent / "sample_data" / "input" / "ESIC ECR AUG-25 SAMPLE.pdf"


def test_parse_sample_esic_ecr_record_count():
    records, warnings = parse_esic_ecr(str(SAMPLE))
    assert len(records) == 10
    assert warnings == []  # Total IP Contribution header sum matches parsed sum


def test_parse_sample_esic_ecr_ip_number_and_name():
    records, _ = parse_esic_ecr(str(SAMPLE))
    by_ip = {r.ip_number: r for r in records}
    assert "9912340001" in by_ip
    assert by_ip["9912340001"].name == "ANIL KUMAR"
    # deliberate name-mismatch test case from the sample data
    assert by_ip["9912340008"].name == "RENU SHARMA"


def test_parse_sample_esic_ecr_contribution_amounts():
    records, _ = parse_esic_ecr(str(SAMPLE))
    by_ip = {r.ip_number: r for r in records}
    assert by_ip["9912340001"].ip_contribution == 102.0
    # deliberate amount-mismatch test case (wagesheet says 86)
    assert by_ip["9912340012"].ip_contribution == 66.0


def test_missing_members_not_in_sample():
    records, _ = parse_esic_ecr(str(SAMPLE))
    ips = {r.ip_number for r in records}
    assert "9912340009" not in ips  # SANJAY PASWAN deliberately absent
    assert "9912340010" not in ips  # POOJA GUPTA deliberately absent (ESIC only)


def test_parse_from_text_single_row():
    text = "1 - 9912340001 ANIL KUMAR 31 13520.00 102.00 -"
    records, warnings = _parse_from_text(text)
    assert len(records) == 1
    assert records[0].ip_number == "9912340001"
    assert records[0].name == "ANIL KUMAR"
    assert records[0].ip_contribution == 102.0
    assert warnings == []


def test_parse_from_text_skips_header_and_footer_lines():
    text = (
        "Employees' State Insurance Corporation\n"
        "SNo. Is Disable IP Number IP Name No. Of Days Total Wages IP Contribution Reason\n"
        "1 - 9912340001 ANIL KUMAR 31 13520.00 102.00 -\n"
        "Page 1 of 1 Printed On: 9/12/2025 18:08:28"
    )
    records, _ = _parse_from_text(text)
    assert len(records) == 1


def test_duplicate_ip_number_is_deduped_with_warning(monkeypatch):
    import app.pipeline.esic_ecr_parser as mod

    class FakePage:
        def extract_text(self):
            return ""

        def extract_tables(self):
            return []

    class FakePDF:
        def __init__(self):
            self.pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_parse_from_text(text):
        from app.pipeline.types import ESICECRRecord

        return (
            [
                ESICECRRecord(ip_number="1", name="A", name_normalized="a", ip_contribution=1.0),
                ESICECRRecord(ip_number="1", name="A DUP", name_normalized="a dup", ip_contribution=2.0),
            ],
            [],
        )

    monkeypatch.setattr(mod.pdfplumber, "open", lambda path: FakePDF())
    monkeypatch.setattr(mod, "_parse_from_text", fake_parse_from_text)

    records, warnings = parse_esic_ecr("fake.pdf")
    assert len(records) == 1
    assert any("Duplicate IP Number" in w for w in warnings)


def test_corrupt_pdf_returns_empty_with_warning(tmp_path):
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_bytes(b"not a real pdf")
    records, warnings = parse_esic_ecr(str(bad_pdf))
    assert records == []
    assert warnings
    assert "Could not open" in warnings[0]
