#!/usr/bin/env python3
"""
Kakuyomu Novel to EPUB Generator with Local AI Translation (Sugoi Toolkit / Local LLM)
Author: Antigravity Assistant
"""

import os
import sys
import re
import argparse
import time
from typing import List, Dict, Optional, Tuple

from core import (
    KakuyomuScraper,
    parse_kakuyomu_url,
    CacheManager,
    SugoiTranslator,
    LLMTranslator,
    EPUBBuilder
)


def sanitize_filename(name: str) -> str:
    """Sanitize novel title for safe filename on Windows/Linux."""
    # Remove characters forbidden in Windows filenames: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:80] if len(sanitized) > 80 else sanitized


def parse_range(range_str: str, total_episodes: int, current_idx: Optional[int]) -> List[int]:
    """Parse range specification into list of 1-based episode indices."""
    range_str = range_str.strip().lower()
    if range_str == "all":
        return list(range(1, total_episodes + 1))
    
    if range_str == "current":
        if current_idx is None:
            return [1]
        return [current_idx]

    indices = set()
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start = max(1, int(sub[0]))
                end = min(total_episodes, int(sub[1]))
                indices.update(range(start, end + 1))
        elif part.isdigit():
            val = int(part)
            if 1 <= val <= total_episodes:
                indices.add(val)

    res = sorted(list(indices))
    return res if res else [1]


def interactive_wizard() -> Dict:
    """Interactive wizard when script is launched without arguments."""
    print("=" * 64)
    print("   KAKUYOMU NOVEL TO EPUB GENERATOR (LOCAL AI TRANSLATION)")
    print("=" * 64)
    print("Alat pembuat file EPUB dari web novel Kakuyomu dengan translasi")
    print("model AI lokal (Sugoi Translator v4 / LM Studio / Ollama).\n")

    default_url = "https://kakuyomu.jp/works/2912051607243271731/episodes/2912051607330854893"
    print(f"Contoh URL: {default_url}")
    url_input = input("Masukkan URL Kakuyomu (Work atau Episode) [Enter untuk contoh]: ").strip()
    if not url_input:
        url_input = default_url

    try:
        work_id, episode_id = parse_kakuyomu_url(url_input)
    except Exception as e:
        print(f"[Error] URL tidak valid: {e}")
        sys.exit(1)

    print(f"\n[1/3] Mengambil informasi novel dari Kakuyomu (ID: {work_id})...")
    scraper = KakuyomuScraper(work_id)
    novel_info = scraper.get_novel_info()

    total_eps = novel_info["total_episodes"]
    print(f"\n>> Judul : {novel_info['title']}")
    print(f">> Author: {novel_info['author']}")
    print(f">> Total : {total_eps} Episode ditemukan\n")

    # Find current index if episode_id was in URL
    curr_idx = None
    if episode_id:
        for ep in novel_info["episodes"]:
            if ep["id"] == episode_id:
                curr_idx = ep["index"]
                break

    # Range selection
    print("-" * 50)
    print("Pilih Episode / Chapter yang ingin di-download:")
    if curr_idx is not None:
        print(f" [1] Hanya episode saat ini (Episode #{curr_idx}: {novel_info['episodes'][curr_idx-1]['title']})")
    else:
        print(f" [1] Hanya Episode #1")
    print(f" [2] Rentang episode (misal: 1-3 atau 1-5)")
    print(f" [3] Semua episode (1-{total_eps})")
    
    choice_range = input("Pilihan [1/2/3] (default 1): ").strip() or "1"
    if choice_range == "1":
        selected_indices = [curr_idx if curr_idx else 1]
    elif choice_range == "2":
        r_input = input(f"Masukkan rentang episode [1-{total_eps}]: ").strip()
        selected_indices = parse_range(r_input, total_eps, curr_idx)
    else:
        selected_indices = list(range(1, total_eps + 1))

    print(f"-> {len(selected_indices)} episode terpilih: {selected_indices[:5]}{'...' if len(selected_indices)>5 else ''}")

    # Engine selection
    print("-" * 50)
    print("Pilih Mesin Penerjemah AI:")
    print(" [1] Sugoi AI Translator (CTranslate2 Local - Cepat, Offline, JP -> EN) [Rekomendasi]")
    print(" [2] Local LLM API (LM Studio / Ollama - Bisa JP -> ID atau JP -> EN)")
    print(" [3] Tanpa Translasi (EPUB Bahasa Jepang Asli)")
    choice_eng = input("Pilihan [1/2/3] (default 1): ").strip() or "1"

    engine = "sugoi"
    target_lang = "en"
    mode = "translated"
    llm_url = "http://localhost:1234/v1"

    if choice_eng == "2":
        engine = "llm"
        print("\nPilih Bahasa Target untuk LLM:")
        print(" [1] Bahasa Indonesia (JP -> ID)")
        print(" [2] English (JP -> EN)")
        l_choice = input("Pilihan [1/2] (default 1): ").strip() or "1"
        target_lang = "id" if l_choice == "1" else "en"
        custom_url = input(f"URL API Local LLM [default: {llm_url}]: ").strip()
        if custom_url:
            llm_url = custom_url
    elif choice_eng == "3":
        engine = "raw"
        mode = "raw"

    if engine != "raw":
        print("-" * 50)
        print("Pilih Format Tampilan Buku (Layout Mode):")
        print(" [1] Hanya Hasil Terjemahan (Tampilan novel standar) [Rekomendasi]")
        print(" [2] Bilingual (Teks Asli Jepang di atas + Terjemahan di bawah)")
        choice_mode = input("Pilihan [1/2] (default 1): ").strip() or "1"
        mode = "bilingual" if choice_mode == "2" else "translated"

    return {
        "url": url_input,
        "work_id": work_id,
        "selected_indices": selected_indices,
        "engine": engine,
        "mode": mode,
        "target_lang": target_lang,
        "llm_url": llm_url,
        "output": None
    }


