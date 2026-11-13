"""
Sugoi V4 CTranslate2 Translator
High-speed, offline Japanese-to-English translation tuned for light novels and visual novels.
"""

import os
import sys
import time
import re
import urllib.request
from typing import List, Dict, Tuple, Optional, Callable
import ctranslate2
import sentencepiece as spm
from core.speech_markers import correct_pronoun_gender

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


def split_japanese_sentences(text: str) -> List[str]:
    """
    Split a Japanese text/paragraph into individual sentences for NMT translation.
    Protects dialogue quotes 「...」 and 『...』 so sentences inside quotes are not broken apart.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # If the entire line is a single dialogue, keep as one unit
    if (text.startswith("「") and text.endswith("」")) or (text.startswith("『") and text.endswith("』")):
        return [text]

    tokens = []
    current = ""
    in_quote = False
    quote_char = ""

    for ch in text:
        current += ch
        if ch in ("「", "『"):
            in_quote = True
            quote_char = "」" if ch == "「" else "』"
        elif in_quote and ch == quote_char:
            in_quote = False
        elif not in_quote and ch in ("。", "！", "？", "\n"):
            tokens.append(current.strip())
            current = ""

    if current.strip():
        tokens.append(current.strip())

    result = [t for t in tokens if t]
    return result if result else [text]


def clean_dialogue_and_narration(ja_text: str, en_text: str) -> str:
    """
    Enforces strict quotation accuracy:
    - If JA has NO quotes, EN must NOT have hallucinated quotes.
    - If JA is a full dialogue line, EN MUST have matching quotes.
    - Normalizes all quote marks to standard ASCII double quotes.
    """
    ja = ja_text.strip()
    en = en_text.strip()

    # Normalize quotes
    en = en.replace("「", '"').replace("」", '"')
    en = en.replace("“", '"').replace("”", '"')
    en = en.replace("『", '"').replace("』", '"')
    en = en.replace("’", "'").replace("‘", "'")

    has_ja_quotes = ("「" in ja) or ("『" in ja)
    is_ja_full_dialogue = (ja.startswith("「") and ja.endswith("」")) or \
                          (ja.startswith("『") and ja.endswith("』"))

    if not has_ja_quotes:
        # Case 1: Pure narrative. Strip any hallucinated quotes/apologies from Sugoi!
        en = re.sub(r'^"[^"]*"\s*', '', en)
        en = en.replace('"', '').strip()
        return en

    if is_ja_full_dialogue:
        # Case 2: Pure dialogue line. Ensure it is cleanly wrapped with quotes.
        inner = en.strip('"').strip()
        inner = re.sub(r'^-+\s*', '', inner).strip()
        return f'"{inner}"'

    # Case 3: Mixed dialogue + narration (e.g. 「何してるの？」と彼女は尋ねた。)
    if en.count('"') % 2 != 0:
        en = en + '"'

    return en


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
        - Splits multi-sentence paragraphs into individual sentence units to prevent NMT hallucinations.
        - Batches all units concurrently for ultra-fast CTranslate2 inference.
        - Protects dialogue quotes (Dialogue Quote Guard).
        - Corrects misidentified gender pronouns using Japanese speech markers.
        """
        results = [""] * len(texts)

        # Expand non-empty paragraphs into sentence units, keeping track of paragraph index
        unit_map: List[Tuple[int, str]] = []
        for idx, text in enumerate(texts):
            if text and text.strip():
                units = split_japanese_sentences(text)
                for u in units:
                    unit_map.append((idx, u))

        if not unit_map:
            return results

        total_units = len(unit_map)
        processed_units = 0
        translated_units: List[str] = [""] * total_units

        # Translate in batches
        for b_start in range(0, total_units, batch_size):
            b_end = min(b_start + batch_size, total_units)
            batch_items = unit_map[b_start:b_end]
            batch_texts = [item[1] for item in batch_items]

            # Tokenize
            tokenized_batch = [self.sp_source.encode(t, out_type=str) for t in batch_texts]

            # Translate using optimal Sugoi V4 beam search and anti-repetition settings
            outputs = self.translator.translate_batch(
                tokenized_batch,
                beam_size=5,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                replace_unknowns=True,
                max_batch_size=batch_size
            )

            # Decode
            for i, out in enumerate(outputs):
                hyp = out.hypotheses[0]
                decoded = self.sp_target.decode(hyp).replace("<unk>", "").strip()
                translated_units[b_start + i] = decoded

            processed_units += len(batch_items)
            if progress_cb:
                progress_cb(processed_units, total_units)

        # Post-process and group units back into paragraphs
        para_units_map: Dict[int, List[str]] = {}
        for (para_idx, ja_unit), en_unit in zip(unit_map, translated_units):
            # Apply dialogue quote guard
            cleaned_en = clean_dialogue_and_narration(ja_unit, en_unit)
            # Apply speech marker gender correction
            gender_en = correct_pronoun_gender(ja_unit, cleaned_en)

            # Ensure sentence has terminal punctuation if Japanese sentence ended with punctuation
            if ja_unit.endswith(("。", "！", "？")) and not gender_en.endswith((".", "!", "?", '"', "'")):
                gender_en += "."

            if para_idx not in para_units_map:
                para_units_map[para_idx] = []
            para_units_map[para_idx].append(gender_en)

        # Assemble final paragraphs
        for para_idx, unit_list in para_units_map.items():
            joined = " ".join(unit_list)
            # Clean punctuation spacing: space before punctuation -> no space
            joined = re.sub(r'\s+([,.:;!?])', r'\1', joined)
            joined = re.sub(r'\s+', ' ', joined).strip()
            results[para_idx] = joined

        return results

    def translate_single(self, text: str) -> str:
        """Translate a single sentence or title."""
        if not text or not text.strip():
            return ""
        res = self.translate_texts([text], batch_size=1)
        return res[0]
