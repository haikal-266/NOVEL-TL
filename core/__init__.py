from .scraper import (
    KakuyomuScraper,
    parse_kakuyomu_url,
    SyosetuScraper,
    parse_syosetu_url,
    parse_novel_url,
    get_novel_scraper,
)
from .cache_manager import CacheManager
from .epub_builder import EPUBBuilder, clean_english_text
from .translators.sugoi import SugoiTranslator

def __getattr__(name: str):
    if name == "SeaLLMTranslator":
        from .translators.seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "QwenTranslator":
        from .translators.seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "LLMTranslator":
        from .translators.llm import LLMTranslator
        return LLMTranslator
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "KakuyomuScraper",
    "parse_kakuyomu_url",
    "SyosetuScraper",
    "parse_syosetu_url",
    "parse_novel_url",
    "get_novel_scraper",
    "CacheManager",
    "EPUBBuilder",
    "clean_english_text",
    "SugoiTranslator",
    "SeaLLMTranslator",
    "LLMTranslator",
    "QwenTranslator"
]
