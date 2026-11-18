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
from .glossary import GlossaryManager, get_glossary_manager
from .dataset_logger import DatasetLogger, get_dataset_logger

def __getattr__(name: str):
    if name == "SeaLLMTranslator":
        from .translators.seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "LLMTranslator":
        from .translators.llm import LLMTranslator
        return LLMTranslator
    if name == "GeminiTranslator":
        from .translators.gemini_translator import GeminiTranslator
        return GeminiTranslator
    if name == "get_gemini_translator":
        from .translators.gemini_translator import get_gemini_translator
        return get_gemini_translator
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
    "GeminiTranslator",
    "get_gemini_translator",
    "DatasetLogger",
    "get_dataset_logger",
    "GlossaryManager",
    "get_glossary_manager"
]
