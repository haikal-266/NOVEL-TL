import re

s = '"Kita harus segera pergi dari sini," ucapnya dengan cemas.'
res = s
# Clean double spaces, double dots, or punctuation glitches
res = re.sub(r"\.\.+", ".", res)
res = re.sub(r"\s+", " ", res).strip()
res = re.sub(r"\s+([,.\?!;:])", r"\1", res)

# Strip spaces immediately inside opening quotes
res = re.sub(r'(^|[\s(])([\"\'“])\s+', r'\1\2', res)

# Ensure space after closing quotes before a letter (e.g. '"ucapnya' -> '" ucapnya')
res = re.sub(r'([,.\?!;:a-zA-Z0-9][\"”])([a-zA-Z])', r'\1 \2', res)

# Parens
res = re.sub(r'\(\s+', '(', res)
res = re.sub(r'\s+\)', ')', res)

print("Result:", repr(res))
