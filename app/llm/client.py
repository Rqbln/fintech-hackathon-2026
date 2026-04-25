from llama_index.llms.openai_like import OpenAILike

from app.config import Settings


def make_llm(settings: Settings) -> OpenAILike:
    """Cerebras inference — OpenAI-compatible, model zai-glm-4.7."""
    return OpenAILike(
        model=settings.cerebras_model,
        api_base=settings.cerebras_base_url,
        api_key=settings.cerebras_api_key,
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=128_000,
    )