def run_pipeline(
    work_id: str,
    selected_indices: List[int],
    engine_name: str = "sugoi",
    mode: str = "translated",
    target_lang: str = "en",
    llm_url: str = "http://localhost:1234/v1",
    llm_model: Optional[str] = None,
    output_path: Optional[str] = None,
    batch_size: int = 16
) -> str:
    """Execute the full scraping, translation, and EPUB packaging pipeline."""
    cache = CacheManager(work_id)
    scraper = KakuyomuScraper(work_id)

    # 1. Fetch novel metadata
    cached_info = cache.load_novel_info()
    if cached_info and cached_info.get("total_episodes"):
        novel_info = cached_info
        print(f"[Novel] Loaded novel info from cache: {novel_info['title']}")
    else:
        print(f"[Novel] Fetching novel info from Kakuyomu...")
        novel_info = scraper.get_novel_info()
        cache.save_novel_info(novel_info)

    title = novel_info["title"]
    author = novel_info["author"]
    total_eps = novel_info["total_episodes"]

    print(f"\n========================================================")
    print(f" Judul       : {title}")
    print(f" Penulis     : {author}")
    print(f" Engine      : {engine_name.upper()} (Target: {target_lang.upper()})")
    print(f" Mode        : {mode.upper()}")
    print(f" Episode(s)  : {len(selected_indices)} dari {total_eps}")
    print(f"========================================================\n")

    # 2. Initialize Translator if needed
    translator = None
    if engine_name == "sugoi":
        print("[Translator] Initializing Sugoi V4 CTranslate2...")
        t0 = time.time()
        translator = SugoiTranslator()
        print(f"[Translator] Sugoi ready on {translator.device.upper()} ({translator.compute_type}) in {time.time() - t0:.2f}s!")
    elif engine_name == "llm":
        print(f"[Translator] Connecting to Local LLM at {llm_url} (Target: {target_lang.upper()})...")
        translator = LLMTranslator(api_base=llm_url, model_name=llm_model, target_lang=target_lang)

    # 2.5 Translate novel metadata to English if not already cached
    if engine_name != "raw":
        if "title_en" not in novel_info or not novel_info.get("title_en") or "top -" in novel_info.get("title_en", ""):
            print("[Novel] Translating novel title to English...")
            clean_t = re.sub(r"【.*?】", "", title).strip()
            if any(sep in clean_t for sep in ["〜", "～"]):
                parts = re.split(r"[〜～]", clean_t)
                main_part = parts[0].strip()
                sub_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
                main_en = translator.translate_single(main_part).replace("♪", "").strip()
                if sub_part:
                    sub_en = translator.translate_single(sub_part).replace("♪", "").strip()
                    novel_info["title_en"] = f"{main_en} - {sub_en}"
                else:
                    novel_info["title_en"] = main_en
            else:
                novel_info["title_en"] = translator.translate_single(clean_t).replace("♪", "").strip()

        if "author_en" not in novel_info or not novel_info.get("author_en"):
            raw_author_en = translator.translate_single(author)
            novel_info["author_en"] = raw_author_en.replace("♪", "").strip() or author

        if "synopsis_en" not in novel_info or not novel_info.get("synopsis_en"):
            if novel_info.get("synopsis"):
                raw_syn_en = translator.translate_single(novel_info["synopsis"])
                clean_syn = re.sub(r"[♪〜～]+", " - ", raw_syn_en)
                clean_syn = re.sub(r"(\s*-\s*)+", " - ", clean_syn).strip(" - ")
                novel_info["synopsis_en"] = clean_syn

        cache.save_novel_info(novel_info)
        print(f">> English Title : {novel_info.get('title_en')}")
        print(f">> English Author: {novel_info.get('author_en')}\n")

    # 3. Process Episodes
    epub_chapters = []
    
    # Map index to episode metadata
    episodes_by_index = {ep["index"]: ep for ep in novel_info["episodes"]}

    for i, idx in enumerate(selected_indices, start=1):
        if idx not in episodes_by_index:
            print(f"[Skip] Index {idx} not found in episode list.")
            continue

        ep_meta = episodes_by_index[idx]
        ep_id = ep_meta["id"]
        ep_title_ja = ep_meta["title"]
        print(f"[{i}/{len(selected_indices)}] Chapter #{idx}: {ep_title_ja}")

        # Check Cache
        cache_key = f"{engine_name}_{target_lang}" if engine_name != "raw" else "raw"
        cached_ep = cache.load_episode(ep_id, cache_key)
        
        if cached_ep:
            print(f"   -> Memuat dari cache...")
            epub_chapters.append(cached_ep)
            continue

        # Fetch fresh episode content
        ep_content = scraper.get_episode_content(ep_id)
        paragraphs = ep_content["paragraphs"]
        print(f"   -> Diambil: {len(paragraphs)} paragraf")

        # If raw mode, no translation needed
        if engine_name == "raw":
            chapter_data = {
                "index": idx,
                "id": ep_id,
                "title_ja": ep_title_ja,
                "title_tl": ep_title_ja,
                "paragraphs": [{"ja": p["raw"], "tl": p["raw"], "is_blank": p["is_blank"]} for p in paragraphs]
            }
            cache.save_episode(ep_id, cache_key, chapter_data)
            epub_chapters.append(chapter_data)
            continue

        # Translation
        t_start = time.time()
        # Translate title
        print(f"   -> Menerjemahkan judul chapter...")
        title_tl = translator.translate_single(ep_title_ja)

        # Translate non-blank paragraphs
        clean_texts = [p["clean"] for p in paragraphs]
        
        def show_progress(done, total):
            pct = int((done / total) * 100) if total else 0
            bar = "█" * (pct // 5) + "-" * (20 - (pct // 5))
            sys.stdout.write(f"\r   -> Menerjemahkan: [{bar}] {pct}% ({done}/{total} paragraf)")
            sys.stdout.flush()

        translated_texts = translator.translate_texts(
            clean_texts,
            batch_size=batch_size,
            progress_cb=show_progress
        )
        print(f"\n   -> Selesai dalam {time.time() - t_start:.2f}s!")

        # Assemble chapter paragraphs
        chap_paras = []
        for p_info, tl_text in zip(paragraphs, translated_texts):
            chap_paras.append({
                "ja": p_info["raw"],
                "tl": tl_text,
                "is_blank": p_info["is_blank"]
            })

        chapter_data = {
            "index": idx,
            "id": ep_id,
            "title_ja": ep_title_ja,
            "title_tl": title_tl,
            "paragraphs": chap_paras
        }
        cache.save_episode(ep_id, cache_key, chapter_data)
        epub_chapters.append(chapter_data)

    # 4. Generate EPUB
    print("\n[EPUB] Membuat file EPUB...")
    builder = EPUBBuilder(novel_info, mode=mode, target_lang=target_lang)
    for chap in epub_chapters:
        builder.add_chapter(
            index=chap["index"],
            title_ja=chap["title_ja"],
            title_tl=chap["title_tl"],
            paragraphs=chap["paragraphs"]
        )

    # Determine output file path
    if not output_path:
        if mode == "translated":
            # Pure English filename
            eng_title = novel_info.get("title_en", "Novel")
            clean_title = sanitize_filename(eng_title)
            clean_title = re.sub(r"(\s*-\s*)+", " - ", clean_title)
            # If there is a subtitle divider ' - ', prefer the main title part for filename
            if " - " in clean_title:
                clean_title = clean_title.split(" - ")[0].strip()
            # If still very long, trim at condition clause like ' if ' or at length limit
            if len(clean_title) > 60 and " if " in clean_title:
                clean_title = clean_title.split(" if ")[0].strip()
            if len(clean_title) > 75:
                clean_title = clean_title[:73].rsplit(" ", 1)[0].rstrip(" ,-:")
                clean_title = re.sub(r"\b(if|to|the|a|an|of|and|in|on|at|by|for|with)\b$", "", clean_title, flags=re.IGNORECASE).strip()
            
            if len(selected_indices) == 1:
                chap_suffix = f" - Chapter {selected_indices[0]}"
            elif len(selected_indices) < total_eps:
                chap_suffix = f" - Chapters {selected_indices[0]}-{selected_indices[-1]}"
            else:
                chap_suffix = " - Complete"
            filename = f"{clean_title}{chap_suffix}.epub"
            os.makedirs("output", exist_ok=True)
            output_path = os.path.join("output", filename)
        elif mode == "bilingual":
            clean_title = sanitize_filename(novel_info.get("title_en", title))
            if " - " in clean_title:
                clean_title = clean_title.split(" - ")[0].strip()
            if len(clean_title) > 85:
                clean_title = clean_title[:83].rsplit(" ", 1)[0].rstrip(" ,-:")
            if len(selected_indices) == 1:
                chap_suffix = f" - Chapter {selected_indices[0]} (Bilingual)"
            elif len(selected_indices) < total_eps:
                chap_suffix = f" - Chapters {selected_indices[0]}-{selected_indices[-1]} (Bilingual)"
            else:
                chap_suffix = " (Bilingual)"
            filename = f"{clean_title}{chap_suffix}.epub"
            os.makedirs("output", exist_ok=True)
            output_path = os.path.join("output", filename)
        else:
            clean_title = sanitize_filename(title)
            filename = f"{clean_title}_raw.epub"
            os.makedirs("output", exist_ok=True)
            output_path = os.path.join("output", filename)

    final_path = builder.build_and_save(output_path)
    file_size_kb = os.path.getsize(final_path) / 1024

    print(f"\n" + "=" * 64)
    print(f" SUKSES! File EPUB berhasil dibuat:")
    print(f" Lokasi   : {final_path}")
    print(f" Ukuran   : {file_size_kb:.1f} KB")
    print(f" Chapters : {len(epub_chapters)} Chapter")
    print("=" * 64 + "\n")
    return final_path


def main():
    parser = argparse.ArgumentParser(
        description="Kakuyomu Web Novel EPUB Generator with Sugoi / Local AI Translation."
    )
    parser.add_argument("--url", help="Kakuyomu novel URL (Work or Episode)")
    parser.add_argument(
        "--range",
        default="current",
        help="Chapter range to process: 'current', '1-5', '1,2,3', 'all' (default: current)"
    )
    parser.add_argument(
        "--engine",
        choices=["sugoi", "llm", "raw"],
        default="sugoi",
        help="Translation engine: sugoi (default, fast local), llm (LM Studio/Ollama), raw (original Japanese)"
    )
    parser.add_argument(
        "--mode",
        choices=["translated", "bilingual", "raw"],
        default="translated",
        help="EPUB layout mode: translated (default), bilingual, raw"
    )
    parser.add_argument(
        "--target-lang",
        default="en",
        help="Target language: 'en' (default for Sugoi) or 'id' (Indonesian, supported in LLM engine)"
    )
    parser.add_argument(
        "--llm-url",
        default="http://localhost:1234/v1",
        help="Local LLM API base URL (default: http://localhost:1234/v1 for LM Studio)"
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="Model name for LLM (default: auto-detected from server)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output EPUB filename"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for Sugoi translation (default: 16)"
    )

    args = parser.parse_args()

    # If no URL provided via CLI, launch interactive wizard
    if not args.url:
        config = interactive_wizard()
        run_pipeline(
            work_id=config["work_id"],
            selected_indices=config["selected_indices"],
            engine_name=config["engine"],
            mode=config["mode"],
            target_lang=config["target_lang"],
            llm_url=config["llm_url"],
            output_path=config["output"]
        )
    else:
        work_id, episode_id = parse_kakuyomu_url(args.url)
        scraper = KakuyomuScraper(work_id)
        info = scraper.get_novel_info()
        total_eps = info["total_episodes"]

        curr_idx = None
        if episode_id:
            for ep in info["episodes"]:
                if ep["id"] == episode_id:
                    curr_idx = ep["index"]
                    break

        selected_indices = parse_range(args.range, total_eps, curr_idx)

        run_pipeline(
            work_id=work_id,
            selected_indices=selected_indices,
            engine_name=args.engine,
            mode=args.mode,
            target_lang=args.target_lang,
            llm_url=args.llm_url,
            llm_model=args.llm_model,
            output_path=args.output,
            batch_size=args.batch_size
        )


if __name__ == "__main__":
    main()

