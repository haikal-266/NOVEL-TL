import sys, os
sys.path.insert(0, os.path.abspath("."))
import re
from core.translators.id_naturalizer import (
    smooth_indonesian_prose,
    naturalize_indonesian_batch,
    apply_persona_lock,
    smooth_dialogue_tags,
    clean_conjunction_clutter
)

print("--- Running Test Suite: Solusi 1 Smart Heuristic Engine ---")

# 1. Male chest anatomy guard
t1 = smooth_indonesian_prose("Aku meletakkan tanganku di atas payudara Jean.")
assert "dada Jean" in t1, f"Failed male chest guard: {t1}"
print("✓ Test 1 Passed: Male chest guard ('payudara Jean' -> 'dada Jean')")

# 2. Calque idioms
t2 = smooth_indonesian_prose("Dia tidak bisa membantu tetapi tertawa saat melihat kejadian itu.")
assert "tak kuasa menahan tawa" in t2, f"Failed calque idiom: {t2}"
print("✓ Test 2 Passed: Calque idiom ('tidak bisa membantu tetapi tertawa' -> 'tak kuasa menahan tawa')")

t3 = smooth_indonesian_prose("Pertemuan penting itu akan mengambil tempat di istana.")
assert "berlangsung" in t3, f"Failed take place: {t3}"
print("✓ Test 3 Passed: Calque idiom ('mengambil tempat' -> 'berlangsung')")

t4 = smooth_indonesian_prose("Jean membuat wajah yang rumit setelah mendengar berita itu.")
assert "memasang ekspresi serbasalah" in t4, f"Failed complicated face: {t4}"
print("✓ Test 4 Passed: Calque idiom ('membuat wajah yang rumit' -> 'memasang ekspresi serbasalah')")

# 3. Conjunction clutter
t5 = smooth_indonesian_prose("Dan kemudian, kami melanjutkan perjalanan.")
assert t5.startswith("Kemudian, kami"), f"Failed conjunction clutter: {t5}"
print("✓ Test 5 Passed: Conjunction clutter ('Dan kemudian, ' -> 'Kemudian, ')")

# 4. Dialogue tag smoothing
t6 = smooth_indonesian_prose('"Kita harus segera pergi dari sini," dia berkata dengan cemas.')
assert '"Kita harus segera pergi dari sini," ucapnya dengan cemas.' in t6, f"Failed dialogue tag: {t6}"
print("✓ Test 6 Passed: Dialogue tag ('dia berkata' -> 'ucapnya')")

t7 = smooth_indonesian_prose('"Siapa yang ada di sana?" dia bertanya.')
assert '"Siapa yang ada di sana?" tanyanya.' in t7, f"Failed dialogue tag: {t7}"
print("✓ Test 7 Passed: Dialogue tag ('dia bertanya' -> 'tanyanya')")

# 5. Persona lock (no 'saya', uses 'aku' and '-ku')
t8 = smooth_indonesian_prose('"Saya ingin memeriksa kondisi rumah saya," dia berkata.')
assert '"Aku ingin memeriksa kondisi rumahku," ucapnya.' in t8, f"Failed persona lock: {t8}"
print("✓ Test 8 Passed: Persona lock ('Saya' -> 'Aku', 'rumah saya' -> 'rumahku', 'dia berkata' -> 'ucapnya')")

# 6. Batch variety (inter-paragraph smoothing)
batch_input = [
    "Kemudian, mereka memasuki hutan yang lebat.",
    "Kemudian, mereka melihat bayangan aneh di balik pohon.",
]
batch_output = naturalize_indonesian_batch(batch_input)
assert batch_output[0].startswith("Kemudian, "), f"Failed batch 0: {batch_output[0]}"
assert batch_output[1].startswith("Setelah itu, "), f"Failed batch 1 variety: {batch_output[1]}"
print("✓ Test 9 Passed: Inter-paragraph variety smoothing (consecutive 'Kemudian' -> 'Setelah itu')")

print("\n--- ALL TESTS PASSED SUCCESSFULLY! ---")
