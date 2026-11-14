"""
Overnight Autonomous Novel TL Pipeline
======================================
Autonomous End-to-End Runner for AFK Execution:
1. Mass Chapter Scrape & Translation (Syosetu / Kakuyomu)
2. Speech Markers & Light Novel Naturalizer Auto-Polish
3. Parallel Corpus Harvesting & Autonomous Data Curation
4. Train/Val Dataset Preparation
5. GPU MarianMT Fine-Tuning on NVIDIA GeForce GTX 1650 (FP16)
6. CTranslate2 INT8 Conversion & Deployment
7. Final Quality & Benchmark Report
"""

import os
import sys
import time
import json
import traceback
import subprocess
import datetime
from typing import List, Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

LOG_FILE = os.path.join(PROJECT_ROOT, "data", "overnight_run.log")
REPORT_FILE = os.path.join(PROJECT_ROOT, "data", "overnight_report.md")
CORPUS_FILE = os.path.join(PROJECT_ROOT, "data", "parallel_corpus.jsonl")


def log(msg: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def run_command_logged(cmd: List[str], desc: str) -> bool:
    log(f"--- Starting: {desc} ---")
    log(f"Command: {' '.join(cmd)}")
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=PROJECT_ROOT
        )
        for line in proc.stdout:
            line_str = line.strip()
            if line_str:
                log(f"  {line_str}")
        proc.wait()
        elapsed = time.time() - t0
        if proc.returncode == 0:
            log(f"--- Completed: {desc} in {elapsed:.1f}s (Success) ---")
            return True
        else:
            log(f"--- Failed: {desc} with returncode {proc.returncode} ---")
            return False
    except Exception as e:
        log(f"--- Exception in {desc}: {e} ---")
        return False


def get_uncached_episodes(work_id: str, limit: int = 150) -> List[Dict]:
    info_path = os.path.join(PROJECT_ROOT, "cache", work_id, "novel_info.json")
    if not os.path.exists(info_path):
        return []
    with open(info_path, "r", encoding="utf-8") as f:
        info = json.load(f)
    episodes = info.get("episodes", [])
    cache_dir = os.path.join(PROJECT_ROOT, "cache", work_id)
    uncached = []
    for ep in episodes:
        ep_id = str(ep.get("id"))
        ep_file = os.path.join(cache_dir, f"ep_{ep_id}_sugoi_en.json")
        if not os.path.exists(ep_file):
            uncached.append(ep)
            if len(uncached) >= limit:
                break
    return uncached


def scrape_and_translate_novels(max_total_episodes: int = 300) -> Tuple[int, int]:
    """
    Scrape and translate uncached episodes across cached novels.
    Returns: (episodes_translated, paragraphs_added)
    """
    log("=" * 65)
    log("  STAGE 1: MASS CHAPTER SCRAPE & HIGH-FLUENCY TRANSLATION")
    log("=" * 65)

    from core.scraper import SyosetuScraper, KakuyomuScraper
    from core.translators.sugoi import SugoiTranslator
    from core.cache_manager import CacheManager
    from core.epub_builder import clean_english_text

    sugoi = SugoiTranslator()
    os.makedirs(os.path.dirname(CORPUS_FILE), exist_ok=True)
    corpus_fp = open(CORPUS_FILE, "a", encoding="utf-8")

    # Target novels prioritized
    target_novels = [
        ("n3722ev", "syosetu", 150),   # Parry
        ("n6316bn", "syosetu", 100),   # Slime
        ("n6537fu", "syosetu", 50),    # Talentless Boy
    ]

    total_eps_done = 0
    total_paras_done = 0
    start_time = time.time()

    for work_id, source, cap in target_novels:
        if total_eps_done >= max_total_episodes:
            break

        needed = min(cap, max_total_episodes - total_eps_done)
        uncached = get_uncached_episodes(work_id, limit=needed)
        log(f"Novel [{work_id}] ({source}): Found {len(uncached)} uncached episodes to process (cap: {needed}).")

        if not uncached:
            continue

        cache = CacheManager(work_id)
        scraper = SyosetuScraper(work_id) if source == "syosetu" else KakuyomuScraper(work_id)

        for ep_idx, ep in enumerate(uncached, 1):
            ep_id = str(ep.get("id"))
            ep_num = ep.get("index", ep_idx)
            ep_title_ja = ep.get("title", "")

            try:
                # 1. Scrape episode content
                content = scraper.get_episode_content(ep_id)
                raw_paras = content.get("paragraphs", [])

                clean_texts = []
                para_objs = []
                for p in raw_paras:
                    if isinstance(p, dict):
                        ja_t = p.get("clean", p.get("raw", "")).strip()
                        is_blank = p.get("is_blank", False) or not ja_t
                    else:
                        ja_t = str(p).strip()
                        is_blank = not ja_t

                    para_objs.append({
                        "ja": ja_t,
                        "tl": "",
                        "is_blank": is_blank
                    })
                    if not is_blank:
                        clean_texts.append(ja_t)

                if not clean_texts:
                    log(f"  [{work_id}] Ep {ep_id}: Empty chapter, skipping.")
                    continue

                # 2. Translate title
                title_tl = ""
                if ep_title_ja:
                    title_tl = clean_english_text(sugoi.translate_single(ep_title_ja, work_id=work_id))

                # 3. Translate paragraphs with full Sugoi + Naturalizer pipeline
                tl_results = sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)

                # 4. Map back & append to corpus
                tl_idx = 0
                for obj in para_objs:
                    if not obj["is_blank"]:
                        clean_tl = clean_english_text(tl_results[tl_idx])
                        obj["tl"] = clean_tl
                        tl_idx += 1

                        # Append pair to corpus
                        rec = {
                            "work_id": work_id,
                            "ep_id": ep_id,
                            "ja": obj["ja"],
                            "en": clean_tl
                        }
                        corpus_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

                corpus_fp.flush()

                # 5. Save to cache
                ep_data = {
                    "index": ep_num,
                    "id": ep_id,
                    "title_ja": ep_title_ja,
                    "title_tl": title_tl,
                    "paragraphs": para_objs
                }
                cache.save_episode(ep_id, "sugoi_en", ep_data)

                total_eps_done += 1
                total_paras_done += len(clean_texts)

                elapsed = time.time() - start_time
                eps_per_min = total_eps_done / max(elapsed / 60.0, 0.01)
                log(f"  [{total_eps_done}/{max_total_episodes}] {work_id} Ep {ep_id} ({len(clean_texts)} paras) translated | Speed: {eps_per_min:.1f} ep/min")

                time.sleep(0.5)

            except Exception as e:
                log(f"  Error on [{work_id}] Ep {ep_id}: {e}")
                traceback.print_exc()
                time.sleep(1.0)

    corpus_fp.close()
    elapsed_total = time.time() - start_time
    log(f"Stage 1 Complete: {total_eps_done} episodes translated, {total_paras_done} paragraphs added in {elapsed_total/60.0:.1f} minutes.")
    return total_eps_done, total_paras_done


