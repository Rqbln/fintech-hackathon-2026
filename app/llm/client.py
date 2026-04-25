from llama_index.llms.openai_like import OpenAILike

from app.config import Settings


def make_llm(settings: Settings) -> OpenAILike:
    return OpenAILike(
        model=settings.z_ai_model,
        api_base=settings.z_ai_base_url,
        api_key=settings.z_ai_api_key,
        is_chat_model=True,
        is_function_calling_model=True,
        context_window=200_000,
    )
