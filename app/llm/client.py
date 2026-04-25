from llama_index.core.llms import LLM
from llama_index.llms.openai_like import OpenAILike

from app.config import Settings

_CEREBRAS_CTX = {
    "llama3.1-8b": 8_192,
    "llama-3.3-70b": 128_000,
    "qwen-3-235b-a22b-instruct-2507": 65_536,
}

_GEMINI_CTX = {
    "gemini-3-flash-preview": 1_048_576,
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.5-flash-preview-04-17": 1_048_576,
    "gemini-2.0-flash": 1_048_576,
}


def _make_cerebras(settings: Settings) -> OpenAILike:
    return OpenAILike(
        model=settings.cerebras_model,
        api_base=settings.cerebras_base_url,
        api_key=settings.cerebras_api_key,
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=_CEREBRAS_CTX.get(settings.cerebras_model, 8_192),
        # Disable the OpenAI SDK's built-in retry (it waits 59s on 429).
        # Our chat_with_retry wrapper handles retries with proper backoff.
        max_retries=0,
    )


def _make_gemini(settings: Settings) -> LLM:
    from llama_index.llms.google_genai import GoogleGenAI

    return GoogleGenAI(
        model=settings.gemini_llm_model,
        api_key=settings.gemini_api_key,
        context_window=_GEMINI_CTX.get(settings.gemini_llm_model, 1_048_576),
    )


def make_llm(settings: Settings) -> LLM:
    """Return the configured LLM — swappable via LLM_PROVIDER env var."""
    if settings.llm_provider == "gemini":
        return _make_gemini(settings)
    return _make_cerebras(settings)
