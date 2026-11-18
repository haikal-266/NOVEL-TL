import re

# Test prototype functions

def smooth_dialogue_tags(text: str) -> str:
    res = text
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berkata\b', r'\1ucapnya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berbisik\b', r'\1bisiknya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+bergumam\b', r'\1gumamnya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+bertanya\b', r'\1tanyanya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berseru\b', r'\1serunya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berteriak\b', r'\1serunya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+mengeluh\b', r'\1keluhnya', res)
    res = re.sub(r'([\"”][,\s]*)\bkata\s+(?:dia|ia)\b', r'\1katanya', res)
    return res

def clean_conjunction_clutter(text: str) -> str:
    res = text
    res = re.sub(r'(^|[.!?]\s*)Dan\s+kemudian,?\s*', r'\1Kemudian, ', res)
    res = re.sub(r'(^|[.!?]\s*)Tetapi\s+bagaimanapun,?\s*', r'\1Namun, ', res)
    res = re.sub(r'(^|[.!?]\s*)Namun\s+tetapi,?\s*', r'\1Namun, ', res)
    res = re.sub(r'(^|[.!?]\s*)Sebagai\s+hasilnya,?\s*', r'\1Alhasil, ', res)
    res = re.sub(r'(^|[.!?]\s*)Oleh\s+karena\s+itu,?\s*', r'\1Karena itu, ', res)
    return res

tests = [
    ('"Aku akan pergi sekarang," dia berkata.', '"Aku akan pergi sekarang," ucapnya.'),
    ('"Apakah kamu yakin?" dia bertanya dengan cemas.', '"Apakah kamu yakin?" tanyanya dengan cemas.'),
    ('"Jangan mendekat!" dia berteriak.', '"Jangan mendekat!" serunya.'),
    ('"Ini terlalu mahal," kata dia menghela napas.', '"Ini terlalu mahal," katanya menghela napas.'),
    ("Dan kemudian, mereka melanjutkan perjalanan ke hutan.", "Kemudian, mereka melanjutkan perjalanan ke hutan."),
    ("Tetapi bagaimanapun, kami harus tetap waspada.", "Namun, kami harus tetap waspada."),
]

all_passed = True
for inp, expected in tests:
    out = clean_conjunction_clutter(smooth_dialogue_tags(inp))
    if out != expected:
        print(f"FAIL:\n  In:  {inp}\n  Out: {out}\n  Exp: {expected}")
        all_passed = False
    else:
        print(f"PASS: {inp} -> {out}")

if all_passed:
    print("\nALL PROTOTYPE TESTS PASSED!")
