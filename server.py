"""
FastAPI Server for Novel to EPUB Generator
Provides REST endpoints for inspecting Kakuyomu novels, running translation jobs,
monitoring progress, and downloading generated EPUB files.
"""

import os
import re
import uuid
import threading
import time
from typing import Dict, List, Optional, Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core import (
    KakuyomuScraper,
    parse_kakuyomu_url,
    SyosetuScraper,
    parse_syosetu_url,
    parse_novel_url,
    get_novel_scraper,
    CacheManager,
    SugoiTranslator,
    EPUBBuilder,
    clean_english_text,
    get_glossary_manager
)

app = FastAPI(title="Novel EPUB Generator API", version="1.0.0")

# Enable CORS for Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Models -----------------

class InspectRequest(BaseModel):
    url: str

class EpisodeItem(BaseModel):
    index: int
    id: str
    title: str
    date: str

class NovelInspectResponse(BaseModel):
    workId: str
    source: str = "kakuyomu"
    currentEpisodeId: Optional[str] = None
    currentEpisodeIndex: Optional[int] = None
    titleJa: str
    titleEn: Optional[str] = None
    titleId: Optional[str] = None
    authorJa: str
    authorEn: Optional[str] = None
    authorId: Optional[str] = None
    synopsis: str
    synopsisEn: Optional[str] = None
    url: str
    totalEpisodes: int
    episodes: List[EpisodeItem]

class GenerateRequest(BaseModel):
    url: str
    rangeType: Literal["current", "range", "all"]
    customRange: Optional[str] = None  # e.g. "1-5" or "1,2,3"
    mode: Literal["translated", "bilingual", "raw"] = "translated"
    targetLang: Literal["en", "id"] = "en"
    forceTranslate: bool = False

class JobState(BaseModel):
    jobId: str
    status: Literal["pending", "running", "completed", "error"]
    progressPercent: int = 0
    currentChapter: int = 0
    totalChapters: int = 0
    chapterTitle: str = ""
    paragraphsDone: int = 0
    paragraphsTotal: int = 0
    message: str = ""
    downloadUrl: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    cancelled: bool = False


# Global job store and singleton translators
JOBS: Dict[str, JobState] = {}
_sugoi_translator = None
_seallm_translator = None
_translator_lock = threading.Lock()

def get_sugoi_translator() -> SugoiTranslator:
    global _sugoi_translator
    with _translator_lock:
        if _sugoi_translator is None:
            from core.translators.sugoi import SugoiTranslator
            _sugoi_translator = SugoiTranslator()
        return _sugoi_translator

def get_seallm_translator(job: Optional[JobState] = None):
    global _seallm_translator
    with _translator_lock:
        if _seallm_translator is None:
            from core.translators.seallm import (
                is_seallm_installed,
                get_seallm_model_path,
                download_seallm_with_progress,
                SeaLLMTranslator
            )

            model_path = get_seallm_model_path()
            if not is_seallm_installed():
                if job:
                    job.message = "Downloading SeaLLM model for the first time from Hugging Face..."
                    job.progressPercent = 1

                def on_download_progress(done_bytes: int, total_bytes: int, speed: float) -> bool:
                    if job:
                        if job.cancelled:
                            return False  # Abort download immediately
                        pct = int((done_bytes / total_bytes) * 100) if total_bytes else 1
                        done_mb = done_bytes / (1024 * 1024)
                        total_mb = total_bytes / (1024 * 1024)
                        job.message = f"Downloading SeaLLM: {done_mb:.1f}/{total_mb:.1f} MB ({pct}%) [{speed:.1f} MB/s]..."
                        job.progressPercent = min(99, pct)
                    return True

                model_path = download_seallm_with_progress(progress_cb=on_download_progress)

            if job:
                job.message = "Loading SeaLLM model into memory..."
                job.progressPercent = 1

            _seallm_translator = SeaLLMTranslator(model_path=model_path, n_threads=4, n_ctx=2048)
        return _seallm_translator

def get_translator() -> SugoiTranslator:
    return get_sugoi_translator()


STATUS_TAGS_RE = re.compile(
    r"【(?:連載(?:版)?|完結(?:済)?|書籍化(?:決定)?|アニメ化(?:決定)?|コミカライズ(?:決定)?|Web版|第[0-9０-９一二三四五六七八九十]+部|R-?15|残酷な描写あり|挿絵あり|短編|本編完結)[^】]*】",
    re.IGNORECASE
)

