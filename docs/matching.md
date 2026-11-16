# Name Matching Strategy

## The Problem
Indian payroll documents have inconsistent name formatting:
- **Spelling variations:** RAJESH KUMAR vs RAJSH KUMR
- **Word order:** KUMAR RAJESH vs RAJESH KUMAR
- **Titles/honorifics:** MR. RAJESH KUMAR, SHRI RAJESH, SMT SUNITA
- **Father's name:** RAJESH S/O RAM KUMAR vs RAJESH KUMAR
- **Initials:** R. KUMAR vs RAJESH KUMAR
- **Transliteration:** MOHAMMED vs MUHAMMAD vs MOHD, SUBRAMANIAM vs SUBRAMANIAN

The system must catch genuine mismatches (wrong person entirely) without crying wolf on trivial variations.

## Algorithm

### Step 1: Normalize
```
Input:  "Mr. RAJESH   KUMAR (S/O Ram Kumar)"
  → lowercase:     "mr. rajesh   kumar (s/o ram kumar)"
  → remove titles: "rajesh   kumar (s/o ram kumar)"
  → remove parentheticals: "rajesh   kumar"
  → remove special chars: "rajesh kumar"
  → collapse whitespace: "rajesh kumar"
```

Titles removed: mr, mrs, ms, dr, shri, smt, sh, kumari, late, master

Parenthetical patterns removed: (s/o ...), (d/o ...), (w/o ...), (c/o ...)

### Step 2: Token Sort
Split into tokens, sort alphabetically, rejoin:
```
"kumar rajesh" → tokens: [kumar, rajesh] → sorted: [kumar, rajesh] → "kumar rajesh"
"rajesh kumar" → tokens: [kumar, rajesh] → sorted: [kumar, rajesh] → "kumar rajesh"
```
Both produce the same result → word order no longer matters.

### Step 3: Similarity Score
Use `rapidfuzz.fuzz.token_sort_ratio(name_a, name_b)` which combines steps 2 and 3 internally.

Returns 0–100:
- 100: Exact match after normalization
- 90–99: Minor spelling difference (1–2 chars)
- 70–89: Moderate difference (could be same person with significant variation, or could be different)
- <70: Likely different person

### Step 4: Verdict
```python
if score >= NAME_MATCH_THRESHOLD (default 90):
    # Names match — proceed to amount check
elif score >= NAME_REVIEW_THRESHOLD (default 70):
    # Possible mismatch — flag as NAME_MISMATCH with "review suggested"
else:
    # Definite mismatch
    verdict = NAME_MISMATCH
```

## Configuration

All thresholds are in `.env` / `config.py`:
- `NAME_MATCH_THRESHOLD=90` — decrease to be more lenient (more false matches), increase to be stricter (more false mismatches)
- `NAME_REVIEW_THRESHOLD=70` — the floor below which it's definitely a different person
- `AMOUNT_TOLERANCE=1.0` — ₹1 rounding tolerance

## Edge Cases

| Scenario | Handling |
|---|---|
| Employee has no UAN | PF verdict = MISSING (with reason "No UAN in wagesheet") |
| Employee has no IP Number | ESIC verdict = MISSING (with reason "No IP Number in wagesheet") |
| Duplicate UAN in wagesheet | Process both, warn in parse_warnings |
| Duplicate UAN in ECR | Match to the first occurrence, warn |
| Amount is 0 in wagesheet | Still match — 0 vs 0 is MATCHED, 0 vs non-zero is AMOUNT_MISMATCH |
| Amount column missing from wagesheet | Use available columns, skip the check, note in reason |
| Name is empty in ECR | NAME_MISMATCH with reason "Name empty in ECR" |

## Known Limitations
- Cannot handle completely different names for the same person (e.g., legal name vs nickname)
- Hindi/regional language names in ECR vs English in wagesheet need transliteration — not handled automatically
- Father's name removal is heuristic (S/O, D/O patterns only)
- Very short names (single word, 3-4 chars) may produce high false-match scores
