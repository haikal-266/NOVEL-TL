"""
SeaLLM-v3-1.5B GGUF Translator (EN -> ID / JP -> ID)
Offline Indonesian novel translator powered by SeaLLMs-v3-1.5B via llama.cpp.
Tuned for natural, literary Southeast Asian / Indonesian phrasing with
Japanese speech marker & gender disambiguation.
"""

import os
import re
import gc
import time
import urllib.request
from typing import List, Optional, Callable
from llama_cpp import Llama
from core.speech_markers import detect_gender_cues, format_context_snippet

DEFAULT_REPO = "mradermacher/SeaLLMs-v3-1.5B-Chat-GGUF"
DEFAULT_FILENAME = "SeaLLMs-v3-1.5B-Chat.Q4_K_M.gguf"
DEFAULT_DOWNLOAD_URL = (
    f"https://huggingface.co/{DEFAULT_REPO}/resolve/main/{DEFAULT_FILENAME}"
)
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "seallm")

SYSTEM_PROMPT_EN_ID = (
    "Kamu adalah editor dan penerjemah novel fiksi profesional berbahasa Indonesia. "
    "Terjemahkan paragraf novel berikut ke dalam bahasa Indonesia sastra yang mengalir, alami, emosional, dan hidup layaknya novel Gramedia.\n\n"
    "PANDUAN PENTING GENDER DARI TEKS ASLI JEPANG:\n"
    "1. Perhatikan tanda gender karakter dari teks asli:\n"
    "   - Karakter Perempuan: tanda '少女/女の子/彼女/妹/姉/娘', kata ganti 'あたし/私', partikel dialog feminim '~わ/~かしら/~のよ/~わね'.\n"
    "     Wajib gunakan kata ganti perempuan ('ia', 'dia perempuan', 'gadis itu', 'putri'), JANGAN tertukar menjadi laki-laki ('dia/pria')!\n"
    "   - Karakter Laki-laki: tanda '少年/男/彼/兄/弟', kata ganti '俺/僕', partikel dialog maskulin '~ぜ/~ぞ/~だろ'.\n"
    "     Gunakan kata ganti laki-laki ('ia', 'pemuda itu', 'pria itu').\n"
    "2. Gunakan kata ganti dialog 'aku-kamu' yang akrab dan luwes. Hindari terjemahan kaku kata per kata.\n"
    "3. DILARANG KERAS menyalin atau menyertakan teks bahasa Jepang/kanji/hiragana/katakana ke dalam hasil terjemahan. Teks asli hanya petunjuk konteks; SELURUH kalimat hasil akhir WAJIB 100% berbahasa Indonesia.\n\n"
    "Format output WAJIB bernomor sama:\n"
    "[1] <hasil terjemahan Indonesia 1>\n"
    "[2] <hasil terjemahan Indonesia 2>\n"
    "DILARANG menulis komentar apapun selain nomor dan teks hasil terjemahan langsung."
)


