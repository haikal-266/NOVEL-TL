"""
SeaLLM-v3-7B GGUF Translator (EN -> ID / JP -> ID)
Offline Indonesian novel translator powered by SeaLLMs-v3-7B via llama.cpp.
Tuned for natural, literary Southeast Asian / Indonesian phrasing.
"""

import os
import re
import gc
import time
import urllib.request
from typing import List, Optional, Callable
from llama_cpp import Llama

DEFAULT_REPO = "QuantFactory/SeaLLMs-v3-7B-Chat-GGUF"
DEFAULT_FILENAME = "SeaLLMs-v3-7B-Chat.Q4_K_M.gguf"
DEFAULT_DOWNLOAD_URL = (
    f"https://huggingface.co/{DEFAULT_REPO}/resolve/main/{DEFAULT_FILENAME}"
)
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "seallm")

SYSTEM_PROMPT_EN_ID = (
    "Kamu adalah editor dan penerjemah novel fiksi profesional berbahasa Indonesia. "
    "Terjemahkan teks bahasa Inggris berikut ke bahasa Indonesia yang luwes, emosional, dan alami layaknya novel terbitan Gramedia. "
    "Hindari terjemahan kaku kata per kata, ubah idiom bahasa Inggris menjadi padanan yang wajar di telinga pembaca Indonesia, "
    "dan gunakan kata ganti 'aku-kamu' untuk dialog akrab. Pastikan ritme kalimat terasa hidup.\n"
    "Aturan ketat:\n"
    "1. HANYA berikan hasil terjemahan langsung tanpa teks pembuka, tanpa pengantar, dan tanpa catatan/penjelasan apapun.\n"
    "2. Pertahankan keutuhan alur cerita dan emosi setiap adegan."
)

SYSTEM_PROMPT_JP_ID = (
    "Anda adalah editor dan penerjemah novel fiksi profesional berbahasa Indonesia.\n"
    "Tugas: Terjemahkan teks novel Jepang berikut ke dalam bahasa Indonesia novel yang alami, mengalir, dan mudah dipahami.\n"
    "Aturan ketat:\n"
    "1. Pertahankan konsistensi nama karakter dan dialog.\n"
    "2. HANYA berikan teks hasil terjemahan langsung tanpa pembuka atau penjelasan."
)


