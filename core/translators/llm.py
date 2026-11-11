"""
Local LLM Translator (LM Studio / Ollama / OpenAI-compatible API)
Enables running Sugoi-14B-Ultra-GGUF, Qwen2.5, or other local models via LM Studio or Ollama.
Supports translating to English (EN) or Indonesian (ID).
"""

import json
import re
import urllib.request
import urllib.error
from typing import List, Optional, Callable

DEFAULT_API_URL = "http://localhost:1234/v1"  # LM Studio default port

SYSTEM_PROMPTS = {
    "en": (
        "You are an expert Japanese-to-English translator specializing in Japanese light novels, "
        "visual novels, and ACG media. Translate the provided numbered paragraphs faithfully, "
        "preserving emotional nuance, dialogue tone, and Japanese honorifics/conventions. "
        "Return each translated paragraph matching the format: [p{number}] Translated paragraph text."
    ),
    "id": (
        "Anda adalah penerjemah profesional bahasa Jepang ke bahasa Indonesia yang ahli dalam menerjemahkan "
        "novel ringan (light novel) dan fiksi remaja Jepang. Terjemahkan paragraf-paragraf bernomor berikut "
        "ke dalam bahasa Indonesia yang luwes, alami, dan enak dibaca, dengan tetap mempertahankan nuansa "
        "dialog dan emosi aslinya. Kembalikan setiap paragraf terjemahan sesuai format: [p{number}] Teks terjemahan."
    )
}

class LLMTranslator:
    def __init__(
        self,
        api_base: str = DEFAULT_API_URL,
        model_name: Optional[str] = None,
        target_lang: str = "en",
        temperature: float = 0.3
    ):
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name or "local-model"
        self.target_lang = "id" if target_lang.lower().startswith("id") else "en"
        self.temperature = temperature
        self._test_connection()

    def _test_connection(self) -> None:
        """Check if local LLM API server is reachable."""
        models_url = f"{self.api_base}/models"
        req = urllib.request.Request(models_url, headers={"User-Agent": "NovelTL/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "data" in data and len(data["data"]) > 0:
                    available = [m.get("id") for m in data["data"]]
                    if self.model_name == "local-model" or self.model_name not in available:
                        self.model_name = available[0]
                        print(f"[LLM] Connected to {self.api_base}! Active model: {self.model_name}")
        except Exception as e:
            print(f"[LLM] Notice: Could not query {models_url} ({e}). Proceeding with model '{self.model_name}'...")

    def _call_chat_completion(self, user_content: str) -> str:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPTS.get(self.target_lang, SYSTEM_PROMPTS["en"])},
                {"role": "user", "content": user_content}
            ],
            "temperature": self.temperature,
            "max_tokens": 4096
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "NovelTL/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json["choices"][0]["message"]["content"]
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to local LLM server at {self.api_base}.\n"
                f"Make sure LM Studio or Ollama is running with the local server enabled.\n"
                f"Details: {e}"
            )

    def translate_texts(
        self,
        texts: List[str],
        chunk_size: int = 15,
        progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Translate a list of paragraphs by chunking them to preserve context and speed up LLM inference.
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

            prompt = (
                f"Translate the following {len(chunk_idxs)} Japanese light novel paragraphs to {self.target_lang.upper()}:\n\n"
                + "\n".join(prompt_lines)
            )

            raw_response = self._call_chat_completion(prompt)

            # Parse numbered responses [p1], [p2]...
            parsed_chunks = {}
            lines = raw_response.splitlines()
            current_num = None
            current_text = []

            for line in lines:
                m = re.match(r"^\[p?(\d+)\]\s*(.*)$", line.strip(), re.IGNORECASE)
                if m:
                    if current_num is not None:
                        parsed_chunks[current_num] = " ".join(current_text).strip()
                    current_num = int(m.group(1))
                    current_text = [m.group(2)] if m.group(2) else []
                elif current_num is not None:
                    if line.strip():
                        current_text.append(line.strip())

            if current_num is not None:
                parsed_chunks[current_num] = " ".join(current_text).strip()

            # Assign to results
            for num, idx in enumerate(chunk_idxs, start=1):
                if num in parsed_chunks:
                    results[idx] = parsed_chunks[num]
                else:
                    # Fallback single translation if batch missed one
                    try:
                        fallback = self.translate_single(texts[idx])
                        results[idx] = fallback
                    except Exception:
                        results[idx] = texts[idx]

            processed += len(chunk_idxs)
            if progress_cb:
                progress_cb(processed, total)

        return results

    def translate_single(self, text: str) -> str:
        """Translate a single sentence or title."""
        if not text or not text.strip():
            return ""
        prompt = f"Translate this light novel title/sentence from Japanese to {self.target_lang.upper()}. Return ONLY the translation, without quotes:\n\n{text.strip()}"
        res = self._call_chat_completion(prompt)
        return res.strip().strip('"').strip("'")

