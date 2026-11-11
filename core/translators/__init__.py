from .sugoi import SugoiTranslator

def __getattr__(name: str):
    if name == "QwenTranslator":
        from .qwen import QwenTranslator
        return QwenTranslator
    if name == "LLMTranslator":
        from .llm import LLMTranslator
        return LLMTranslator
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["SugoiTranslator", "LLMTranslator", "QwenTranslator"]