def get_seallm_model_path(
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Return the absolute path where the SeaLLM GGUF model file should be located."""
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

    print(f"[SeaLLM 7B] Mengunduh model {filename} dari {url}...")
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
                        print("[SeaLLM 7B] Unduhan dibatalkan.")
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
    print(f"[SeaLLM 7B] Model berhasil diunduh ke {target_path}")
    return target_path


def ensure_seallm_downloaded(
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Ensure SeaLLM-v3-7B GGUF model is downloaded and return its file path."""
    if is_seallm_installed(filename, model_dir):
        return get_seallm_model_path(filename, model_dir)
    return download_seallm_with_progress(filename=filename, model_dir=model_dir)


class SeaLLMTranslator:
    """
    Offline Southeast Asian / Indonesian translator powered by SeaLLMs-v3-7B GGUF.
    Produces rich, flowing Indonesian prose for light novels.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_threads: Optional[int] = None,
        n_ctx: int = 2048
    ):
        if not model_path:
            model_path = ensure_seallm_downloaded()

        # Reserve at least 1 core for OS / FastAPI server responsiveness
        cpu_threads = n_threads or min(4, max(1, (os.cpu_count() or 4) - 1))
        print(f"[SeaLLM 7B] Memuat model {os.path.basename(model_path)} (threads={cpu_threads}, ctx={n_ctx})...")
        self.llm = Llama(
            model_path=model_path,
            n_threads=cpu_threads,
            n_ctx=n_ctx,
            n_batch=512,
            verbose=False
        )
        print("[SeaLLM 7B] Model siap digunakan!")

    def _clean_output(self, raw: str, fallback_orig: str = "") -> str:
        """Strip conversational filler, meta-comments, or accidental refusal notes."""
        text = raw.strip()

        # Check for LLM meta-chatter / refusal hallucinations
        meta_patterns = [
            r"^(Teks ini|Teks di atas|Kalimat ini)\s+sudah\s+(dalam\s+)?bahasa\s+indonesia.*$",
            r"^.*tidak\s+perlu\s+diterjemahkan.*$",
            r"^.*tidak\s+perlu\s+terjemahan.*$",
            r"^(Catatan|Note|Terjemahan|Hasil terjemahan|Artinya)\s*:\s*",
            r"^Berikut\s+(adalah\s+)?hasil\s+terjemahan.*:\s*",
            r"^Here\s+is\s+the\s+translation.*:\s*",
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

    def translate_single_en_to_id(self, text: str) -> str:
        """Translate a single English sentence or title to Indonesian."""
        if not text or not text.strip():
            return ""

        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_EN_ID}<|im_end|>\n"
            f"<|im_start|>user\n{text.strip()}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        output = self.llm(
            prompt,
            max_tokens=512,
            temperature=0.25,
            top_p=0.9,
            stop=["<|im_end|>", "<|endoftext|>"]
        )

        return self._clean_output(output["choices"][0]["text"], fallback_orig=text)

    def translate_en_to_id(
        self,
        texts: List[str],
        batch_size: int = 5,
        progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Translate English texts to Indonesian using chunked batching.
        Empty strings are returned as empty strings.
        """
        results = [""] * len(texts)
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]

        if not valid_indices:
            return results

        total = len(valid_indices)
        processed = 0

        chunk_size = max(1, min(batch_size, 2))
        for b_start in range(0, total, chunk_size):
            time.sleep(0.03)  # Yield CPU to allow FastAPI event loop to handle polling
            batch_idxs = valid_indices[b_start : b_start + chunk_size]
            batch_texts = [texts[idx].strip() for idx in batch_idxs]

            if len(batch_texts) == 1:
                results[batch_idxs[0]] = self.translate_single_en_to_id(batch_texts[0])
            else:
                numbered_input = "\n".join([f"[{i+1}] {t}" for i, t in enumerate(batch_texts)])
                prompt = (
                    f"<|im_start|>system\n{SYSTEM_PROMPT_EN_ID}\n"
                    "Format output WAJIB bernomor sama:\n"
                    "[1] <hasil terjemahan 1>\n"
                    "[2] <hasil terjemahan 2>\n"
                    "DILARANG menulis komentar apapun selain nomor dan teks terjemahan.<|im_end|>\n"
                    f"<|im_start|>user\n{numbered_input}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )

                try:
                    output = self.llm(
                        prompt,
                        max_tokens=min(2048, 250 * len(batch_texts)),
                        temperature=0.25,
                        top_p=0.9,
                        stop=["<|im_end|>", "<|endoftext|>"]
                    )
                    raw_out = output["choices"][0]["text"].strip()
                    parsed = re.findall(r"\[(\d+)\]\s*(.*?)(?=(?:\n\s*\[\d+\])|\Z)", raw_out, flags=re.DOTALL)
                    parsed_dict = {int(num): text.strip() for num, text in parsed}

                    if len(parsed_dict) == len(batch_texts):
                        for i, idx in enumerate(batch_idxs):
                            results[idx] = self._clean_output(parsed_dict.get(i + 1, ""), fallback_orig=batch_texts[i])
                    else:
                        for i, idx in enumerate(batch_idxs):
                            results[idx] = self.translate_single_en_to_id(batch_texts[i])
                except Exception:
                    for i, idx in enumerate(batch_idxs):
                        results[idx] = self.translate_single_en_to_id(batch_texts[i])

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
            print("[SeaLLM 7B] Model di-unload dari RAM.")
