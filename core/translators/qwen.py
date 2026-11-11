"""
Qwen 2.5 GGUF Translator (JP -> ID)
Offline Japanese-to-Indonesian light novel translation via llama.cpp.
Tuned for CPU & Helio G99 execution (n_threads=4, n_ctx=2048).
"""

import os
import re
import gc
from typing import List, Optional, Callable
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

DEFAULT_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
DEFAULT_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "qwen")

SYSTEM_PROMPT = (
    "Anda adalah penerjemah novel profesional bahasa Jepang ke bahasa Indonesia.\n"
    "Tugas: Terjemahkan teks novel Jepang berikut ke dalam bahasa Indonesia novel yang alami, mengalir, dan mudah dipahami.\n"
    "Aturan ketat:\n"
    "1. Pertahankan konsistensi nama karakter dan dialog.\n"
    "2. HANYA berikan teks hasil terjemahan langsung.\n"
    "3. DILARANG memberikan teks pembuka, penjelasan, terjemahan alternatif, atau catatan kaki."
)

SYSTEM_PROMPT_EN_ID = (
    "Kamu adalah editor dan penerjemah novel fiksi profesional berbahasa Indonesia. "
    "Terjemahkan teks bahasa Inggris berikut ke bahasa Indonesia yang luwes, emosional, dan alami layaknya novel terbitan Gramedia. "
    "Hindari terjemahan kaku kata per kata, ubah idiom bahasa Inggris menjadi padanan yang wajar di telinga pembaca Indonesia, "
    "dan gunakan kata ganti 'aku-kamu' untuk dialog akrab. Pastikan ritme kalimat terasa hidup.\n"
    "Aturan ketat:\n"
    "1. HANYA berikan hasil terjemahan langsung tanpa teks pembuka, tanpa pengantar, dan tanpa catatan/penjelasan apapun.\n"
    "2. Pertahankan keutuhan alur cerita dan emosi setiap adegan."
)


def ensure_qwen_downloaded(
    repo_id: str = DEFAULT_REPO,
    filename: str = DEFAULT_FILENAME,
    model_dir: str = DEFAULT_MODEL_DIR
) -> str:
    """Ensure Qwen GGUF model is downloaded and return its file path."""
    os.makedirs(model_dir, exist_ok=True)
    target_path = os.path.join(model_dir, filename)

    if os.path.exists(target_path) and os.path.getsize(target_path) > 100 * 1024 * 1024:
        return target_path

    print(f"[Qwen GGUF] Mengunduh model {filename} dari Hugging Face ({repo_id})...")
    downloaded_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=model_dir
    )
    return downloaded_path


class QwenTranslator:
    """
    Offline Japanese-to-Indonesian translator powered by Qwen 2.5 GGUF.
    Optimized for lightweight execution on CPU (Helio G99 / Desktop CPU).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_threads: int = 4,
        n_ctx: int = 2048
    ):
        if not model_path:
            model_path = ensure_qwen_downloaded()

        print(f"[Qwen GGUF] Memuat model {os.path.basename(model_path)} (threads={n_threads}, ctx={n_ctx})...")
        self.llm = Llama(
            model_path=model_path,
            n_threads=n_threads,
            n_ctx=n_ctx,
            n_batch=512,
            verbose=False
        )
        print("[Qwen GGUF] Model siap digunakan!")

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

    def translate_single(self, text: str) -> str:
        """Translate a single sentence or title."""
        if not text or not text.strip():
            return ""

        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{text.strip()}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        output = self.llm(
            prompt,
            max_tokens=512,
            temperature=0.2,
            top_p=0.9,
            stop=["<|im_end|>", "<|endoftext|>"]
        )

        raw_text = output["choices"][0]["text"]
        return self._clean_output(raw_text)

    def translate_texts(
        self,
        texts: List[str],
        batch_size: int = 5,
        progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Translate a list of paragraphs to Indonesian with chunked batching.
        Empty paragraphs are returned as empty strings.
        """
        results = [""] * len(texts)
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]

        if not valid_indices:
            return results

        total = len(valid_indices)
        processed = 0

        # Chunk paragraphs for faster inference and better narrative context
        chunk_size = max(1, min(batch_size, 8))
        for b_start in range(0, total, chunk_size):
            batch_idxs = valid_indices[b_start : b_start + chunk_size]
            batch_texts = [texts[idx].strip() for idx in batch_idxs]

            if len(batch_texts) == 1:
                results[batch_idxs[0]] = self.translate_single(batch_texts[0])
            else:
                numbered_input = "\n".join([f"[{i+1}] {t}" for i, t in enumerate(batch_texts)])
                prompt = (
                    f"<|im_start|>system\n{SYSTEM_PROMPT}\n"
                    "Format output WAJIB bernomor sama:\n"
                    "[1] <hasil terjemahan 1>\n"
                    "[2] <hasil terjemahan 2>\n"
                    "DILARANG menulis apapun selain nomor dan terjemahan langsung.<|im_end|>\n"
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
                            results[idx] = self._clean_output(parsed_dict.get(i + 1, ""))
                    else:
                        for i, idx in enumerate(batch_idxs):
                            results[idx] = self.translate_single(batch_texts[i])
                except Exception as e:
                    for i, idx in enumerate(batch_idxs):
                        results[idx] = self.translate_single(batch_texts[i])

            processed += len(batch_idxs)
            if progress_cb:
                progress_cb(processed, total)

        return results

    def translate_single_en_to_id(self, text: str) -> str:
        """Translate a single English sentence/title to Indonesian."""
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
            temperature=0.2,
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

        chunk_size = max(1, min(batch_size, 6))
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
                        temperature=0.2,
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
            print("[Qwen GGUF] Model di-unload dari RAM.")

