from typing import TYPE_CHECKING

def __getattr__(name: str):
    if name == "NovelJPTranslator":
        from .novel_jp import NovelJPTranslator
        return NovelJPTranslator
    if name == "SugoiTranslator":
        from .sugoi import SugoiTranslator
        return SugoiTranslator
    if name == "MarianIDTranslator":
        from .marian_id import MarianIDTranslator
        return MarianIDTranslator
    if name == "SeaLLMTranslator":
        from .seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "LLMTranslator":
        from .llm import LLMTranslator
        return LLMTranslator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["NovelJPTranslator", "SugoiTranslator", "MarianIDTranslator", "SeaLLMTranslator", "LLMTranslator"]