def get_seallm_model_path(
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Return the absolute path where the SeaLLM GGUF model file is located."""
    return os.path.join(model_dir, filename)


def is_seallm_installed(
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> bool:
    """Check if the model file is already downloaded and valid (> 100 MB)."""
    target_path = get_seallm_model_path(filename, model_dir)
    return os.path.exists(target_path) and os.path.getsize(target_path) > 100 * 1024 * 1024


def download_seallm_with_progress(
    url: str = DEFAULT_DOWNLOAD_URL,
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR,
    progress_cb: Optional[Callable[[int, int, float], bool]] = None
) -> str:
    """
    Download SeaLLM GGUF directly from Hugging Face with chunk streaming and cancel support.
    progress_cb(downloaded_bytes, total_bytes, speed_mb_s) -> return False to cancel download.
    """
    os.makedirs(model_dir, exist_ok=True)
    target_path = os.path.join(model_dir, filename)
    part_path = target_path + ".part"

    if is_seallm_installed(filename, model_dir):
        return target_path

    print(f"[SeaLLM 1.5B] Mengunduh model {filename} dari {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        start_time = time.time()
        last_speed_time = start_time
        last_downloaded = 0
        speed_mb_s = 0.0

        with open(part_path, "wb") as f:
            chunk_size = 1024 * 1024  # 1 MB chunk
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                now = time.time()
                time_diff = now - last_speed_time
                if time_diff >= 0.8:
                    speed_mb_s = ((downloaded - last_downloaded) / (1024 * 1024)) / time_diff
                    last_speed_time = now
                    last_downloaded = downloaded

                if progress_cb:
                    should_continue = progress_cb(downloaded, total_size, speed_mb_s)
                    if not should_continue:
                        print("[SeaLLM 1.5B] Unduhan dibatalkan.")
                        f.close()
                        if os.path.exists(part_path):
                            try:
                                os.remove(part_path)
                            except Exception:
                                pass
                        raise RuntimeError("Unduhan SeaLLM dibatalkan oleh pengguna.")

    if os.path.exists(target_path):
        os.remove(target_path)
    os.rename(part_path, target_path)
    print(f"[SeaLLM 1.5B] Model berhasil diunduh ke {target_path}")
    return target_path


def ensure_seallm_downloaded(
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Ensure SeaLLM-v3-1.5B GGUF model is downloaded and return its file path."""
    if is_seallm_installed(filename, model_dir):
        return get_seallm_model_path(filename, model_dir)
    return download_seallm_with_progress(filename=filename, model_dir=model_dir)


class SeaLLMTranslator:
    """
    Offline Southeast Asian / Indonesian translator powered by SeaLLMs-v3-1.5B GGUF.
    Produces rich, flowing Indonesian prose for light novels with Japanese speech marker analysis.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_threads: Optional[int] = None,
        n_ctx: int = 2048
    ):
        if not model_path:
            model_path = ensure_seallm_downloaded()

        cpu_threads = n_threads or min(4, max(1, (os.cpu_count() or 4) - 1))
        print(f"[SeaLLM 1.5B] Memuat model {os.path.basename(model_path)} (threads={cpu_threads}, ctx={n_ctx})...")
        self.llm = Llama(
            model_path=model_path,
            n_threads=cpu_threads,
            n_ctx=n_ctx,
            n_batch=512,
            verbose=False
        )
        print("[SeaLLM 1.5B] Model siap digunakan!")

    def _clean_output(self, raw: str, fallback_orig: str = "") -> str:
        """Strip conversational filler, meta-comments, or accidental refusal notes."""
        text = raw.strip()

        # Remove leaked gender hints or context snippets
        text = re.sub(r"\(Konteks asli:.*?\)", "", text).strip()
        text = re.sub(r"\(Original context:.*?\)", "", text).strip()
        text = re.sub(r"\[(Karakter|Character):\s*(Perempuan|Laki-laki|Female|Male)\]", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\[(Perempuan|Laki-laki|Female|Male)\]", "", text, flags=re.IGNORECASE).strip()

        meta_patterns = [
            r"^(Teks ini|Teks di atas|Kalimat ini)\s+sudah\s+(dalam\s+)?bahasa\s+indonesia.*$",
            r"^.*tidak\s+perlu\s+diterjemahkan.*$",
            r"^.*tidak\s+perlu\s+terjemahan.*$",
            r"^(Catatan|Note|Terjemahan|Hasil terjemahan|Artinya|Polished|Edited)\s*:\s*",
            r"^Berikut\s+(adalah\s+)?hasil\s+terjemahan.*:\s*",
            r"^Here\s+is\s+the\s+(translation|polished|edited).*?:\s*",
        ]
        for pat in meta_patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                cleaned = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
                if not cleaned:
                    return fallback_orig.strip()
                text = cleaned

        # Remove markdown quotes if wrapped
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        elif text.startswith('「') and text.endswith('」'):
            text = text[1:-1].strip()
        elif text.startswith('“') and text.endswith('”'):
            text = text[1:-1].strip()
        return text

    def translate_single_en_to_id(self, text: str, ja_context: str = "") -> str:
        """Translate a single English sentence or title to Indonesian."""
        if not text or not text.strip():
            return ""

        hint = ""
        gender = detect_gender_cues(ja_context)
        if gender == "FEMALE":
            hint = " [Karakter: Perempuan]"
        elif gender == "MALE":
            hint = " [Karakter: Laki-laki]"

        user_content = f"{text.strip()}{hint}"
        if ja_context:
            user_content += f" (Konteks asli: {format_context_snippet(ja_context)})"

        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_EN_ID}\n"
            "DILARANG menulis komentar apapun selain teks hasil terjemahan langsung.<|im_end|>\n"
            f"<|im_start|>user\n{user_content}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        output = self.llm(
            prompt,
            max_tokens=512,
            temperature=0.2,
            top_p=0.9,
            stop=["<|im_end|>", "<|endoftext|>"]
        )

        res = self._clean_output(output["choices"][0]["text"], fallback_orig=text)
        # If output accidentally still contains Japanese characters, retry purely English without Japanese context
        if ja_context and re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", res):
            return self.translate_single_en_to_id(text, ja_context="")
        return res

    def translate_en_to_id(
        self,
        texts: List[str],
        ja_texts: Optional[List[str]] = None,
        batch_size: int = 4,
        progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Translate English texts to Indonesian using chunked batching with Japanese speech markers.
        Empty strings are returned as empty strings.
        """
        results = [""] * len(texts)
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]

        if not valid_indices:
            return results

        total = len(valid_indices)
        processed = 0

        chunk_size = max(1, min(batch_size, 4))
        for b_start in range(0, total, chunk_size):
            time.sleep(0.02)  # Yield CPU execution to keep FastAPI responsive
            batch_idxs = valid_indices[b_start : b_start + chunk_size]
            batch_texts = [texts[idx].strip() for idx in batch_idxs]

            if len(batch_texts) == 1:
                ja_c = ja_texts[batch_idxs[0]] if ja_texts and batch_idxs[0] < len(ja_texts) else ""
                results[batch_idxs[0]] = self.translate_single_en_to_id(batch_texts[0], ja_context=ja_c)
            else:
                # Build context-rich batch input
                lines = []
                for i, idx in enumerate(batch_idxs):
                    en_t = batch_texts[i]
                    ja_t = ja_texts[idx] if ja_texts and idx < len(ja_texts) else ""
                    gender = detect_gender_cues(ja_t)
                    gender_hint = " [Perempuan]" if gender == "FEMALE" else (" [Laki-laki]" if gender == "MALE" else "")

                    if ja_t:
                        snippet = format_context_snippet(ja_t)
                        lines.append(f"[{i+1}] {en_t}{gender_hint} (Konteks asli: {snippet})")
                    else:
                        lines.append(f"[{i+1}] {en_t}{gender_hint}")

                numbered_input = "\n".join(lines)
                prompt = (
                    f"<|im_start|>system\n{SYSTEM_PROMPT_EN_ID}<|im_end|>\n"
                    f"<|im_start|>user\n{numbered_input}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )

                try:
                    output = self.llm(
                        prompt,
                        max_tokens=min(2048, 250 * len(batch_texts)),
                        temperature=0.2,
                        top_p=0.9,
                        stop=["<|im_end|>", "<|endoftext|>"]
                    )
                    raw_out = output["choices"][0]["text"].strip()
                    parsed = re.findall(r"\[(\d+)\]\s*(.*?)(?=(?:\n\s*\[\d+\])|\Z)", raw_out, flags=re.DOTALL)
                    parsed_dict = {int(num): text.strip() for num, text in parsed}

                    if len(parsed_dict) == len(batch_texts):
                        for i, idx in enumerate(batch_idxs):
                            tl = self._clean_output(parsed_dict.get(i + 1, ""), fallback_orig=batch_texts[i])
                            # If result accidentally has leftover Japanese characters, re-translate clean
                            if re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", tl):
                                tl = self.translate_single_en_to_id(batch_texts[i], ja_context="")
                            results[idx] = tl
                    else:
                        for i, idx in enumerate(batch_idxs):
                            ja_c = ja_texts[idx] if ja_texts and idx < len(ja_texts) else ""
                            results[idx] = self.translate_single_en_to_id(batch_texts[i], ja_context=ja_c)
                except Exception:
                    for i, idx in enumerate(batch_idxs):
                        ja_c = ja_texts[idx] if ja_texts and idx < len(ja_texts) else ""
                        results[idx] = self.translate_single_en_to_id(batch_texts[i], ja_context=ja_c)

            processed += len(batch_idxs)
            if progress_cb:
                progress_cb(processed, total)

        return results

    def close(self) -> None:
        """Explicitly unload model from memory to free RAM."""
        if hasattr(self, "llm") and self.llm is not None:
            del self.llm
            self.llm = None
            gc.collect()
            print("[SeaLLM 1.5B] Model di-unload dari RAM.")