def main():
    t_start = time.time()
    log("=================================================================")
    log("   STARTING OVERNIGHT AUTONOMOUS NOVEL TL PIPELINE (AFK MODE)    ")
    log("=================================================================")

    # Step 1: Mass Scrape & Translate (Goal: ~200-250 new chapters)
    eps_done, paras_done = scrape_and_translate_novels(max_total_episodes=250)

    # Step 2: Autonomous Pronoun & Data Quality Curation
    log("\n" + "=" * 65)
    log("  STAGE 2: AUTONOMOUS DATA CURATION & PRONOUN VERIFICATION")
    log("=" * 65)
    curate_py = os.path.join(PROJECT_ROOT, "scripts", "auto_curate_corpus.py")
    curate_ok = run_command_logged([sys.executable, "-u", curate_py], "Corpus Curation")

    # Step 3: Train/Val Dataset Preparation
    log("\n" + "=" * 65)
    log("  STAGE 3: DATASET SPLIT & SENTENCEPIECE FORMATTER")
    log("=" * 65)
    prep_py = os.path.join(PROJECT_ROOT, "scripts", "prepare_training_data.py")
    prep_ok = run_command_logged([sys.executable, "-u", prep_py], "Dataset Preparation")

    # Step 4: GPU MarianMT Fine-Tuning (3 Epochs with FP16 on GTX 1650)
    log("\n" + "=" * 65)
    log("  STAGE 4: NEURAL MODEL FINE-TUNING (GTX 1650 4GB FP16)")
    log("=" * 65)
    train_py = os.path.join(PROJECT_ROOT, "scripts", "train_nmt.py")
    train_ok = run_command_logged([
        sys.executable, "-u", train_py,
        "--epochs", "3",
        "--batch-size", "4",
        "--lr", "1.5e-5"
    ], "MarianMT Fine-Tuning")

    # Step 5: CTranslate2 Conversion into models/custom_nmt
    log("\n" + "=" * 65)
    log("  STAGE 5: CTRANSLATE2 CONVERSION & EVALUATION")
    log("=" * 65)
    export_py = os.path.join(PROJECT_ROOT, "scripts", "export_to_ctranslate2.py")
    export_ok = run_command_logged([sys.executable, "-u", export_py], "CTranslate2 Conversion")

    total_runtime = time.time() - t_start
    hours = total_runtime / 3600.0

    # Write Final Report
    report_content = f"""# Overnight Novel TL Pipeline Summary Report

> [!NOTE]
> Run finished at: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> Total Runtime: {hours:.2f} hours ({total_runtime/60:.1f} minutes)

## Results & Statistics:
- **New Episodes Scraped & Translated**: {eps_done} episodes
- **New Paragraphs Processed**: {paras_done} paragraphs
- **Curated Dataset Status**: {"SUCCESS" if curate_ok else "FAILED"}
- **Dataset Split Status**: {"SUCCESS" if prep_ok else "FAILED"}
- **Model Fine-Tuning Status**: {"SUCCESS" if train_ok else "FAILED"}
- **CTranslate2 INT8 Deployment**: {"SUCCESS" if export_ok else "FAILED"}

## Active Models & Cache:
- All new episodes are immediately available in the web & mobile EPUB generator.
- Speech markers, character gender registry, and light novel naturalizer rules applied automatically.
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)

    log("\n=================================================================")
    log(f"   OVERNIGHT PIPELINE COMPLETE! Total Time: {hours:.2f} hours    ")
    log("=================================================================")


if __name__ == "__main__":
    main()

