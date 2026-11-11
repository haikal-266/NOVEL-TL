from typing import TYPE_CHECKING

def __getattr__(name: str):
    if name == "SugoiTranslator":
        from .sugoi import SugoiTranslator
        return SugoiTranslator
    if name == "SeaLLMTranslator":
        from .seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "QwenTranslator":
        # Kept for backward compatibility, mapped to SeaLLMTranslator
        from .seallm import SeaLLMTranslator
        return SeaLLMTranslator
    if name == "LLMTranslator":
        from .llm import LLMTranslator
        return LLMTranslator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["SugoiTranslator", "SeaLLMTranslator", "QwenTranslator", "LLMTranslator"]
