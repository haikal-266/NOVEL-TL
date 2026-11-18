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
import datetime
from typing import Dict, List, Optional, Literal, Any, Tuple
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
    mode: Literal["translated", "bilingual", "raw", "audit"] = "translated"
    targetLang: Literal["en", "id"] = "en"
    engine: Literal["gemini", "offline"] = "gemini"
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
    auditUrl: Optional[str] = None
    auditFilename: Optional[str] = None
    error: Optional[str] = None
    cancelled: bool = False


# Global job store and singleton translators
JOBS: Dict[str, JobState] = {}
_sugoi_translator = None
_id_translator = None
_gemini_translator = None
_translator_lock = threading.Lock()

def get_sugoi_translator(job: Optional[JobState] = None):
    """
    Returns the default Japanese-to-English translator:
    Sugoi V4 CTranslate2 INT8 empowered with JapaneseGrammarPatcher,
    pro-drop resolution, speech markers, and light novel prose smoothing.
    """
    global _sugoi_translator
    with _translator_lock:
        if _sugoi_translator is None:
            if job:
                job.message = "Memuat engine Sugoi V4 + Grammar Patcher..."
            from core.translators.sugoi import SugoiTranslator
            print("[Server] Using Sugoi V4 + Grammar Patcher as default JP->EN engine...")
            _sugoi_translator = SugoiTranslator()
        return _sugoi_translator

def get_id_translator(job: Optional[JobState] = None):
    global _id_translator
    with _translator_lock:
        if _id_translator is None:
            if job:
                job.message = "Memuat engine VelTL EN->ID CTranslate2 ke memori..."
                job.progressPercent = 1
            from core.translators.marian_id import MarianIDTranslator
            _id_translator = MarianIDTranslator()
        return _id_translator

def get_gemini_instance(job: Optional[JobState] = None):
    global _gemini_translator
    with _translator_lock:
        if _gemini_translator is None:
            if job:
                job.message = "Menginisialisasi engine Google Gemini Flash (Free Tier)..."
            from core.translators.gemini_translator import get_gemini_translator
            _gemini_translator = get_gemini_translator()
        return _gemini_translator

def get_translator() -> Any:
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


def translate_chapter_title(ep_title_ja: str, sugoi: Any, id_trans: Any = None, work_id: str = "", chap_index: int = 1) -> Tuple[str, str]:
    """
    Safely translates chapter titles while protecting numeric chapter markers.
    Prevents numbers like '25' becoming 'I am 25 years old' or '49' becoming '59'.
    """
    clean_ja = (ep_title_ja or "").strip()
    if not clean_ja:
        return f"Chapter {chap_index}", f"Bab {chap_index}"

    # Pure number title (e.g. "03", "25", "101")
    if clean_ja.isdigit():
        num = int(clean_ja)
        return f"Chapter {num}", f"Bab {num}"

    # Number prefix with separator (e.g. "49　秘密通路の探索" or "77: 魔鼠の謎")
    m = re.match(r'^(\d+)[\s　:：\-_]*(.*)$', clean_ja)
    if m:
        num = m.group(1)
        sub_ja = m.group(2).strip()
        if not sub_ja:
            return f"Chapter {num}", f"Bab {num}"
        en_sub = clean_english_text(sugoi.translate_single(sub_ja, work_id=work_id))
        if id_trans:
            id_sub = id_trans.translate_single(en_sub, ja_text=sub_ja)
            return f"Chapter {num}: {en_sub}", f"Bab {num}: {id_sub}"
        return f"Chapter {num}: {en_sub}", f"Chapter {num}: {en_sub}"

    # General title
    en_title = clean_english_text(sugoi.translate_single(clean_ja, work_id=work_id)) or f"Chapter {chap_index}"
    if id_trans:
        id_title = id_trans.translate_single(en_title, ja_text=clean_ja) or f"Bab {chap_index}"
        return en_title, id_title
    return en_title, en_title


