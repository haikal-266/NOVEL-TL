"""
Autonomous Data Curation & Gold-Standard Corpus Builder
Applies multi-layered invariant checks, gender cue resolution (he/she auto-correction),
dialogue quotation parity, and data sanity filtering on parallel_corpus.jsonl.
Outputs: data/gold_corpus.jsonl
"""

import os
import sys
import re
import json
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.speech_markers import detect_gender_cues
from core.glossary import get_glossary_manager
from core.translators.sugoi import clean_dialogue_and_narration, smooth_dialogue_contractions

INPUT_CORPUS = os.path.join(PROJECT_ROOT, "data", "parallel_corpus.jsonl")
OUTPUT_GOLD_CORPUS = os.path.join(PROJECT_ROOT, "data", "gold_corpus.jsonl")
CURATION_LOG = os.path.join(PROJECT_ROOT, "data", "curation_fixes.log")

# Character gender registry for known works
CHARACTER_GENDER = {
    # Lettina
    "レティーナ": "FEMALE",
    "lettina": "FEMALE",
    "retina": "FEMALE",
    "クルーゼス": "MALE",
    "croesus": "MALE",
    "kruzes": "MALE",
    # Parry
    "ノール": "MALE",
    "noor": "MALE",
    "リーン": "FEMALE",
    "lyne": "FEMALE",
    "イネス": "FEMALE",
    "ines": "FEMALE",
    # Evil Grand Sorceress
    "修司": "MALE",
    "エルブラス": "MALE",
    "elbrus": "MALE",
    "デナ": "FEMALE",
    "dena": "FEMALE",
    "ロツェ": "FEMALE",
    "lhotse": "FEMALE",
    "アネット": "FEMALE",
    "anette": "FEMALE",
}

FEMALE_FIXES = [
    (r"\bHe\b", "She"),
    (r"\bhe\b", "she"),
    (r"\bHimself\b", "Herself"),
    (r"\bhimself\b", "herself"),
    (r"\bHis\b", "Her"),
    (r"\bhis\b", "her"),
    (r"\bHim\b", "Her"),
    (r"\bhim\b", "her"),
]

MALE_FIXES = [
    (r"\bShe\b", "He"),
    (r"\bshe\b", "he"),
    (r"\bHerself\b", "Himself"),
    (r"\bherself\b", "himself"),
    (r"\bHer\b", "His"),
    (r"\bher\b", "his"),
]


def audit_and_fix_pronouns(ja: str, en: str) -> tuple[str, str]:
    """
    Checks gender agreement between Japanese source and English target.
    Returns: (corrected_en, reason)
    """
    cue = detect_gender_cues(ja)
    
    # Check known character names if cue is None
    if not cue:
        ja_lower = ja.lower()
        en_lower = en.lower()
        for char_name, gender in CHARACTER_GENDER.items():
            if char_name in ja_lower or char_name in en_lower:
                cue = gender
                break

    if not cue:
        return en, ""

    fixed = en
    reason = ""

    if cue == "FEMALE":
        # Check if male pronouns were hallucinated
        has_male_pronouns = bool(re.search(r"\b(he|him|his|himself)\b", en, flags=re.IGNORECASE))
        if has_male_pronouns:
            for pat, repl in FEMALE_FIXES:
                fixed = re.sub(pat, repl, fixed)
            reason = "Fixed MALE -> FEMALE pronoun (cues in JA)"

    elif cue == "MALE":
        # Check if female pronouns were hallucinated
        has_female_pronouns = bool(re.search(r"\b(she|her|hers|herself)\b", en, flags=re.IGNORECASE))
        if has_female_pronouns:
            for pat, repl in MALE_FIXES:
                fixed = re.sub(pat, repl, fixed)
            reason = "Fixed FEMALE -> MALE pronoun (cues in JA)"

    return fixed, reason


def is_valid_translation(ja: str, en: str) -> tuple[bool, str]:
    """Checks for translation sanity and quality."""
    if not ja.strip() or not en.strip():
        return False, "Empty sentence"

    # Residual Japanese text in English output (NMT failure)
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", en):
        return False, "Residual Japanese characters in English"

    # Extreme length ratio anomaly (indicates hallucination or dropped content)
    ratio = len(en) / max(len(ja), 1)
    if ratio < 0.1 and len(ja) > 30:
        return False, f"Severe truncation (ratio: {ratio:.2f})"
    if ratio > 6.0 and len(ja) > 20:
        return False, f"Severe explosion/hallucination (ratio: {ratio:.2f})"

    # Repetition hallucination check (e.g. "I know, I know, I know, I know")
    words = en.split()
    if len(words) >= 8:
        for i in range(len(words) - 3):
            quad = " ".join(words[i:i+4])
            if en.count(quad) >= 3:
                return False, f"Repetition hallucination detected ('{quad}')"

    return True, ""


