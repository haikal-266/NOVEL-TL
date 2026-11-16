"""
Gold-Standard Novel & Human Bilingual Corpus Builder for VelTL
==============================================================
Builds a pristine 90,000+ sentence pair training corpus combining:
1. 50,000 Human-Verified Japanese-English pairs (Tanaka Corpus & BSD Dialogues)
2. 40,000 Sanitized & Grammar-Patched Syosetu Light Novel pairs from existing corpus.

Applies strict sanity filters:
- Deduplication
- Length ratio anomalies
- Untranslated Japanese text in English output
- Hallucinated quotes / repetition loops
- Zero-anaphora & speech-marker grammar patching
"""

import os
import sys
import json
import re
import random
from typing import List, Dict, Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.translators.sugoi import patch_japanese_grammar, smooth_light_novel_prose

OLD_CORPUS_PATH = os.path.join(PROJECT_ROOT, "data", "gold_corpus.jsonl")
NEW_CORPUS_PATH = os.path.join(PROJECT_ROOT, "data", "gold_corpus.jsonl")
BACKUP_PATH = os.path.join(PROJECT_ROOT, "data", "gold_corpus_backup.jsonl")

KANJI_KANA_REGEX = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")


def is_clean_pair(ja: str, en: str) -> bool:
    """Strict sanity check on Japanese-English pair."""
    ja = ja.strip()
    en = en.strip()

    if not ja or not en:
        return False

    # Length limits
    if len(ja) < 4 or len(en) < 4:
        return False
    if len(ja) > 350 or len(en) > 500:
        return False

    # English should not contain Japanese characters (untranslated fragments)
    if KANJI_KANA_REGEX.search(en):
        return False

    # Japanese must contain at least one kanji or kana
    if not KANJI_KANA_REGEX.search(ja):
        return False

    # Ratio sanity check: len(en) should be roughly 0.5x to 4x of len(ja)
    ratio = len(en) / max(len(ja), 1)
    if ratio < 0.25 or ratio > 4.5:
        return False

    # Drop obvious machine failure strings
    en_lower = en.lower()
    drop_patterns = [
        "translated by", "http://", "https://", "www.", "@",
        "i don't know how to translate", "i cannot translate",
        "as an ai", "patreon", "translator's note", "tl/n"
    ]
    if any(p in en_lower for p in drop_patterns):
        return False

    # Check for excessive repetition (stuck loops)
    words = en.split()
    if len(words) >= 6:
        # If the same 3-word sequence repeats >= 3 times
        for w_i in range(len(words) - 3):
            trigram = " ".join(words[w_i:w_i+3]).lower()
            if en_lower.count(trigram) >= 3:
                return False

    return True


def fetch_human_corpus(target_count: int = 55000) -> List[Dict[str, str]]:
    """Fetch human-verified bilingual sentences from Tanaka Corpus & BSD."""
    from datasets import load_dataset

    results = []
    seen_ja: Set[str] = set()

    # 1. Tanaka Corpus (~147k human verified sentences)
    print(f"[Corpus] Loading Tanaka Corpus from Hugging Face...")
    try:
        tanaka = load_dataset("hpprc/tanaka-corpus", split="train")
        # Shuffle deterministically
        indices = list(range(len(tanaka)))
        random.seed(42)
        random.shuffle(indices)

        for idx in indices:
            row = tanaka[idx]
            ja = row.get("ja", "").strip()
            en = row.get("en", "").strip()
            if ja not in seen_ja and is_clean_pair(ja, en):
                seen_ja.add(ja)
                results.append({"ja": ja, "en": en, "source": "tanaka_human"})
                if len(results) >= 40000:
                    break
        print(f"[Corpus] Loaded {len(results):,} human pairs from Tanaka Corpus.")
    except Exception as e:
        print(f"[Corpus] Warning: Tanaka Corpus fetch error: {e}")

    # 2. BSD Conversational Dialogue (~20k human dialogue sentences)
    print(f"[Corpus] Loading BSD Dialogue from Hugging Face...")
    try:
        bsd = load_dataset("ryo0634/bsd_ja_en", split="train")
        bsd_count = 0
        for row in bsd:
            ja = row.get("ja_sentence", "").strip()
            en = row.get("en_sentence", "").strip()
            if ja not in seen_ja and is_clean_pair(ja, en):
                seen_ja.add(ja)
                results.append({"ja": ja, "en": en, "source": "bsd_human"})
                bsd_count += 1
                if bsd_count >= 15000:
                    break
        print(f"[Corpus] Loaded {bsd_count:,} human pairs from BSD Dialogue.")
    except Exception as e:
        print(f"[Corpus] Warning: BSD Dialogue fetch error: {e}")

    return results


def sanitize_existing_novel_corpus() -> List[Dict[str, str]]:
    """Clean, filter, and patch the existing 61k novel sentences."""
    if not os.path.exists(OLD_CORPUS_PATH):
        return []

    print(f"[Corpus] Sanitizing existing novel corpus from {OLD_CORPUS_PATH}...")
    cleaned = []
    seen_ja: Set[str] = set()

    with open(OLD_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                ja = row.get("ja", "").strip()
                en = row.get("en", "").strip()

                if not ja or not en:
                    continue

                # 1. Apply pre-processing grammar patcher to Japanese
                ja_patched = patch_japanese_grammar(ja)

                # 2. Apply English light novel prose smoothing
                en_patched = smooth_light_novel_prose(en)

                # 3. Sanity check
                if ja_patched not in seen_ja and is_clean_pair(ja_patched, en_patched):
                    seen_ja.add(ja_patched)
                    cleaned.append({
                        "ja": ja_patched,
                        "en": en_patched,
                        "source": "syosetu_curated"
                    })
            except Exception:
                continue

    print(f"[Corpus] Retained {len(cleaned):,} pristine pairs from novel corpus.")
    return cleaned


def build_and_save_gold_corpus():
    print("=" * 65)
    print("  BUILDING GOLD-STANDARD NOVEL & HUMAN CORPUS")
    print("=" * 65)

    # Backup existing corpus
    if os.path.exists(OLD_CORPUS_PATH) and not os.path.exists(BACKUP_PATH):
        import shutil
        shutil.copyfile(OLD_CORPUS_PATH, BACKUP_PATH)
        print(f"[Backup] Saved backup of old corpus to {BACKUP_PATH}")

    # 1. Fetch Human Data (50k+ pairs)
    human_pairs = fetch_human_corpus()

    # 2. Sanitize Novel Data (35k-40k pairs)
    novel_pairs = sanitize_existing_novel_corpus()

    # 3. Combine & Balance
    all_pairs = human_pairs + novel_pairs
    print(f"[Corpus] Total combined pairs before final deduplication: {len(all_pairs):,}")

    # Deduplicate by Japanese sentence
    unique_pairs = []
    seen_ja: Set[str] = set()
    for item in all_pairs:
        ja = item["ja"]
        if ja not in seen_ja:
            seen_ja.add(ja)
            unique_pairs.append({
                "ja": item["ja"],
                "en": item["en"]
            })

    # Shuffle for uniform training distribution
    random.seed(42)
    random.shuffle(unique_pairs)

    total_final = len(unique_pairs)
    print(f"[Corpus] Final Pristine Gold Corpus: {total_final:,} verified sentence pairs!")

    # Write out to data/gold_corpus.jsonl
    with open(NEW_CORPUS_PATH, "w", encoding="utf-8") as f:
        for item in unique_pairs:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[Corpus] Successfully saved to: {NEW_CORPUS_PATH}")


if __name__ == "__main__":
    build_and_save_gold_corpus()

