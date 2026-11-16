from pathlib import Path

from app.pipeline.pf_ecr_parser import _parse_from_text, parse_pf_ecr

SAMPLE = Path(__file__).resolve().parent.parent.parent / "sample_data" / "input" / "PF ECR AUG-25 SAMPLE.pdf"


def test_parse_sample_pf_ecr_record_count():
    records, warnings = parse_pf_ecr(str(SAMPLE))
    assert len(records) == 11
    assert warnings == []  # Total Members header (11) matches parsed count


def test_parse_sample_pf_ecr_uan_and_name():
    records, _ = parse_pf_ecr(str(SAMPLE))
    by_uan = {r.uan: r for r in records}
    assert "999912340001" in by_uan
    assert by_uan["999912340001"].name == "ANIL KUMAR"
    # deliberate name-mismatch test case from the sample data
    assert by_uan["999912340007"].name == "DEVENDRA PRASAD"


def test_parse_sample_pf_ecr_ee_share_amounts():
    records, _ = parse_pf_ecr(str(SAMPLE))
    by_uan = {r.uan: r for r in records}
    assert by_uan["999912340001"].ee_share == 1622.0
    # deliberate amount-mismatch test case (wagesheet says 1654)
    assert by_uan["999912340011"].ee_share == 1354.0


def test_missing_member_not_in_sample():
    records, _ = parse_pf_ecr(str(SAMPLE))
    uans = {r.uan for r in records}
    assert "999912340009" not in uans  # SANJAY PASWAN deliberately absent


def test_parse_from_text_handles_duplicated_identical_name():
    text = "1 999900000001 ANIL KUMAR ANIL KUMAR 13,520 13,520 13,520 13,520 1,622 1,126 496 0"
    records, warnings = _parse_from_text(text, page_num=1)
    assert len(records) == 1
    assert records[0].uan == "999900000001"
    assert records[0].name == "ANIL KUMAR"
    assert records[0].ee_share == 1622.0
    assert warnings == []


def test_parse_from_text_flags_uneven_name_split():
    # "A B C" can't be split into two equal, identical halves -> flagged, not silently guessed
    text = "1 999900000001 A B C 13,520 13,520 13,520 13,520 1,622 1,126 496 0"
    records, warnings = _parse_from_text(text, page_num=1)
    assert len(records) == 1
    assert len(warnings) == 1
    assert "could not cleanly split" in warnings[0]


def test_parse_from_text_skips_non_member_lines():
    text = (
        "EMPLOYEE'S PROVIDENT FUND ORGANISATION\n"
        "Total Members 1\n"
        "1 999900000001 ANIL KUMAR ANIL KUMAR 13,520 13,520 13,520 13,520 1,622 1,126 496 0\n"
        "DLCPM9999990000 / AUG-2025 / 15-SEP-2025 20:39"
    )
    records, _ = _parse_from_text(text, page_num=1)
    assert len(records) == 1


def test_duplicate_uan_is_deduped_with_warning(tmp_path, monkeypatch):
    # Exercise the dedupe path in parse_pf_ecr by monkeypatching the per-page parse step.
    import app.pipeline.pf_ecr_parser as mod

    class FakePage:
        def extract_text(self):
            return "Total Members 2"

        def extract_tables(self):
            return []

    class FakePDF:
        def __init__(self):
            self.pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_parse_from_text(text, page_num):
        from app.pipeline.types import PFECRRecord

        return (
            [
                PFECRRecord(uan="1", name="A", name_normalized="a", ee_share=1.0),
                PFECRRecord(uan="1", name="A DUP", name_normalized="a dup", ee_share=2.0),
            ],
            [],
        )

    monkeypatch.setattr(mod.pdfplumber, "open", lambda path: FakePDF())
    monkeypatch.setattr(mod, "_parse_from_text", fake_parse_from_text)

    records, warnings = parse_pf_ecr("fake.pdf")
    assert len(records) == 1
    assert any("Duplicate UAN" in w for w in warnings)


def test_corrupt_pdf_returns_empty_with_warning(tmp_path):
    bad_pdf = tmp_path / "corrupt.pdf"
    bad_pdf.write_bytes(b"not a real pdf")
    records, warnings = parse_pf_ecr(str(bad_pdf))
    assert records == []
    assert warnings
    assert "Could not open" in warnings[0]
