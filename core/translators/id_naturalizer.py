"""
Indonesian Light Novel Prose Naturalizer
Enhances raw machine translation into natural, fluent, and emotionally engaging
Indonesian light novel prose (Gramedia / official publication style).
"""

import re
from typing import List

# Common stiff literal phrases -> natural Indonesian light novel phrasing
IDIOM_REPLACEMENTS = [
    # Dialogue & Greetings
    (r"\blihat aku nanti\b", "sampai nanti"),
    (r"\blihat saya nanti\b", "sampai jumpa nanti"),
    (r"\bmemberikan noda kecil\b", "mengangguk pelan"),
    (r"\bmemberikan sebuah noda kecil\b", "mengangguk pelan"),
    (r"\bmemberi noda\b", "mengangguk"),
    (r"\bmemberi anggukan\b", "mengangguk pelan"),
    (r"\bmemberikan anggukan\b", "mengangguk"),
    (r"\bmenunjuk jari saya\b", "melambaikan tangan"),
    (r"\bmenunjuk jarinya\b", "melambaikan tangannya"),
    (r"\bmenunjuk jari\b", "melambaikan tangan"),
    (r"\bmenangkap selimut\b", "memakai payung"),
    
    # Sci-Fi / Cold sleep terms
    (r"\btidur panas\b", "tidur kriogenik"),
    (r"\btidur dingin\b", "tidur kriogenik"),
    
    # Actions & Reactions
    (r"\bmelepaskan menguap besar\b", "menguap lebar"),
    (r"\bmelepaskan menguap\b", "menguap"),
    (r"\bmembuat wajah yang canggung\b", "memasang wajah serbasalah"),
    (r"\bmembuat wajah yang canggung\b", "memasang ekspresi canggung"),
    (r"\bmembuat senyum kecut\b", "tersenyum kecut"),
    (r"\bmemperlihatkan senyum kecut\b", "tersenyum kecut"),
    (r"\bmenarik nafas panjang\b", "menghela napas panjang"),
    (r"\bmelepaskan desahan\b", "menghela napas"),
    (r"\bmelepaskan helaan napas\b", "menghela napas"),
    (r"\bmenghembuskan nafas\b", "menghela napas"),
    (r"\bmenggelengkan kepala dengan tak berdaya\b", "menggeleng pasrah"),
    (r"\bmiringkan kepalanya\b", "memiringkan kepala heran"),
    (r"\bmemiringkan kepalanya karena heran\b", "memiringkan kepala heran"),
    
    # Phrases & Translationese
    (r"\bmengambil bentuk\b", "mulai terbentuk"),
    (r"\bdari masa depan saya diri\b", "dari diriku di masa depan"),
    (r"\buntuk masa lalu Anda sendiri\b", "untuk dirimu di masa lalu"),
    (r"\bdari masa depan saya\b", "dari masa depanku"),
    (r"\bke masa lalu Anda\b", "ke masa lalumu"),
    (r"\bbunga-bunga dalam satu bungkus\b", "sebuket bunga"),
    (r"\bsebuah karangan bunga\b", "sebuket bunga"),
    (r"\bkamar bayi\b", "buaian ayunan"),
    (r"\bkehidupan mulut saya kering\b", "tenggorokanku terasa kering"),
    (r"\btenggorokan saya kering\b", "tenggorokanku terasa kering"),
    (r"\bsebelas belas tahun\b", "tujuh puluh tahun"),
    (r"\bsepuluh puluh tahun\b", "tujuh puluh tahun"),
    (r"\bsetuju ratusan tahun\b", "tujuh puluh tahun"),
]


def smooth_indonesian_prose(text: str) -> str:
    """Apply dictionary and regex smoothing for natural Indonesian novel prose."""
    if not text or not text.strip():
        return ""

    res = text.strip()

    # Apply idiom replacements
    for pattern, replacement in IDIOM_REPLACEMENTS:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)

    # Clean double spaces or punctuation glitches
    res = re.sub(r"\s+", " ", res).strip()
    res = re.sub(r"\s+([,.\?!;:\"'])", r"\1", res)
    res = re.sub(r"([\"'\(])\s+", r"\1", res)

    # Capitalize start of sentence if needed
    if res and res[0].islower():
        res = res[0].upper() + res[1:]

    return res


def naturalize_indonesian_batch(texts: List[str]) -> List[str]:
    """Process a batch of Indonesian translated paragraphs."""
    return [smooth_indonesian_prose(t) for t in texts]

