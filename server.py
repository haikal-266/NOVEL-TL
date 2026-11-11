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
    CacheManager,
    SugoiTranslator,
    EPUBBuilder,
    clean_english_text
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
    currentEpisodeId: Optional[str] = None
    currentEpisodeIndex: Optional[int] = None
    titleJa: str
    titleEn: Optional[str] = None
    authorJa: str
    authorEn: Optional[str] = None
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


# Global job store and singleton translator
JOBS: Dict[str, JobState] = {}
_sugoi_translator: Optional[SugoiTranslator] = None
_translator_lock = threading.Lock()

def get_translator() -> SugoiTranslator:
    global _sugoi_translator
    with _translator_lock:
        if _sugoi_translator is None:
            _sugoi_translator = SugoiTranslator()
        return _sugoi_translator


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:80] if len(sanitized) > 80 else sanitized


# ----------------- Endpoints -----------------

@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/novel/inspect", response_model=NovelInspectResponse)
def inspect_novel(req: InspectRequest) -> NovelInspectResponse:
    try:
        work_id, episode_id = parse_kakuyomu_url(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Kakuyomu URL: {str(e)}")

    cache = CacheManager(work_id)
    cached = cache.load_novel_info()
    if cached and cached.get("total_episodes"):
        novel_info = cached
    else:
        scraper = KakuyomuScraper(work_id)
        novel_info = scraper.get_novel_info()
        cache.save_novel_info(novel_info)

    curr_idx = None
    if episode_id:
        for ep in novel_info.get("episodes", []):
            if ep["id"] == episode_id:
                curr_idx = ep["index"]
                break

    # Ensure English title, author, and synopsis are translated
    if not novel_info.get("title_en") or not novel_info.get("author_en"):
        try:
            translator = get_translator()
            if not novel_info.get("title_en") and novel_info.get("title"):
                clean_t = re.sub(r"【.*?】", "", novel_info["title"]).strip()
                if any(sep in clean_t for sep in ["〜", "～"]):
                    parts = re.split(r"[〜～]", clean_t)
                    main_part = parts[0].strip()
                    sub_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
                    main_en = translator.translate_single(main_part).replace("♪", "").strip()
                    sub_en = translator.translate_single(sub_part).replace("♪", "").strip() if sub_part else ""
                    novel_info["title_en"] = f"{main_en} - {sub_en}" if sub_en else main_en
                else:
                    novel_info["title_en"] = translator.translate_single(clean_t).replace("♪", "").strip()

            if not novel_info.get("author_en") and novel_info.get("author"):
                novel_info["author_en"] = translator.translate_single(novel_info["author"]).replace("♪", "").strip()

            if not novel_info.get("synopsis_en") and novel_info.get("synopsis"):
                short_syn = novel_info["synopsis"][:250].strip()
                novel_info["synopsis_en"] = translator.translate_single(short_syn).replace("♪", "").strip()

            cache.save_novel_info(novel_info)
        except Exception as e:
            print(f"[inspect_novel] translation warning: {e}")

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
        currentEpisodeId=episode_id,
        currentEpisodeIndex=curr_idx,
        titleJa=novel_info.get("title", ""),
        titleEn=novel_info.get("title_en"),
        authorJa=novel_info.get("author", "Unknown Author"),
        authorEn=novel_info.get("author_en"),
        synopsis=novel_info.get("synopsis", ""),
        synopsisEn=novel_info.get("synopsis_en"),
        url=novel_info.get("url", ""),
        totalEpisodes=novel_info.get("total_episodes", len(ep_items)),
        episodes=ep_items
    )


