"""
Sugoi V4 CTranslate2 Translator
High-speed, offline Japanese-to-English translation tuned for light novels and visual novels.
"""

import os
import sys
import time
import urllib.request
from typing import List, Optional, Callable
import ctranslate2
import sentencepiece as spm

MODEL_REPO = "entai2965/sugoi-v4-ja-en-ctranslate2"
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "sugoi_v4")

MODEL_FILES = [
    "config.json",
    "source_vocabulary.json",
    "target_vocabulary.json",
    "spm/spm.ja.nopretok.model",
    "spm/spm.ja.nopretok.vocab",
    "spm/spm.en.nopretok.model",
    "spm/spm.en.nopretok.vocab",
    "model.bin"
]

def ensure_model_downloaded(model_dir: str = DEFAULT_MODEL_DIR) -> str:
    """Ensure all required Sugoi model files are downloaded."""
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(os.path.join(model_dir, "spm"), exist_ok=True)

    base_url = f"https://huggingface.co/{MODEL_REPO}/resolve/main"

    for rel_path in MODEL_FILES:
        dest_path = os.path.join(model_dir, rel_path.replace("/", os.sep))
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            continue

        url = f"{base_url}/{rel_path}"
        print(f"[Sugoi] Downloading {rel_path}...")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(dest_path + ".tmp", "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024
            last_print = 0
            t0 = time.time()
            
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if time.time() - last_print > 3:
                    pct = (downloaded / total * 100) if total else 0
                    speed = downloaded / max(time.time() - t0, 0.1) / (1024 * 1024)
                    print(f"  {downloaded / (1024*1024):.1f}MB / {total / (1024*1024):.1f}MB ({pct:.1f}%) @ {speed:.2f} MB/s")
                    last_print = time.time()

        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(dest_path + ".tmp", dest_path)

    return model_dir


class SugoiTranslator:
    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR, device: str = "auto"):
        self.model_dir = os.path.abspath(model_dir)
        ensure_model_downloaded(self.model_dir)

        # Decide device and compute type
        chosen_device = device
        if chosen_device == "auto":
            chosen_device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"

        # Try initializing with chosen device, fall back to CPU if cublas/cuda libraries missing
        try:
            compute_type = "float16" if chosen_device == "cuda" else "int8"
            self.translator = ctranslate2.Translator(
                self.model_dir,
                device=chosen_device,
                compute_type=compute_type
            )
            self.device = chosen_device
            self.compute_type = compute_type
        except Exception as e:
            if chosen_device == "cuda":
                print(f"[Sugoi] CUDA init failed ({e}), falling back to CPU (int8)...")
                self.translator = ctranslate2.Translator(
                    self.model_dir,
                    device="cpu",
                    compute_type="int8"
                )
                self.device = "cpu"
                self.compute_type = "int8"
            else:
                raise e

        # Load sentencepiece tokenizers
        spm_ja = os.path.join(self.model_dir, "spm", "spm.ja.nopretok.model")
        spm_en = os.path.join(self.model_dir, "spm", "spm.en.nopretok.model")
        self.sp_source = spm.SentencePieceProcessor(spm_ja)
        self.sp_target = spm.SentencePieceProcessor(spm_en)

        # Warmup test to verify if CUDA runtime / cuBLAS actually works on this system
        if self.device == "cuda":
            try:
                dummy = [self.sp_source.encode("テスト", out_type=str)]
                self.translator.translate_batch(dummy)
            except Exception as e:
                print(f"[Sugoi] CUDA runtime check failed ({e}), falling back to CPU (int8)...")
                self.translator = ctranslate2.Translator(
                    self.model_dir,
                    device="cpu",
                    compute_type="int8"
                )
                self.device = "cpu"
                self.compute_type = "int8"

    def translate_texts(
        self,
        texts: List[str],
        batch_size: int = 16,
        progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Translate a list of Japanese texts/paragraphs to English.
        Empty texts are returned as empty strings without invoking the model.
        """
        results = [""] * len(texts)
        
        # Identify non-empty items
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices:
            return results

        total = len(valid_indices)
        processed = 0

        for b_start in range(0, len(valid_indices), batch_size):
            batch_idxs = valid_indices[b_start : b_start + batch_size]
            batch_texts = [texts[idx].strip() for idx in batch_idxs]

            # Tokenize
            tokenized_batch = [self.sp_source.encode(t, out_type=str) for t in batch_texts]

            # Translate
            outputs = self.translator.translate_batch(
                tokenized_batch,
                beam_size=3,
                max_batch_size=batch_size
            )

            # Decode
            for idx, out in zip(batch_idxs, outputs):
                hyp = out.hypotheses[0]
                decoded = self.sp_target.decode(hyp).replace("<unk>", "").strip()
                results[idx] = decoded

            processed += len(batch_idxs)
            if progress_cb:
                progress_cb(processed, total)

        return results

    def translate_single(self, text: str) -> str:
        """Translate a single sentence or title."""
        if not text or not text.strip():
            return ""
        res = self.translate_texts([text], batch_size=1)
        return res[0]