def main():
    print("=" * 65)
    print("  AUTONOMOUS DATA CURATION & GOLD CORPUS BUILDER")
    print("=" * 65)

    if not os.path.exists(INPUT_CORPUS):
        print(f"Error: {INPUT_CORPUS} not found!")
        return

    glossary = get_glossary_manager()

    total_in = 0
    total_gold = 0
    pronoun_fixes = 0
    quote_fixes = 0
    dropped_corrupt = 0

    fix_samples = []

    print(f"Reading input corpus: {INPUT_CORPUS}...")
    t0 = time.time()

    with open(INPUT_CORPUS, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_GOLD_CORPUS, "w", encoding="utf-8") as f_out, \
         open(CURATION_LOG, "w", encoding="utf-8") as f_log:

        for line_num, line in enumerate(f_in, 1):
            total_in += 1
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except Exception:
                dropped_corrupt += 1
                continue

            ja = record.get("ja", "").strip()
            en = record.get("en", "").strip()
            work_id = record.get("work_id", "")

            # 1. Sanity check
            valid, drop_reason = is_valid_translation(ja, en)
            if not valid:
                dropped_corrupt += 1
                f_log.write(f"[DROPPED Line {line_num}] Reason: {drop_reason}\nJA: {ja}\nEN: {en}\n\n")
                continue

            orig_en = en

            # 2. Quotation parity & normalization
            en = clean_dialogue_and_narration(ja, en)
            if en != orig_en:
                quote_fixes += 1

            # 3. Dialogue contraction smoothing
            en = smooth_dialogue_contractions(en)

            # 4. Pronoun & Gender audit
            en_fixed, fix_reason = audit_and_fix_pronouns(ja, en)
            if fix_reason:
                pronoun_fixes += 1
                if len(fix_samples) < 15:
                    fix_samples.append((ja, en, en_fixed, fix_reason))
                f_log.write(f"[FIX Line {line_num}] {fix_reason}\nJA:  {ja}\nOLD: {en}\nNEW: {en_fixed}\n\n")
                en = en_fixed

            # 5. Glossary post-processing
            en = glossary.apply_post_glossary(en, work_id=work_id)

            # Clean extra spaces & punctuation
            en = re.sub(r"\s+([,.:;!?])", r"\1", en)
            en = re.sub(r"\s+", " ", en).strip()

            # Save clean gold record
            gold_record = {
                "ja": ja,
                "en": en,
                "work_id": work_id,
                "ep_id": record.get("ep_id", "")
            }
            f_out.write(json.dumps(gold_record, ensure_ascii=False) + "\n")
            total_gold += 1

            if total_in % 5000 == 0:
                print(f"  Processed {total_in:,} pairs... (Gold so far: {total_gold:,})")

    elapsed = time.time() - t0

    print("\n" + "=" * 65)
    print("  CURATION COMPLETE!")
    print(f"  Total Input Pairs:         {total_in:,}")
    print(f"  Total Gold Pairs Produced: {total_gold:,} ({(total_gold/total_in)*100:.1f}%)")
    print(f"  Pronoun Gender Fixes:      {pronoun_fixes:,}")
    print(f"  Quotation Parity Fixes:    {quote_fixes:,}")
    print(f"  Dropped Outlier/Corrupt:   {dropped_corrupt:,}")
    print(f"  Processing Time:           {elapsed:.2f} seconds")
    print(f"  Gold Corpus File:          {OUTPUT_GOLD_CORPUS}")
    print(f"  Audit Log:                 {CURATION_LOG}")
    print("=" * 65)

    if fix_samples:
        print("\n--- Sample Pronoun Fixes Applied Automatically ---")
        for i, (ja_s, old_e, new_e, r_s) in enumerate(fix_samples[:5], 1):
            print(f"\n[{i}] {r_s}")
            print(f"    JA : {ja_s[:60]}...")
            print(f"    OLD: {old_e}")
            print(f"    NEW: {new_e}")


if __name__ == "__main__":
    main()