def clean_title_for_translation(title: str) -> str:
    """Strip only promotional/status bracket tags, preserving emphasized story title words like 【パリイ】."""
    return STATUS_TAGS_RE.sub("", title).strip()


def translate_novel_title(title_ja: str, sugoi: SugoiTranslator) -> str:
    """Accurately translate novel titles with subtitle/delimiter separation and clean punctuation."""
    clean_t = clean_title_for_translation(title_ja)
    if any(sep in clean_t for sep in ["〜", "～"]):
        parts = re.split(r"[〜～]", clean_t)
        main_part = parts[0].strip()
        sub_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
        main_en = clean_english_text(sugoi.translate_single(main_part)).replace("♪", "").strip()
        sub_en = clean_english_text(sugoi.translate_single(sub_part)).replace("♪", "").strip() if sub_part else ""
        if main_en and sub_en:
            main_en = main_en.rstrip(" .")
            sub_en = sub_en.lstrip(" .")
            return f"{main_en} - {sub_en}"
        return main_en or sub_en
    else:
        return clean_english_text(sugoi.translate_single(clean_t)).replace("♪", "").strip()


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:80] if len(sanitized) > 80 else sanitized


# ----------------- Endpoints -----------------

@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/glossary/stats")
def glossary_stats() -> Dict[str, int]:
    return get_glossary_manager().get_stats()


@app.get("/api/glossary/terms")
def glossary_terms(work_id: Optional[str] = None) -> Dict[str, str]:
    return get_glossary_manager().get_terms(work_id=work_id or "")


class AddTermRequest(BaseModel):
    termJa: str
    termEn: str
    category: Optional[str] = "custom"
    workId: Optional[str] = ""


@app.post("/api/glossary/term")
def add_glossary_term(req: AddTermRequest) -> Dict[str, str]:
    get_glossary_manager().add_term(
        term_ja=req.termJa,
        term_en=req.termEn,
        category=req.category or "custom",
        work_id=req.workId or ""
    )
    return {"status": "saved", "termJa": req.termJa, "termEn": req.termEn}


class AddCharacterGenderRequest(BaseModel):
    nameJa: str
    gender: str  # FEMALE or MALE
    workId: Optional[str] = ""


@app.get("/api/glossary/characters")
def list_character_genders(work_id: Optional[str] = None) -> Dict[str, str]:
    return get_glossary_manager().get_character_genders(work_id=work_id or "")


@app.post("/api/glossary/character")
def set_character_gender(req: AddCharacterGenderRequest) -> Dict[str, str]:
    get_glossary_manager().set_character_gender(
        name_ja=req.nameJa,
        gender=req.gender,
        work_id=req.workId or ""
    )
    return {"status": "saved", "nameJa": req.nameJa, "gender": req.gender.upper()}


