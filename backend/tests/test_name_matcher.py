import pytest

from app.pipeline.name_matcher import classify_name_match, match_names, normalize_name


def test_normalize_lowercases_and_strips_title_and_patronymic():
    assert normalize_name("Mr. RAJESH   KUMAR (S/O Ram Kumar)") == "rajesh kumar"


def test_normalize_patronymic_without_parens():
    assert normalize_name("RAJESH KUMAR S/O RAM") == "rajesh kumar"


def test_normalize_empty_and_none():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_normalize_title_word_boundary_does_not_eat_substrings():
    # "sh" is a title token but must not strip inside "ashok"
    assert normalize_name("ASHOK KUMAR") == "ashok kumar"


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("RAJESH KUMAR", "RAJESH KUMAR", 100.0),
        ("KUMAR RAJESH", "RAJESH KUMAR", 100.0),
        ("MR. RAJESH KUMAR", "RAJESH KUMAR", 100.0),
        ("RAJESH KUMAR S/O RAM", "RAJESH KUMAR", 100.0),
        ("rajesh kumar", "RAJESH KUMAR", 100.0),
    ],
)
def test_match_names_exact_cases(a, b, expected):
    assert match_names(a, b) == expected


def test_match_names_minor_spelling_is_high():
    score = match_names("RAJESH KUMAR", "RAJSH KUMR")
    assert score > 85


def test_match_names_different_person_is_low():
    score = match_names("RAJESH KUMAR", "SUNIL SHARMA")
    assert score < 50


def test_match_names_empty_string_is_zero():
    assert match_names("", "RAJESH") == 0.0
    assert match_names("RAJESH", "") == 0.0
    assert match_names(None, "RAJESH") == 0.0


def test_match_names_initials_is_moderate():
    score = match_names("R KUMAR", "RAJESH KUMAR")
    assert 50 <= score <= 90


def test_match_names_transliteration_is_moderate_high():
    score = match_names("MOHAMMED", "MUHAMMAD")
    assert 60 <= score <= 90


def test_classify_name_match_thresholds():
    assert classify_name_match(95) == "match"
    assert classify_name_match(90) == "match"
    assert classify_name_match(89.9) == "review"
    assert classify_name_match(70) == "review"
    assert classify_name_match(69.9) == "mismatch"
    assert classify_name_match(0) == "mismatch"


def test_classify_name_match_custom_thresholds():
    assert classify_name_match(80, threshold=75, review_threshold=60) == "match"
    assert classify_name_match(65, threshold=75, review_threshold=60) == "review"
    assert classify_name_match(50, threshold=75, review_threshold=60) == "mismatch"