def run_job_worker(job_id: str, req: GenerateRequest) -> None:
    job = JOBS[job_id]
    try:
        job.status = "running"
        job.message = "Parsing URL and loading novel metadata..."
        work_id, episode_id = parse_kakuyomu_url(req.url)
        cache = CacheManager(work_id)
        scraper = KakuyomuScraper(work_id)

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

        job.totalChapters = len(selected_indices)
        job.message = f"Selected {job.totalChapters} chapters for translation..."

        # Initialize translator
        translator = get_translator()

        # Translate metadata if not present
        if not novel_info.get("title_en"):
            clean_t = re.sub(r"【.*?】", "", novel_info["title"]).strip()
            if any(sep in clean_t for sep in ["〜", "～"]):
                parts = re.split(r"[〜～]", clean_t)
                main_part = parts[0].strip()
                sub_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
                main_en = translator.translate_single(main_part).replace("♪", "").strip()
                sub_en = translator.translate_single(sub_part).replace("♪", "").strip() if sub_part else ""
                novel_info["title_en"] = f"{main_en} - {sub_en}" if sub_en else main_en
            else:
                novel_info["title_en"] = translator.translate_single(clean_t).replace("♪", "").strip()

        if not novel_info.get("author_en"):
            novel_info["author_en"] = translator.translate_single(novel_info["author"]).replace("♪", "").strip()

        if not novel_info.get("synopsis_en") and novel_info.get("synopsis"):
            novel_info["synopsis_en"] = translator.translate_single(novel_info["synopsis"]).replace("♪", "").strip()

        cache.save_novel_info(novel_info)

        # Process chapters
        epub_chapters = []
        episodes_by_index = {ep["index"]: ep for ep in novel_info["episodes"]}

        for chap_i, idx in enumerate(selected_indices, start=1):
            if idx not in episodes_by_index:
                continue

            ep_meta = episodes_by_index[idx]
            ep_id = ep_meta["id"]
            ep_title_ja = ep_meta["title"]

            job.currentChapter = chap_i
            job.chapterTitle = ep_title_ja
            job.message = f"Processing Chapter {chap_i}/{job.totalChapters}: {ep_title_ja}"

            # Check cache
            cached_ep = cache.load_episode(ep_id, "sugoi_en")
            if cached_ep:
                epub_chapters.append(cached_ep)
                job.progressPercent = int((chap_i / job.totalChapters) * 90)
                continue

            # Fetch fresh
            ep_content = scraper.get_episode_content(ep_id)
            paragraphs = ep_content["paragraphs"]
            job.paragraphsTotal = len([p for p in paragraphs if not p["is_blank"]])
            job.paragraphsDone = 0

            # Translate title
            title_tl = clean_english_text(translator.translate_single(ep_title_ja))

            # Translate paragraphs
            clean_texts = [p["clean"] for p in paragraphs]

            def on_progress(done: int, total: int) -> None:
                job.paragraphsDone = done
                chap_weight = 1.0 / job.totalChapters
                chap_base = (chap_i - 1) / job.totalChapters
                current_pct = (chap_base + (done / total if total else 1.0) * chap_weight) * 90
                job.progressPercent = min(90, int(current_pct))

            translated_texts = translator.translate_texts(
                clean_texts,
                batch_size=16,
                progress_cb=on_progress
            )

            chap_paras = []
            for p_info, tl_text in zip(paragraphs, translated_texts):
                chap_paras.append({
                    "ja": p_info["raw"],
                    "tl": clean_english_text(tl_text),
                    "is_blank": p_info["is_blank"]
                })

            chapter_data = {
                "index": idx,
                "id": ep_id,
                "title_ja": ep_title_ja,
                "title_tl": title_tl,
                "paragraphs": chap_paras
            }
            cache.save_episode(ep_id, "sugoi_en", chapter_data)
            epub_chapters.append(chapter_data)
            job.progressPercent = int((chap_i / job.totalChapters) * 90)

        # Build EPUB
        job.message = "Assembling EPUB package..."
        builder = EPUBBuilder(novel_info, mode=req.mode, target_lang="en")
        for chap in epub_chapters:
            builder.add_chapter(
                index=chap["index"],
                title_ja=chap["title_ja"],
                title_tl=chap["title_tl"],
                paragraphs=chap["paragraphs"]
            )

        # Output filename
        eng_title = novel_info.get("title_en", "Novel")
        clean_title = sanitize_filename(eng_title)
        clean_title = re.sub(r"(\s*-\s*)+", " - ", clean_title)
        if " - " in clean_title:
            clean_title = clean_title.split(" - ")[0].strip()
        if len(clean_title) > 60 and " if " in clean_title:
            clean_title = clean_title.split(" if ")[0].strip()
        if len(clean_title) > 75:
            clean_title = clean_title[:73].rsplit(" ", 1)[0].rstrip(" ,-:")

        if len(selected_indices) == 1:
            chap_suffix = f" - Chapter {selected_indices[0]}"
        elif len(selected_indices) < total_eps:
            chap_suffix = f" - Chapters {selected_indices[0]}-{selected_indices[-1]}"
        else:
            chap_suffix = " - Complete"

        filename = f"{clean_title}{chap_suffix}.epub"
        output_dir = os.path.abspath("output")
        os.makedirs(output_dir, exist_ok=True)
        final_file_path = os.path.join(output_dir, filename)

        builder.build_and_save(final_file_path)

        job.progressPercent = 100
        job.status = "completed"
        job.filename = filename
        job.downloadUrl = f"/api/download/{filename}"
        job.message = f"Finished! EPUB successfully generated."

    except Exception as e:
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
