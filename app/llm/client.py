from llama_index.llms.openai_like import OpenAILike

from app.config import Settings

# Context windows by model (used as a hint for LlamaIndex internals)
_CONTEXT_WINDOWS = {
    "llama3.1-8b": 8_192,
    "qwen-3-235b-a22b-instruct-2507": 65_536,
}
_DEFAULT_CONTEXT = 32_768


def make_llm(settings: Settings) -> OpenAILike:
    """Analysis / remediation / report LLM — llama3.1-8b (100 RPM)."""
    return OpenAILike(
        model=settings.cerebras_model,
        api_base=settings.cerebras_base_url,
        api_key=settings.cerebras_api_key,
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=_CONTEXT_WINDOWS.get(settings.cerebras_model, _DEFAULT_CONTEXT),
    )


def make_extraction_llm(settings: Settings) -> OpenAILike:
    """Extraction-only LLM — qwen-3-235b (65k context, 1 call per contract)."""
    return OpenAILike(
        model=settings.cerebras_extraction_model,
        api_base=settings.cerebras_base_url,
        api_key=settings.cerebras_api_key,
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=_CONTEXT_WINDOWS.get(settings.cerebras_extraction_model, _DEFAULT_CONTEXT),
    )
