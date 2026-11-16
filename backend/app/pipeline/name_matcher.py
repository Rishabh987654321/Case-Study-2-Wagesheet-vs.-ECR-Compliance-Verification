import re

from rapidfuzz import fuzz

_TITLES = r"mr|mrs|ms|dr|shri|smt|sh|kumari|late|master"
_TITLE_RE = re.compile(rf"\b(?:{_TITLES})\.?\b")
_PATRONYMIC_RE = re.compile(r"\(?\b(?:s/o|d/o|w/o|c/o)\b[^)]*\)?")
_NON_LETTER_RE = re.compile(r"[^a-z\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(name: str | None) -> str:
    """Lowercase, strip titles/patronymic clauses/special chars, collapse whitespace."""
    if not name:
        return ""
    text = name.lower()
    text = _PATRONYMIC_RE.sub(" ", text)
    text = _TITLE_RE.sub(" ", text)
    text = _NON_LETTER_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def match_names(name_a: str | None, name_b: str | None) -> float:
    """Similarity score 0-100 using token_sort_ratio on normalized names."""
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    if not norm_a or not norm_b:
        return 0.0
    return fuzz.token_sort_ratio(norm_a, norm_b)


def classify_name_match(score: float, threshold: int = 90, review_threshold: int = 70) -> str:
    """Returns "match", "review", or "mismatch" based on configured thresholds."""
    if score >= threshold:
        return "match"
    if score >= review_threshold:
        return "review"
    return "mismatch"
