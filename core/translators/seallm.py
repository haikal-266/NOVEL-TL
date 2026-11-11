"""
SeaLLM-v3-7B GGUF Translator (EN -> ID / JP -> ID)
Offline Indonesian novel translator powered by SeaLLMs-v3-7B via llama.cpp.
Tuned for natural, literary Southeast Asian / Indonesian phrasing.
"""

import os
import re
import gc
from typing import List, Optional, Callable
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

DEFAULT_REPO = "QuantFactory/SeaLLMs-v3-7B-Chat-GGUF"
DEFAULT_FILENAME = "SeaLLMs-v3-7B-Chat.Q4_K_M.gguf"
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


def ensure_seallm_downloaded(
    repo_id: str = DEFAULT_REPO,
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Ensure SeaLLM-v3-7B GGUF model is downloaded and return its file path."""
    os.makedirs(model_dir, exist_ok=True)
    target_path = os.path.join(model_dir, filename)

    if os.path.exists(target_path) and os.path.getsize(target_path) > 100 * 1024 * 1024:
        return target_path

    print(f"[SeaLLM 7B] Mengunduh model {filename} dari Hugging Face ({repo_id})...")
    downloaded_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=model_dir
    )
    return downloaded_path


class SeaLLMTranslator:
    """
    Offline Southeast Asian / Indonesian translator powered by SeaLLMs-v3-7B GGUF.
    Produces rich, flowing Indonesian prose for light novels.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_threads: int = 4,
        n_ctx: int = 2048
    ):
        if not model_path:
            model_path = ensure_seallm_downloaded()

        print(f"[SeaLLM 7B] Memuat model {os.path.basename(model_path)} (threads={n_threads}, ctx={n_ctx})...")
        self.llm = Llama(
            model_path=model_path,
            n_threads=n_threads,
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

        chunk_size = max(1, min(batch_size, 5))
        for b_start in range(0, total, chunk_size):
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

