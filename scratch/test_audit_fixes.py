import sys, os, re
sys.path.insert(0, os.path.abspath("."))

from core.translators.marian_id import UniversalEntityShield
from core.translators.id_naturalizer import smooth_indonesian_prose
from core.translators.sugoi import patch_japanese_grammar
from server import translate_chapter_title

print("--- RUNNING AUDIT FIXES TEST SUITE ---")

# 1. Test Entity Shield Stopword Protection & Case Sensitivity
shield = UniversalEntityShield()
texts = [
    "The hero met Shia and Philly in the forest.",
    "Was it true that Cerlis defeated the monster?",
    "But then, Rock drew his sword."
]
shield.extract_names_from_texts(texts)

# Verify 'The', 'Was', 'But' are NOT in tag_map
for stopword in ["The", "Was", "But", "In", "And"]:
    assert stopword not in shield.tag_map, f"CRITICAL: Stopword '{stopword}' was incorrectly masked!"
print("✓ Test 1: Stopword Blacklist verified ('The', 'Was', 'But' are NEVER masked).")

# Verify 'Shia', 'Philly', 'Cerlis', 'Rock' ARE properly shielded
for name in ["Shia", "Philly", "Cerlis", "Rock"]:
    assert name in shield.tag_map, f"Expected '{name}' to be shielded, but not found!"
print("✓ Test 2: Auto-Proper Noun Shield verified ('Shia', 'Philly', 'Cerlis', 'Rock' shielded).")

# Verify case-sensitivity in masking
test_line = "Rock threw a rock at the wall."
masked = shield.mask(test_line)
assert "rock at the wall" in masked, f"Lower-case 'rock' was incorrectly masked: {masked}"
assert not masked.startswith("Rock "), f"Upper-case 'Rock' was not masked: {masked}"
unmasked = shield.unmask(masked)
assert unmasked == test_line, f"Unmask mismatch: {unmasked} vs {test_line}"
print("✓ Test 3: Case-sensitive masking verified (Capitalized 'Rock' shielded, lowercase 'rock' untouched).")

# 2. Test Katakana Hallucination & Subtitle Tag Scrubber
dirty_id = "Aku bertemu dengan TAGA マジック・エクスプロレーション dan <font color=\"#FFFF00\">タルミナス・アイシクル 11</font>."
shield.tag_map = {"Shia": "TAGA"}
shield.reverse_map = {"TAGA": "Shia"}
cleaned_id = shield.unmask(dirty_id)
assert "マジック・エクスプロレーション" not in cleaned_id, f"Katakana leak not scrubbed: {cleaned_id}"
assert "タルミナス" not in cleaned_id, f"Terminus icicle not scrubbed: {cleaned_id}"
assert "<font" not in cleaned_id, f"HTML tag not scrubbed: {cleaned_id}"
assert "Shia" in cleaned_id, f"Entity not unmasked: {cleaned_id}"
print("✓ Test 4: Katakana Hallucination & Subtitle Tag Scrubber verified.")

# 3. Test Sensitive Religious, Domain & NSFW Sanitization
sensitive_cases = [
    ("Syiah tersenyum saat melihat buku itu.", "Shia tersenyum"),
    ("Surat ini dikirim ke Philadelphia.", "Surat ini dikirim ke Philly."),
    ("Mereka menyembah Allah iblis di kuil tua.", "Mereka menyembah Dewa Iblis di kuil tua."),
    ("Tuan Letze adalah seorang petenis agung.", "Tuan Letze adalah seorang Penyihir Agung."),
    ("Kami kembali ke serikat buruh untuk melapor.", "Kami kembali ke Guild untuk melapor."),
    ("Dokkaebi itu menyerang desa.", "Goblin itu menyerang desa."),
    ("Bijak agung Dasheng telah tiba.", "Bijak agung Bijak Agung telah tiba."),
    ("Dia dihadang oleh SMA vampir.", "Dia dihadang oleh Vampire High Lord."),
    ("Mereka memuji Tuhan Chicken.", "Mereka memuji Ayam Suci."),
    ("Wanita itu dengan lembut membelai bola-bolanya.", "Wanita itu dengan lembut mengelus Tama."),
    ("◇◇◇ (Tawa)", "◇◇◇")
]

for inp, expected_sub in sensitive_cases:
    out = smooth_indonesian_prose(inp)
    assert expected_sub in out, f"Failed domain/sensitive sanitation: In='{inp}', Out='{out}', Expected='{expected_sub}'"
print("✓ Test 5: Sensitive Domain & Religious Sanitizer verified (11/11 cases passed).")

# 4. Test Pre-Sugoi Japanese Ground-Truth Locks
ja_samples = [
    ("ゴブリンロードが現れた", "Goblin Lordが現れた"),
    ("ヴァンパイアハイロードの城", "Vampire High Lordの城"),
    ("タマを撫でて部屋を出た", "Tamaを撫でて部屋を出た"),
    ("ニワトリがコッコと鳴いた", "ニワトリがKokkoと鳴いた"),
    ("俺は第8位階の魔導士だ", "俺はRank 8の魔導士だ"),
]

for ja_in, ja_exp in ja_samples:
    ja_patched = patch_japanese_grammar(ja_in)
    assert ja_exp in ja_patched, f"Sugoi pre-patch failed: In='{ja_in}', Out='{ja_patched}', Expected='{ja_exp}'"
print("✓ Test 6: Pre-Sugoi Ground-Truth Locks verified (Lord, Tama, Kokko, Rank).")

# 5. Test Chapter Title Parser
class MockTranslator:
    def translate_single(self, text, ja_text="", work_id=""):
        return f"Translated {text}"

mock_sugoi = MockTranslator()
mock_id = MockTranslator()

t1_en, t1_id = translate_chapter_title("25", mock_sugoi, mock_id)
assert t1_en == "Chapter 25" and t1_id == "Bab 25", f"Numeric title failed: {t1_en}, {t1_id}"

t2_en, t2_id = translate_chapter_title("03", mock_sugoi, mock_id)
assert t2_en == "Chapter 3" and t2_id == "Bab 3", f"Zero-padded numeric title failed: {t2_en}, {t2_id}"

t3_en, t3_id = translate_chapter_title("49　秘密通路の探索", mock_sugoi, mock_id)
assert t3_en.startswith("Chapter 49: ") and t3_id.startswith("Bab 49: "), f"Numbered sub-title failed: {t3_en}, {t3_id}"

print("✓ Test 7: Chapter Title Parser verified (No more 'I am 25 years old' or corrupted digits).")

print("\n=============================================")
print("  ALL 7 AUDIT FIX SUITES PASSED WITH 100%!   ")
print("=============================================")