def translate_chapter_title_gemini(ep_title_ja: str, gemini: Any, target_lang: str = "id", work_id: str = "", chap_index: int = 1) -> Tuple[str, str]:
    """
    Translates chapter titles using Gemini while preserving numeric chapter markers.
    """
    clean_ja = (ep_title_ja or "").strip()
    if not clean_ja:
        return f"Chapter {chap_index}", f"Bab {chap_index}"

    if clean_ja.isdigit():
        num = int(clean_ja)
        return f"Chapter {num}", f"Bab {num}"

    m = re.match(r'^(\d+)[\s　:：\-_]*(.*)$', clean_ja)
    if m:
        num = m.group(1)
        sub_ja = m.group(2).strip()
        if not sub_ja:
            return f"Chapter {num}", f"Bab {num}"
        tl_sub = gemini.translate_single(sub_ja, target_lang=target_lang, work_id=work_id)
        if target_lang == "id":
            return f"Chapter {num}: {tl_sub}", f"Bab {num}: {tl_sub}"
        return f"Chapter {num}: {tl_sub}", f"Chapter {num}: {tl_sub}"

    tl_title = gemini.translate_single(clean_ja, target_lang=target_lang, work_id=work_id) or f"Chapter {chap_index}"
    if target_lang == "id":
        return tl_title, tl_title
    return tl_title, tl_title


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
        titleId=novel_info.get("title_en") or novel_info.get("title", ""),
        authorJa=novel_info.get("author", "Unknown Author"),
        authorEn=novel_info.get("author_en") or novel_info.get("author", "Unknown Author"),
        authorId=novel_info.get("author_en") or novel_info.get("author", "Unknown Author"),
        synopsis=novel_info.get("synopsis", ""),
        synopsisEn=novel_info.get("synopsis_en") or novel_info.get("synopsis", ""),
        url=novel_info.get("url", ""),
        totalEpisodes=novel_info.get("total_episodes", len(ep_items)),
        episodes=ep_items
    )


