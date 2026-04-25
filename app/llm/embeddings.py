from google.genai import types as genai_types
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

from app.config import Settings


def make_embed_model(settings: Settings) -> GoogleGenAIEmbedding:
    """Return Gemini Embedding 2 with MRL dimension reduction to settings.gemini_embed_dim."""
    embedding_config = genai_types.EmbedContentConfig(
        output_dimensionality=settings.gemini_embed_dim,
    )
    return GoogleGenAIEmbedding(
        model_name=settings.gemini_embed_model,
        api_key=settings.gemini_api_key,
        embed_batch_size=100,
        embedding_config=embedding_config,
    )
