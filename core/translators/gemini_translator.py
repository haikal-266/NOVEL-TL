"""
Google Gemini Flash Translator
High-speed, literary-grade translation engine using Google AI Studio Free Tier.
Direct Japanese -> Indonesian or Japanese -> English.
Passively logs translation pairs to the parallel dataset for future offline fine-tuning.
"""

import os
import re
import json
import time
import requests
from typing import List, Dict, Optional, Callable, Any

from core.dataset_logger import get_dataset_logger

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.json"))
DEFAULT_API_KEY = ""

def load_gemini_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_gemini_config(config_data: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[GeminiTranslator] Failed to save config: {e}")

class GeminiTranslator:
    def __init__(self, api_key: Optional[str] = None):
        cfg = load_gemini_config()
        self.api_keys: List[str] = []
        if api_key:
            self.api_keys = [api_key.strip()]
        elif cfg.get("gemini_api_keys") and isinstance(cfg["gemini_api_keys"], list):
            self.api_keys = [k.strip() for k in cfg["gemini_api_keys"] if k and k.strip()]
        elif os.environ.get("GEMINI_API_KEY"):
            self.api_keys = [os.environ["GEMINI_API_KEY"].strip()]
        elif cfg.get("gemini_api_key"):
            self.api_keys = [cfg["gemini_api_key"].strip()]
        else:
            self.api_keys = []

        self.current_key_idx = 0
        self.models = [
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3-flash-preview",
            "gemini-3.5-flash-lite"
        ]
        self.dataset_logger = get_dataset_logger()

    @property
    def api_key(self) -> str:
        if not self.api_keys:
            return DEFAULT_API_KEY
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def update_api_key(self, new_key: str) -> None:
        key_clean = new_key.strip()
        if key_clean not in self.api_keys:
            self.api_keys.append(key_clean)
        self.current_key_idx = self.api_keys.index(key_clean)
        cfg = load_gemini_config()
        cfg["gemini_api_key"] = key_clean
        cfg["gemini_api_keys"] = self.api_keys
        save_gemini_config(cfg)

    def _call_gemini_api(self, prompt: str, timeout: int = 35) -> str:
        """Call Gemini API with multi-key rotation, model fallback, and automatic retry on rate limit."""
        if not self.api_keys:
            raise RuntimeError(
                "Google Gemini API Key belum dikonfigurasi. "
                "Silakan masukkan API key Anda di config.json atau set environment variable GEMINI_API_KEY."
            )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3
            }
        }
        last_error = ""

        # Try across all configured API keys
        total_keys = max(1, len(self.api_keys))
        for key_offset in range(total_keys):
            active_key = self.api_keys[(self.current_key_idx + key_offset) % total_keys]
            
            for model in self.models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={active_key}"
                for attempt in range(2):
                    try:
                        resp = requests.post(url, json=payload, timeout=timeout)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    # Set this successful key as current default
                                    self.current_key_idx = (self.current_key_idx + key_offset) % total_keys
                                    return parts[0]["text"]
                        elif resp.status_code == 429:
                            # Quota exhausted or rate limited on this key -> switch to next key if available
                            last_error = f"HTTP 429 (Rate/Quota limit pada key {active_key[:6]}...)"
                            time.sleep(1.0)
                            break  # Break inner loop to try next model or next key
                        elif resp.status_code == 503:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        else:
                            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    except Exception as e:
                        last_error = str(e)
                        time.sleep(1.0)

        raise RuntimeError(f"Gagal memanggil API Gemini Flash: {last_error}")

    def translate_texts(
        self,
        texts: List[str],
        target_lang: str = "id",
        chunk_size: int = 25,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        work_id: str = "",
        ep_id: str = "",
        chap_index: int = 0
    ) -> List[str]:
        """
        Translates a list of paragraphs in chunks.
        Automatically logs non-blank parallel translation pairs to the dataset.
        """
        results = [""] * len(texts)
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices:
            return results

        total = len(valid_indices)
        processed = 0

        for start in range(0, len(valid_indices), chunk_size):
            chunk_idxs = valid_indices[start : start + chunk_size]
            prompt_lines = []
            for num, idx in enumerate(chunk_idxs, start=1):
                clean_text = texts[idx].strip()
                prompt_lines.append(f"[p{num}] {clean_text}")

            if target_lang.lower().startswith("id"):
                system_instruction = (
                    "Anda adalah penerjemah sastra profesional spesialis novel ringan (light novel) dan web novel Jepang ke bahasa Indonesia (standar penerbitan resmi Gramedia/Phoenix Gramedia).\n\n"
                    "Pedoman penting:\n"
                    "1. Terjemahkan secara akurat, alami, luwes, dan sastrawi. Hindari terjemahan kaku kata-per-kata.\n"
                    "2. Gunakan sudut pandang orang pertama 'aku'/'-ku', dan lawan bicara 'kamu'/'kau' sesuai keakraban konteks.\n"
                    "3. Percakapan dalam tanda petik 「...」 atau \"...\" harus menggunakan bahasa dialog yang hidup dan berkarakter.\n"
                    "4. JANGAN menghilangkan nama karakter, kata dalam daftar nama, atau bagian cerita apa pun.\n"
                    "5. Kembalikan teks terjemahan dalam format bernomor yang persis:\n"
                    "[p1] Teks terjemahan paragraf 1\n"
                    "[p2] Teks terjemahan paragraf 2\n\n"
                    "Teks Sumber Jepang:\n"
                )
            else:
                system_instruction = (
                    "You are a professional Japanese light novel translator specializing in high-grade English localization.\n\n"
                    "Guidelines:\n"
                    "1. Translate faithfully into fluent, engaging, natural English prose.\n"
                    "2. Preserve dialogue nuance and character voices.\n"
                    "3. Do not omit any names, dialogue lines, or sentences.\n"
                    "4. Return exactly matching numbered paragraphs:\n"
                    "[p1] Translated paragraph 1\n"
                    "[p2] Translated paragraph 2\n\n"
                    "Japanese source text:\n"
                )

            full_prompt = system_instruction + "\n".join(prompt_lines)
            raw_response = self._call_gemini_api(full_prompt)

            # Parse numbered [p1], [p2]
            parsed_chunks: Dict[int, str] = {}
            current_num = None
            current_text: List[str] = []

            for line in raw_response.splitlines():
                line_str = line.strip()
                m = re.match(r"^\[p?(\d+)\]\s*(.*)$", line_str, re.IGNORECASE)
                if m:
                    if current_num is not None:
                        parsed_chunks[current_num] = " ".join(current_text).strip()
                    current_num = int(m.group(1))
                    current_text = [m.group(2)] if m.group(2) else []
                elif current_num is not None:
                    if line_str:
                        current_text.append(line_str)

            if current_num is not None:
                parsed_chunks[current_num] = " ".join(current_text).strip()

            # Assign and log
            pairs_to_log = []
            for num, idx in enumerate(chunk_idxs, start=1):
                ja_orig = texts[idx].strip()
                if num in parsed_chunks and parsed_chunks[num]:
                    tl_out = parsed_chunks[num]
                else:
                    # Fallback single
                    tl_out = self.translate_single(ja_orig, target_lang=target_lang, work_id=work_id)

                results[idx] = tl_out

                # Prepare dataset logging record
                if ja_orig and tl_out:
                    if target_lang.lower().startswith("id"):
                        pairs_to_log.append({
                            "ja": ja_orig,
                            "id": tl_out,
                            "en": "",
                            "work_id": work_id,
                            "chapter_id": ep_id,
                            "chapter_index": chap_index,
                            "p_index": idx + 1,
                            "model": "gemini-flash"
                        })
                    else:
                        pairs_to_log.append({
                            "ja": ja_orig,
                            "id": "",
                            "en": tl_out,
                            "work_id": work_id,
                            "chapter_id": ep_id,
                            "chapter_index": chap_index,
                            "p_index": idx + 1,
                            "model": "gemini-flash"
                        })

            if pairs_to_log:
                try:
                    self.dataset_logger.log_pairs(pairs_to_log)
                except Exception as log_err:
                    print(f"[GeminiTranslator] Dataset logging notice: {log_err}")

            processed += len(chunk_idxs)
            if progress_cb:
                progress_cb(processed, total)

        return results

    def translate_single(self, text: str, target_lang: str = "id", work_id: str = "") -> str:
        clean = (text or "").strip()
        if not clean:
            return ""

        if target_lang.lower().startswith("id"):
            prompt = (
                "Terjemahkan frasa/kalimat novel ringan Jepang ini ke bahasa Indonesia sastra penerbitan resmi. "
                "Langsung berikan hasil terjemahannya saja tanpa penjelasan, pembuka, atau tanda kutip tambahan:\n"
                f"{clean}"
            )
        else:
            prompt = (
                "Translate this Japanese light novel phrase/sentence into clean, natural English. "
                "Return only the direct translation with no explanations or extra quotes:\n"
                f"{clean}"
            )

        try:
            res = self._call_gemini_api(prompt, timeout=15)
            # Remove possible formatting quirks
            res = re.sub(r'^(Terjemahan:\s*|Translation:\s*|"|\')', '', res.strip(), flags=re.IGNORECASE)
            res = re.sub(r'("|\')$', '', res.strip())
            return res.strip()
        except Exception:
            return clean

_gemini_translator_instance = None

def get_gemini_translator(api_key: Optional[str] = None) -> GeminiTranslator:
    global _gemini_translator_instance
    if _gemini_translator_instance is None or api_key:
        _gemini_translator_instance = GeminiTranslator(api_key=api_key)
    return _gemini_translator_instance