def generate_audit_markdown(novel_info: Dict[str, Any], chapters: List[Dict[str, Any]], target_lang: str) -> str:
    lines = []
    title = novel_info.get("title_en") or novel_info.get("title_id") or novel_info.get("title", "Novel")
    author = novel_info.get("author_en") or novel_info.get("author_id") or novel_info.get("author", "Unknown")
    work_id = novel_info.get("work_id", "")
    url = novel_info.get("url", "")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lang_desc = "ENGLISH" if target_lang.lower().startswith("en") else "INDONESIAN"
    lines.append(f"# {title}\n")
    lines.append(f"- **Author:** {author}")
    lines.append(f"- **Work ID:** `{work_id}`")
    lines.append(f"- **Source URL:** {url}")
    lines.append(f"- **Language:** {lang_desc}")
    lines.append(f"- **Generated At:** {now}")
    lines.append(f"- **Total Chapters:** {len(chapters)}")
    lines.append("\n---\n")

    for chap in chapters:
        c_idx = chap.get("index", 0)
        c_title_tl = chap.get("title_tl", "")
        lines.append(f"## Chapter {c_idx}: {c_title_tl}\n")

        p_num = 1
        for p in chap.get("paragraphs", []):
            if p.get("is_blank"):
                lines.append("\n* * *\n")
                continue
            en = p.get("en", "").strip()
            tl = p.get("tl", "").strip()

            if target_lang.lower().startswith("en"):
                text = en or tl
                if text:
                    lines.append(f"[p{p_num:03d}] {text}\n")
                    p_num += 1
            else:
                # Target is Indonesian
                if en and tl and en != tl:
                    # Clean parallel EN -> ID (MarianMT gold dataset format)
                    lines.append(f"### [p{p_num:03d}]")
                    lines.append(f"* **EN**: {en}")
                    lines.append(f"* **ID**: {tl}\n")
                else:
                    text = tl or en
                    if text:
                        lines.append(f"[p{p_num:03d}] {text}\n")
                p_num += 1

        lines.append("\n---\n")

    return "\n".join(lines)


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
        engine = getattr(req, "engine", "gemini") or "gemini"
        force_translate = getattr(req, "forceTranslate", False) or False

        # Set cache flavor
        if engine == "gemini":
            if req.mode == "audit":
                cache_flavor = f"gemini_audit_{target_lang}"
            elif target_lang == "id":
                cache_flavor = "gemini_id"
            else:
                cache_flavor = "gemini_en"
        else:
            if req.mode == "audit":
                cache_flavor = f"bridge_audit_{target_lang}"
            elif target_lang == "id":
                cache_flavor = "bridge_id"
            else:
                cache_flavor = "sugoi_en"

        job.totalChapters = len(selected_indices)
        if engine == "gemini":
            job_desc = "GEMINI FLASH JP->ID (LITERARY)" if target_lang == "id" else "GEMINI FLASH JP->EN"
        else:
            job_desc = "OFFLINE BRIDGE JP->EN->ID" if target_lang == "id" else "OFFLINE JP->EN (SUGOI)"
        job.message = f"Preparing {job.totalChapters} chapters for translation ({job_desc})..."

        # Initialize translators
        if engine == "gemini":
            gemini = get_gemini_instance(job=job)
            sugoi = get_sugoi_translator() if (req.mode == "audit" and target_lang == "id") else None
            id_trans = None
        else:
            gemini = None
            sugoi = get_sugoi_translator()
            id_trans = get_id_translator(job=job) if target_lang == "id" else None

        # Translate metadata if not present (or if forceTranslate is requested)
        title_meta_key = f"title_{target_lang}"
        author_meta_key = f"author_{target_lang}"
        synopsis_meta_key = f"synopsis_{target_lang}"

        if force_translate or not novel_info.get(title_meta_key) or not novel_info.get("title_en") or "I'll do everything" in novel_info.get(title_meta_key, ""):
            if engine == "gemini":
                title_en = gemini.translate_single(clean_title_for_translation(novel_info["title"]), target_lang="en")
            else:
                title_en = translate_novel_title(novel_info["title"], sugoi)
            novel_info["title_en"] = title_en
            # Keep novel title in English as standard light novel reading convention
            novel_info[title_meta_key] = title_en
            novel_info["title_id"] = title_en

        if force_translate or not novel_info.get(author_meta_key):
            raw_author = novel_info["author"].strip()
            # Clean conversational endings like です (e.g. バターです -> Butter)
            clean_author_ja = re.sub(r'です$', '', raw_author) if len(raw_author) > 2 else raw_author
            if engine == "gemini":
                author_en = gemini.translate_single(clean_author_ja, target_lang="en") or raw_author
            else:
                author_en = clean_english_text(sugoi.translate_single(clean_author_ja)).replace("♪", "").replace("It's", "").strip() or raw_author
            novel_info["author_en"] = author_en
            # Pen names should retain their proper English/Romaji form, not literally translated to Indonesian
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
            if cached_ep and req.mode == "audit":
                if target_lang == "id":
                    has_distinct_id = any(
                        p.get("tl") and p.get("en") and p.get("tl").strip() != p.get("en").strip()
                        for p in cached_ep.get("paragraphs", [])
                        if not p.get("is_blank")
                    )
                    if not has_distinct_id:
                        cached_ep = None  # Invalidate old English cache and force generating proper Indonesian
                elif target_lang == "en":
                    has_en = any(
                        p.get("en") or p.get("tl")
                        for p in cached_ep.get("paragraphs", [])
                        if not p.get("is_blank")
                    )
                    if not has_en:
                        cached_ep = None

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

            if engine == "gemini":
                # ====== GOOGLE GEMINI FLASH (Free Cloud API) ======
                def on_gemini_progress(done: int, total: int) -> None:
                    job.paragraphsDone = done
                    current_pct = (chap_base + (done / total if total else 1.0) * chap_weight) * 90
                    job.progressPercent = min(90, int(current_pct))

                if target_lang == "id":
                    use_offline_fallback = False
                    try:
                        job.message = f"Chapter {chap_i}/{job.totalChapters}: Menerjemahkan JP -> ID (Gemini Flash)..."
                        en_title, title_tl = translate_chapter_title_gemini(ep_title_ja, gemini, target_lang="id", work_id=work_id, chap_index=idx)
                        job.chapterTitle = title_tl

                        id_texts = gemini.translate_texts(
                            clean_texts,
                            target_lang="id",
                            chunk_size=25,
                            progress_cb=on_gemini_progress,
                            work_id=work_id,
                            ep_id=ep_id,
                            chap_index=idx
                        )
                        final_translations = id_texts

                        # If audit mode, also translate English for comparison
                        if req.mode == "audit":
                            job.message = f"Chapter {chap_i}/{job.totalChapters}: Menyiapkan teks EN untuk Audit Report..."
                            if sugoi:
                                en_texts = sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)
                            else:
                                en_texts = gemini.translate_texts(clean_texts, target_lang="en", chunk_size=25, work_id=work_id, ep_id=ep_id, chap_index=idx)
                            
                            # Enrich dataset with EN translation
                            trilingual = [
                                {
                                    "ja": clean_texts[i].strip(),
                                    "id": id_texts[i].strip(),
                                    "en": en_texts[i].strip(),
                                    "work_id": work_id,
                                    "chapter_id": ep_id,
                                    "chapter_index": idx,
                                    "p_index": i + 1,
                                    "model": "gemini-flash"
                                }
                                for i in range(len(clean_texts))
                                if clean_texts[i].strip() and id_texts[i].strip()
                            ]
                            if trilingual:
                                from core.dataset_logger import get_dataset_logger
                                get_dataset_logger().log_pairs(trilingual)
                        else:
                            en_texts = [""] * len(clean_texts)

                    except Exception as gemini_err:
                        print(f"[Server Warning] Gemini translation error ({gemini_err}). Otomatis beralih ke Offline VelTL...")
                        job.message = f"Chapter {chap_i}/{job.totalChapters}: Kuota Gemini habis/gagal, beralih ke Offline VelTL..."
                        use_offline_fallback = True

                    if use_offline_fallback:
                        # Graceful automatic fallback to offline Sugoi + MarianID
                        offline_sugoi = get_sugoi_translator()
                        offline_id = get_id_translator(job=job)
                        en_title, title_tl = translate_chapter_title(ep_title_ja, offline_sugoi, id_trans=offline_id, work_id=work_id, chap_index=idx)
                        job.chapterTitle = title_tl
                        en_texts = offline_sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)
                        id_texts = offline_id.translate_en_to_id(en_texts, ja_texts=clean_texts, batch_size=32, progress_cb=on_gemini_progress, work_id=work_id)
                        final_translations = id_texts

                else:
                    # Target lang is EN
                    try:
                        job.message = f"Chapter {chap_i}/{job.totalChapters}: Translating JP -> EN (Gemini Flash)..."
                        en_title, title_tl = translate_chapter_title_gemini(ep_title_ja, gemini, target_lang="en", work_id=work_id, chap_index=idx)
                        job.chapterTitle = title_tl

                        en_texts = gemini.translate_texts(
                            clean_texts,
                            target_lang="en",
                            chunk_size=25,
                            progress_cb=on_gemini_progress,
                            work_id=work_id,
                            ep_id=ep_id,
                            chap_index=idx
                        )
                        final_translations = en_texts
                    except Exception as gemini_err:
                        print(f"[Server Warning] Gemini EN error ({gemini_err}). Fallback ke Sugoi V4...")
                        job.message = f"Chapter {chap_i}/{job.totalChapters}: Gemini offline/quota, fallback ke Sugoi V4..."
                        offline_sugoi = get_sugoi_translator()
                        en_title, title_tl = translate_chapter_title(ep_title_ja, offline_sugoi, id_trans=None, work_id=work_id, chap_index=idx)
                        job.chapterTitle = title_tl
                        en_texts = offline_sugoi.translate_texts(clean_texts, batch_size=16, progress_cb=on_gemini_progress, work_id=work_id)
                        final_translations = [clean_english_text(t) for t in en_texts]

            elif target_lang == "id" and id_trans:
                # ====== BRIDGE METHOD (JP -> EN -> ID) ======
                # Step 1: JP -> EN via Sugoi V4 + JapaneseGrammarPatcher
                job.message = f"Chapter {chap_i}/{job.totalChapters}: Tahap 1 JP -> EN (Sugoi + Patcher)..."
                en_title, title_tl = translate_chapter_title(ep_title_ja, sugoi, id_trans=id_trans, work_id=work_id, chap_index=idx)
                job.chapterTitle = title_tl
                en_texts = sugoi.translate_texts(clean_texts, batch_size=16, work_id=work_id)

                if job.cancelled:
                    break

                # Step 2: EN -> ID via MarianMT INT8 (Ultra fast, zero hallucination, naturalized)
                job.message = f"Chapter {chap_i}/{job.totalChapters}: Tahap 2 EN -> ID (MarianMT INT8)..."

                def on_id_progress(done: int, total: int) -> None:
                    job.paragraphsDone = done
                    current_pct = (chap_base + (done / total if total else 1.0) * chap_weight) * 90
                    job.progressPercent = min(90, int(current_pct))

                id_texts = id_trans.translate_en_to_id(
                    en_texts,
                    ja_texts=clean_texts,
                    batch_size=32,
                    progress_cb=on_id_progress,
                    work_id=work_id
                )
                final_translations = id_texts

            else:
                # ====== STANDARD JP -> EN (Sugoi V4) ======
                job.message = f"Translating Chapter {chap_i}/{job.totalChapters}: {ep_title_ja}"
                en_title, title_tl = translate_chapter_title(ep_title_ja, sugoi, id_trans=None, work_id=work_id, chap_index=idx)
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
            for i, (p_info, tl_text) in enumerate(zip(paragraphs, final_translations)):
                en_val = en_texts[i].strip() if ('en_texts' in locals() and i < len(en_texts)) else ""
                chap_paras.append({
                    "ja": p_info["raw"],
                    "en": en_val,
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

        # Output filename (Always prefer clean English title for novel naming)
        lang_title = novel_info.get("title_en") or novel_info.get(title_meta_key) or "Novel"
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

        if req.mode == "audit":
            audit_md_content = generate_audit_markdown(novel_info, epub_chapters, target_lang)
            lang_label = "EN Dataset" if target_lang.lower().startswith("en") else "ID Report"
            audit_filename = f"{clean_title}{chap_suffix} [{lang_label}].md"
            audit_path = os.path.join(output_dir, audit_filename)
            with open(audit_path, "w", encoding="utf-8") as f:
                f.write(audit_md_content)
            job.auditFilename = audit_filename
            job.auditUrl = f"/api/download/{audit_filename}"
            print(f"[Server] Audit report saved: {audit_path}")

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
    media_type = "text/markdown; charset=utf-8" if filename.endswith(".md") else "application/epub+zip"
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename
    )


@app.get("/api/dataset/stats")
def get_dataset_stats_endpoint() -> Dict[str, Any]:
    from core.dataset_logger import get_dataset_logger
    return get_dataset_logger().get_stats()


class SettingsUpdateRequest(BaseModel):
    geminiApiKey: Optional[str] = None
    defaultEngine: Optional[Literal["gemini", "offline"]] = None


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    from core.translators.gemini_translator import load_gemini_config
    cfg = load_gemini_config()
    raw_keys = cfg.get("gemini_api_keys", [])
    raw_key = cfg.get("gemini_api_key", "")
    masked_key = f"{raw_key[:6]}...{raw_key[-4:]}" if len(raw_key) > 10 else ("Set" if raw_key else "")
    return {
        "geminiApiKeyMasked": masked_key,
        "isGeminiConfigured": bool(raw_key or raw_keys),
        "totalKeysInPool": len(raw_keys) if raw_keys else (1 if raw_key else 0),
        "defaultEngine": cfg.get("default_engine", "gemini")
    }


@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest) -> Dict[str, Any]:
    from core.translators.gemini_translator import load_gemini_config, save_gemini_config, get_gemini_translator
    cfg = load_gemini_config()
    if req.geminiApiKey and req.geminiApiKey.strip():
        cfg["gemini_api_key"] = req.geminiApiKey.strip()
        get_gemini_translator().update_api_key(req.geminiApiKey.strip())
    if req.defaultEngine:
        cfg["default_engine"] = req.defaultEngine
    save_gemini_config(cfg)
    return {"status": "ok"}


# Serve built Angular frontend if available
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist", "web", "browser")
if os.path.exists(STATIC_DIR):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