@app.post("/api/novel/inspect", response_model=NovelInspectResponse)
def inspect_novel(req: InspectRequest) -> NovelInspectResponse:
    try:
        source, work_id, episode_id = parse_novel_url(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Novel URL: {str(e)}")

    cache = CacheManager(work_id)
    cached = cache.load_novel_info()
    
    # Always fetch fresh TOC & metadata from source so new chapters are instantly detected
    try:
        scraper = get_novel_scraper(req.url)
        fresh_info = scraper.get_novel_info()
        # Preserve existing translated titles/authors from cache
        if cached:
            for k in ["title_en", "author_en", "title_id", "author_id", "synopsis_en"]:
                if cached.get(k) and not fresh_info.get(k):
                    fresh_info[k] = cached[k]
        novel_info = fresh_info
        cache.save_novel_info(novel_info)
    except Exception as scrape_err:
        print(f"[Inspect] Scraper error, falling back to cache: {scrape_err}")
        if cached and cached.get("total_episodes"):
            novel_info = cached
        else:
            raise HTTPException(status_code=502, detail=f"Failed to fetch novel from {source.title()}: {scrape_err}")

    # Immediately translate novel title and author to English if not yet translated
    should_translate_title = (
        not novel_info.get("title_en")
        or "I'll do everything" in novel_info.get("title_en", "")
    )
    if should_translate_title:
        try:
            sugoi = get_sugoi_translator()
            novel_info["title_en"] = translate_novel_title(novel_info.get("title", ""), sugoi)
            if not novel_info.get("author_en"):
                novel_info["author_en"] = sugoi.translate_single(novel_info.get("author", "")).replace("♪", "").strip()
            cache.save_novel_info(novel_info)
        except Exception as e:
            print(f"[Inspect] Title translation skipped: {e}")

    curr_idx = None
    if episode_id:
        for ep in novel_info.get("episodes", []):
            if ep["id"] == episode_id:
                curr_idx = ep["index"]
                break

    ep_items = [
        EpisodeItem(
            index=ep["index"],
            id=ep["id"],
            title=ep["title"],
            date=ep.get("date", "")
        )
        for ep in novel_info.get("episodes", [])
    ]

    return NovelInspectResponse(
        workId=work_id,
        source=novel_info.get("source", source),
        currentEpisodeId=episode_id,
        currentEpisodeIndex=curr_idx,
        titleJa=novel_info.get("title", ""),
        titleEn=novel_info.get("title_en") or novel_info.get("title", ""),
        titleId=novel_info.get("title_id"),
        authorJa=novel_info.get("author", "Unknown Author"),
        authorEn=novel_info.get("author_en") or novel_info.get("author", "Unknown Author"),
        authorId=novel_info.get("author_id"),
        synopsis=novel_info.get("synopsis", ""),
        synopsisEn=novel_info.get("synopsis_en") or novel_info.get("synopsis", ""),
        url=novel_info.get("url", ""),
        totalEpisodes=novel_info.get("total_episodes", len(ep_items)),
        episodes=ep_items
    )


def run_job_worker(job_id: str, req: GenerateRequest) -> None:
    job = JOBS[job_id]
    try:
        job.status = "running"
        job.message = "Parsing URL and loading novel metadata..."
        source, work_id, episode_id = parse_novel_url(req.url)
        cache = CacheManager(work_id)
        scraper = get_novel_scraper(req.url)

        novel_info = cache.load_novel_info()
        if not novel_info or not novel_info.get("total_episodes"):
            novel_info = scraper.get_novel_info()
            cache.save_novel_info(novel_info)

        total_eps = novel_info["total_episodes"]

        # Determine indices
        curr_idx = None
        if episode_id:
            for ep in novel_info.get("episodes", []):
                if ep["id"] == episode_id:
                    curr_idx = ep["index"]
                    break

        if req.rangeType == "all":
            selected_indices = list(range(1, total_eps + 1))
        elif req.rangeType == "current":
            selected_indices = [curr_idx if curr_idx else 1]
        else:
            # Custom range
            raw_range = req.customRange or "1"
            indices_set = set()
            for part in raw_range.split(","):
                part = part.strip()
                if "-" in part:
                    s, e = part.split("-", 1)
                    if s.isdigit() and e.isdigit():
                        indices_set.update(range(max(1, int(s)), min(total_eps, int(e)) + 1))
                elif part.isdigit():
                    val = int(part)
                    if 1 <= val <= total_eps:
                        indices_set.add(val)
            selected_indices = sorted(list(indices_set)) or [1]

        target_lang = getattr(req, "targetLang", "en") or "en"
        force_translate = getattr(req, "forceTranslate", False) or False
        if target_lang == "id":
            cache_flavor = "bridge_id"
        else:
            cache_flavor = "sugoi_en"

        job.totalChapters = len(selected_indices)
        job_desc = "BRIDGE JP->EN->ID" if target_lang == "id" else "JP->EN (SUGOI)"
        job.message = f"Preparing {job.totalChapters} chapters for translation ({job_desc})..."

        # Initialize translators
        sugoi = get_sugoi_translator()
        seallm = get_seallm_translator(job=job) if target_lang == "id" else None

        # Translate metadata if not present (or if forceTranslate is requested)
        title_meta_key = f"title_{target_lang}"
        author_meta_key = f"author_{target_lang}"
        synopsis_meta_key = f"synopsis_{target_lang}"

        if force_translate or not novel_info.get(title_meta_key) or "I'll do everything" in novel_info.get(title_meta_key, ""):
            title_en = translate_novel_title(novel_info["title"], sugoi)
            novel_info["title_en"] = title_en
            if target_lang == "id" and seallm:
                novel_info[title_meta_key] = seallm.translate_single_en_to_id(title_en, ja_context=novel_info["title"])
            else:
                novel_info[title_meta_key] = title_en

        if force_translate or not novel_info.get(author_meta_key):
            author_en = sugoi.translate_single(novel_info["author"]).replace("♪", "").strip()
            novel_info["author_en"] = author_en
            if target_lang == "id" and seallm:
                novel_info[author_meta_key] = seallm.translate_single_en_to_id(author_en, ja_context=novel_info["author"])
            else:
                novel_info[author_meta_key] = author_en

        cache.save_novel_info(novel_info)

        # Process chapters sequentially (one chapter completely finished before the next)
        epub_chapters = []
        episodes_by_index = {ep["index"]: ep for ep in novel_info["episodes"]}

        for chap_i, idx in enumerate(selected_indices, start=1):
            if job.cancelled:
                print(f"[Job {job_id}] Cancel detected before chapter {chap_i}")
                break

            if idx not in episodes_by_index:
                continue

            ep_meta = episodes_by_index[idx]
            ep_id = ep_meta["id"]
            ep_title_ja = ep_meta["title"]

            job.currentChapter = chap_i
            job.chapterTitle = ep_title_ja

            # Check cache (skip if forceTranslate is true)
            cached_ep = None if force_translate else cache.load_episode(ep_id, cache_flavor)
            if cached_ep:
                epub_chapters.append(cached_ep)
                job.chapterTitle = cached_ep.get("title_tl") or ep_title_ja
                job.message = f"Chapter {chap_i}/{job.totalChapters}: Loaded from cache..."
                job.progressPercent = int((chap_i / job.totalChapters) * 90)
                if job.cancelled:
                    break
                continue

            # Fetch fresh content from Kakuyomu
            job.message = f"Fetching Chapter {chap_i}/{job.totalChapters}: {ep_title_ja}"
            ep_content = scraper.get_episode_content(ep_id)
            paragraphs = ep_content["paragraphs"]
            clean_texts = [p["clean"] for p in paragraphs]
            job.paragraphsTotal = len([p for p in paragraphs if not p["is_blank"]])
            job.paragraphsDone = 0

            chap_weight = 1.0 / job.totalChapters
            chap_base = (chap_i - 1) / job.totalChapters

            if target_lang == "id" and seallm:
                # ====== BRIDGE METHOD (JP -> EN -> ID) ======
                # Step 1: JP -> EN via Sugoi V4 (Ultra fast, accurate anime/LN syntax)
                job.message = f"Chapter {chap_i}/{job.totalChapters}: Stage 1 JP -> EN (Sugoi)..."
                en_title = clean_english_text(sugoi.translate_single(ep_title_ja, work_id=work_id))
                en_texts = sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)

                if job.cancelled:
                    break

                # Step 2: EN -> ID via SeaLLM 1.5B (Natural, literary Indonesian with speech markers)
                job.message = f"Chapter {chap_i}/{job.totalChapters}: Stage 2 EN -> ID (SeaLLM)..."
                title_tl = seallm.translate_single_en_to_id(en_title, ja_context=ep_title_ja)
                job.chapterTitle = title_tl

                def on_id_progress(done: int, total: int) -> None:
                    job.paragraphsDone = done
                    current_pct = (chap_base + (done / total if total else 1.0) * chap_weight) * 90
                    job.progressPercent = min(90, int(current_pct))

                id_texts = seallm.translate_en_to_id(
                    en_texts,
                    ja_texts=clean_texts,
                    batch_size=4,
                    progress_cb=on_id_progress
                )
                final_translations = id_texts

            else:
                # ====== STANDARD JP -> EN (Sugoi V4) ======
                job.message = f"Translating Chapter {chap_i}/{job.totalChapters}: {ep_title_ja}"
                title_tl = clean_english_text(sugoi.translate_single(ep_title_ja, work_id=work_id))
                job.chapterTitle = title_tl

                def on_en_progress(done: int, total: int) -> None:
                    job.paragraphsDone = done
                    current_pct = (chap_base + (done / total if total else 1.0) * chap_weight) * 90
                    job.progressPercent = min(90, int(current_pct))

                en_texts = sugoi.translate_texts(
                    clean_texts,
                    batch_size=16,
                    progress_cb=on_en_progress,
                    work_id=work_id
                )
                final_translations = [clean_english_text(t) for t in en_texts]

            # Assemble full chapter data
            chap_paras = []
            for p_info, tl_text in zip(paragraphs, final_translations):
                chap_paras.append({
                    "ja": p_info["raw"],
                    "tl": tl_text.strip(),
                    "is_blank": p_info["is_blank"]
                })

            chapter_data = {
                "index": idx,
                "id": ep_id,
                "title_ja": ep_title_ja,
                "title_tl": title_tl,
                "paragraphs": chap_paras
            }
            cache.save_episode(ep_id, cache_flavor, chapter_data)
            epub_chapters.append(chapter_data)
            job.progressPercent = int((chap_i / job.totalChapters) * 90)

            # Check if user clicked cancel during or right after this chapter
            if job.cancelled:
                print(f"[Job {job_id}] Cancel detected after completing chapter {chap_i}")
                break

        # Check if cancelled and how many chapters were fully completed
        if job.cancelled:
            if not epub_chapters:
                job.status = "error"
                job.error = "Translation cancelled by user before first chapter finished."
                job.message = "Cancelled (0 chapters completed)."
                return
            else:
                job.message = f"Translation cancelled. Packaging {len(epub_chapters)} completed chapters..."

        # Build EPUB
        builder = EPUBBuilder(novel_info, mode=req.mode, target_lang=target_lang)
        for chap in epub_chapters:
            builder.add_chapter(
                index=chap["index"],
                title_ja=chap["title_ja"],
                title_tl=chap["title_tl"],
                paragraphs=chap["paragraphs"]
            )

        # Output filename
        lang_title = novel_info.get(title_meta_key) or novel_info.get("title_en", "Novel")
        clean_title = sanitize_filename(lang_title)
        clean_title = re.sub(r"(\s*-\s*)+", " - ", clean_title)
        if " - " in clean_title:
            clean_title = clean_title.split(" - ")[0].strip()
        if len(clean_title) > 60 and " if " in clean_title:
            clean_title = clean_title.split(" if ")[0].strip()
        if len(clean_title) > 75:
            clean_title = clean_title[:73].rsplit(" ", 1)[0].rstrip(" ,-:")

        if job.cancelled:
            first_idx = epub_chapters[0]["index"]
            last_idx = epub_chapters[-1]["index"]
            chap_suffix = f" - Chapters {first_idx}-{last_idx} (Cancelled - {len(epub_chapters)} Chaps)"
        elif len(selected_indices) == 1:
            chap_suffix = f" - Chapter {selected_indices[0]}"
        elif len(selected_indices) < total_eps:
            chap_suffix = f" - Chapters {selected_indices[0]}-{selected_indices[-1]}"
        else:
            chap_suffix = " - Complete"

        lang_suffix = " (Indonesian)" if target_lang == "id" else ""
        filename = f"{clean_title}{chap_suffix}{lang_suffix}.epub"
        output_dir = os.path.abspath("output")
        os.makedirs(output_dir, exist_ok=True)
        final_file_path = os.path.join(output_dir, filename)

        builder.build_and_save(final_file_path)

        if epub_chapters:
            job.chapterTitle = epub_chapters[-1].get("title_tl") or job.chapterTitle

        job.progressPercent = 100
        job.status = "completed"
        job.filename = filename
        job.downloadUrl = f"/api/download/{filename}"
        if job.cancelled:
            job.message = f"Cancelled! EPUB successfully generated for {len(epub_chapters)} completed chapters."
        else:
            job.message = f"Completed! EPUB file generated successfully."

    except Exception as e:
        print(f"[Worker Error] Job {job_id}: {e}")
        if job.cancelled:
            job.status = "error"
            job.error = "Cancelled by user."
            job.message = "Process cancelled by user."
        else:
            job.status = "error"
            job.error = str(e)
            job.message = f"Error: {str(e)}"


@app.post("/api/novel/generate", response_model=JobState)
def start_generation(req: GenerateRequest, background_tasks: BackgroundTasks) -> JobState:
    job_id = uuid.uuid4().hex[:8]
    state = JobState(
        jobId=job_id,
        status="pending",
        message="Queued..."
    )
    JOBS[job_id] = state
    background_tasks.add_task(run_job_worker, job_id, req)
    return state


@app.get("/api/jobs/{job_id}", response_model=JobState)
def get_job_status(job_id: str) -> JobState:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]


@app.post("/api/jobs/{job_id}/cancel", response_model=JobState)
def cancel_job(job_id: str) -> JobState:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOBS[job_id]
    if job.status in ("running", "pending"):
        job.cancelled = True
        job.message = "Cancelling translation... Finalizing current chapter and generating EPUB..."
    return job


@app.get("/api/download/{filename}")
def download_epub(filename: str):
    # Check in output folder first, then workspace root
    file_path = os.path.join(os.path.abspath("output"), filename)
    if not os.path.exists(file_path):
        file_path = os.path.abspath(filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        media_type="application/epub+zip",
        filename=filename
    )


# Serve built Angular frontend if available
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist", "web", "browser")
if os.path.exists(STATIC_DIR):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
