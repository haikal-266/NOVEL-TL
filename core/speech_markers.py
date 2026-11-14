"""
Japanese Speech Markers & Gender Cue Analyzer for Web Novels.
Extracts gender markers, first-person pronouns, honorifics, and sentence-ending particles
to resolve pro-drop ambiguities and prevent gender misidentification.
"""

import re
from typing import Dict, List, Optional

# Female speech markers & keywords
FEMALE_PRONOUNS = {"あたし", "アタシ", "あたくし", "彼女"}
FEMALE_NOUNS = {"少女", "女の子", "娘", "お姉さん", "姉", "妹", "母", "お嬢様", "令嬢", "女性", "女"}
FEMALE_PARTICLES = ["わ", "かしら", "のよ", "わよ", "わね", "のね", "ちょうだい", "てよ", "もの"]

# Male speech markers & keywords
MALE_PRONOUNS = {"俺", "オレ", "おれ", "僕", "ボク", "ぼく", "わし", "彼"}
MALE_NOUNS = {"少年", "男の子", "息子", "お兄さん", "兄", "弟", "父", "男性", "男", "青年"}
MALE_PARTICLES = ["ぜ", "ぞ", "だろ", "かい", "じゃねえ", "だぜ", "だぞ", "な"]


def detect_gender_cues(ja_text: str, work_id: str = "") -> Optional[str]:
    """
    Analyze a Japanese sentence or dialogue for gender markers.
    Returns 'FEMALE', 'MALE', or None.
    """
    if not ja_text:
        return None

    score_female = 0
    score_male = 0

    # 1. Pronouns & nouns check
    for w in FEMALE_PRONOUNS | FEMALE_NOUNS:
        if w in ja_text:
            score_female += 2

    for w in MALE_PRONOUNS | MALE_NOUNS:
        if w in ja_text:
            score_male += 2

    # 2. Known character name registry check (prioritized)
    try:
        from core.glossary import get_glossary_manager
        char_dict = get_glossary_manager().get_character_genders(work_id=work_id)
        for char_name, char_gender in char_dict.items():
            if char_name in ja_text:
                if char_gender == "FEMALE":
                    score_female += 3
                elif char_gender == "MALE":
                    score_male += 3
    except Exception:
        pass

    # 3. Dialogue particle check for lines with 「...」 or 『...』
    dialogues = re.findall(r"[「『](.*?)[」』]", ja_text)
    for diag in dialogues:
        diag = diag.strip().rstrip("!?！？…・。")
        for p in FEMALE_PARTICLES:
            if diag.endswith(p):
                score_female += 1
        for p in MALE_PARTICLES:
            if diag.endswith(p):
                score_male += 1

    if score_female > score_male:
        return "FEMALE"
    elif score_male > score_female:
        return "MALE"
    return None


def format_context_snippet(ja_text: str, max_chars: int = 50) -> str:
    """Format a compact Japanese snippet for LLM context disambiguation."""
    if not ja_text:
        return ""
    clean = re.sub(r"\s+", " ", ja_text).strip()
    if len(clean) > max_chars:
        return clean[:max_chars] + "…"
    return clean


def correct_pronoun_gender(ja_text: str, en_text: str, work_id: str = "") -> str:
    """
    Corrects misidentified gender pronouns in English based on Japanese speech markers.
    Only modifies text if the Japanese cues are unambiguously FEMALE or MALE.
    """
    gender = detect_gender_cues(ja_text, work_id=work_id)
    if not gender or not en_text:
        return en_text

    has_explicit_male_pronoun = bool(re.search(r"彼(?!女)", ja_text))
    has_explicit_female_pronoun = "彼女" in ja_text

    text = en_text
    if gender == "FEMALE":
        replacements = [
            (r"\bHe\b", "She"),
            (r"\bhe\b", "she"),
            (r"\bHimself\b", "Herself"),
            (r"\bhimself\b", "herself"),
        ]
        if not has_explicit_male_pronoun:
            replacements.extend([
                (r"\bHis\b", "Her"),
                (r"\bhis\b", "her"),
                (r"\bHim\b", "Her"),
                (r"\bhim\b", "her"),
            ])
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text)

    elif gender == "MALE":
        replacements = [
            (r"\bShe\b", "He"),
            (r"\bshe\b", "he"),
            (r"\bHerself\b", "Himself"),
            (r"\bherself\b", "himself"),
        ]
        if not has_explicit_female_pronoun:
            replacements.extend([
                (r"\bHers\b", "His"),
                (r"\bhers\b", "his"),
                (r"\bHer\s+([a-zA-Z]+)", r"His \1"),
                (r"\bher\s+([a-zA-Z]+)", r"his \1"),
                (r"\bHer\b", "Him"),
                (r"\bher\b", "him"),
            ])
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text)

    return text

