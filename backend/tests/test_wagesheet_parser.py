from pathlib import Path

import openpyxl
import pytest

from app.pipeline.wagesheet_parser import parse_wagesheet

SAMPLE = Path(__file__).resolve().parent.parent.parent / "sample_data" / "input" / "Sample_Wagesheet_Aug25.xlsx"


def test_parse_sample_wagesheet_employee_count():
    employees, warnings = parse_wagesheet(str(SAMPLE))
    assert len(employees) == 12
    assert warnings == []


def test_parse_sample_wagesheet_column_mapping():
    employees, _ = parse_wagesheet(str(SAMPLE))
    first = employees[0]
    assert first.name == "ANIL KUMAR"
    assert first.uan == "999912340001"
    assert first.ip_number == "9912340001"
    assert first.agency == "Sample Staffing Pvt. Ltd."
    assert first.state == "Bihar"
    assert first.pf_amount == 1622.0
    assert first.esic_amount == 102.0
    assert first.name_normalized == "anil kumar"


def test_parse_sample_wagesheet_row_numbers_are_1_based_excel_rows():
    employees, _ = parse_wagesheet(str(SAMPLE))
    assert employees[0].row_number == 2  # header is row 1
    assert employees[-1].row_number == 13


def test_uan_stored_as_scientific_notation_float_is_normalized(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "UAN", "IP Number", "Agency", "State", "ESIC @ 0.75%", "PF @ 12%"])
    ws.append(["TEST PERSON", 999912340099, 9912340099, "Agency X", "Delhi", 50, 800])
    path = tmp_path / "wagesheet.xlsx"
    wb.save(path)

    employees, _ = parse_wagesheet(str(path))
    assert len(employees) == 1
    assert employees[0].uan == "999912340099"
    assert employees[0].ip_number == "9912340099"


def test_missing_identifier_columns_still_parses_name(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "UAN"])
    ws.append(["NO IP PERSON", "999900000001"])
    path = tmp_path / "wagesheet.xlsx"
    wb.save(path)

    employees, _ = parse_wagesheet(str(path))
    assert len(employees) == 1
    assert employees[0].uan == "999900000001"
    assert employees[0].ip_number is None


def test_blank_rows_and_total_rows_are_skipped(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "UAN", "IP Number", "Agency", "State", "ESIC @ 0.75%", "PF @ 12%"])
    ws.append(["REAL PERSON", "999900000001", "9900000001", "Agency X", "Delhi", 50, 800])
    ws.append([None, None, None, None, None, None, None])
    ws.append(["Grand Total", None, None, None, None, 50, 800])
    path = tmp_path / "wagesheet.xlsx"
    wb.save(path)

    employees, _ = parse_wagesheet(str(path))
    assert len(employees) == 1
    assert employees[0].name == "REAL PERSON"


def test_duplicate_uan_produces_warning(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "UAN", "IP Number", "Agency", "State", "ESIC @ 0.75%", "PF @ 12%"])
    ws.append(["PERSON A", "999900000001", "9900000001", "Agency X", "Delhi", 50, 800])
    ws.append(["PERSON B", "999900000001", "9900000002", "Agency X", "Delhi", 60, 900])
    path = tmp_path / "wagesheet.xlsx"
    wb.save(path)

    employees, warnings = parse_wagesheet(str(path))
    assert len(employees) == 2
    assert any("duplicate UAN" in w for w in warnings)


def test_empty_workbook_returns_empty_with_warning(tmp_path):
    wb = openpyxl.Workbook()
    path = tmp_path / "empty.xlsx"
    wb.save(path)

    employees, warnings = parse_wagesheet(str(path))
    assert employees == []
    assert warnings  # some warning explaining why


def test_corrupt_or_empty_file_raises_clean_error(tmp_path):
    bad = tmp_path / "corrupt.xlsx"
    bad.write_bytes(b"not a real xlsx file")
    with pytest.raises(ValueError, match="Could not read the wagesheet"):
        parse_wagesheet(str(bad))

    empty = tmp_path / "empty.xlsx"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="Could not read the wagesheet"):
        parse_wagesheet(str(empty))


def test_header_not_found_raises(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Foo", "Bar", "Baz"])
    ws.append([1, 2, 3])
    path = tmp_path / "no_header.xlsx"
    wb.save(path)

    with pytest.raises(ValueError):
        parse_wagesheet(str(path))


def test_amount_with_currency_symbol_and_commas_is_parsed(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "UAN", "IP Number", "Agency", "State", "ESIC @ 0.75%", "PF @ 12%"])
    ws.append(["PERSON A", "999900000001", "9900000001", "Agency X", "Delhi", "₹1,250.50", "1,800"])
    path = tmp_path / "wagesheet.xlsx"
    wb.save(path)

    employees, warnings = parse_wagesheet(str(path))
    assert employees[0].esic_amount == 1250.50
    assert employees[0].pf_amount == 1800.0
    assert warnings == []
