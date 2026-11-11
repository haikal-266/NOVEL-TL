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


def detect_gender_cues(ja_text: str) -> Optional[str]:
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

    # 2. Dialogue particle check for lines with 「...」 or 『...』
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
