"""
Batch Re-translate & Training Corpus Generator
Re-translates all cached Japanese novel episodes using the newly tuned Sugoi V4 pipeline
(paragraph-level context, tuned beam search, dialogue contractions, and glossary).
Updates cache files and exports a parallel training corpus (data/parallel_corpus.jsonl).
"""

import os
import sys
import glob
import json
import time
import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.translators.sugoi import SugoiTranslator
from core.epub_builder import clean_english_text
from core.glossary import get_glossary_manager


def main():
    print("=" * 65)
    print("  NOVEL TL - BATCH RE-TRANSLATION & CORPUS HARVESTER")
    print("=" * 65)

    sugoi = SugoiTranslator()
    glossary = get_glossary_manager()

    ep_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "cache", "*", "ep_*.json")))
    total_files = len(ep_files)
    print(f"Found {total_files} cached episode files to process.")

    corpus_path = os.path.join(PROJECT_ROOT, "data", "parallel_corpus.jsonl")
    os.makedirs(os.path.dirname(corpus_path), exist_ok=True)
    corpus_fp = open(corpus_path, "a", encoding="utf-8")

    total_paras_processed = 0
    start_time = time.time()

    for idx, filepath in enumerate(ep_files, 1):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            work_id = os.path.basename(os.path.dirname(filepath))
            ep_id = data.get("id", "unknown")
            ep_index = data.get("index", idx)
            ep_title_ja = data.get("title_ja", "")

            paragraphs = data.get("paragraphs", [])
            valid_indices = [
                i for i, p in enumerate(paragraphs)
                if p.get("ja") and p["ja"].strip() and not p.get("is_blank")
            ]

            if not valid_indices:
                continue

            clean_texts = [paragraphs[i]["ja"] for i in valid_indices]

            # Re-translate episode title
            if ep_title_ja:
                new_title_tl = clean_english_text(sugoi.translate_single(ep_title_ja, work_id=work_id))
                data["title_tl"] = new_title_tl

            # Re-translate paragraphs with tuned Sugoi V4
            new_translations = sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)

            # Update episode paragraphs & append to parallel corpus
            for i_val, tl_text in zip(valid_indices, new_translations):
                clean_tl = clean_english_text(tl_text)
                paragraphs[i_val]["tl"] = clean_tl
                
                # Append pair to corpus
                record = {
                    "work_id": work_id,
                    "ep_id": ep_id,
                    "ja": paragraphs[i_val]["ja"],
                    "en": clean_tl
                }
                corpus_fp.write(json.dumps(record, ensure_ascii=False) + "\n")

            total_paras_processed += len(valid_indices)

            # Save updated episode back to disk
            tmp_path = filepath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)

            # Calculate ETA
            elapsed = time.time() - start_time
            paras_per_sec = total_paras_processed / max(elapsed, 0.1)
            pct = (idx / total_files) * 100

            print(
                f"[{idx:3d}/{total_files:3d}] ({pct:5.1f}%) "
                f"Work: {work_id:20} Ep: {ep_index:3} | "
                f"+{len(valid_indices):3d} paras ({paras_per_sec:4.1f} p/s) | "
                f"Total: {total_paras_processed:,} paras"
            )
            corpus_fp.flush()

            # Slight yield to keep system responsive
            time.sleep(0.01)

        except Exception as e:
            print(f"[{idx:3d}/{total_files:3d}] Error in {filepath}: {e}")

    corpus_fp.close()
    total_elapsed = time.time() - start_time
    stats = glossary.get_stats()

    print("\n" + "=" * 65)
    print("  BATCH RE-TRANSLATION COMPLETE!")
    print(f"  Total Episodes Updated: {total_files}")
    print(f"  Total Paragraphs Re-translated: {total_paras_processed:,}")
    print(f"  Total Time: {total_elapsed / 60:.1f} minutes")
    print(f"  Parallel Corpus Saved: {corpus_path}")
    print(f"  Glossary Terms Harvested: {stats.get('total_terms', 0):,}")
    print("=" * 65)


if __name__ == "__main__":
    main()

