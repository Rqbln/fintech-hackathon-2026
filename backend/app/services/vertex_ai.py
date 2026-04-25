"""Vertex AI client for Gemini generation and text embeddings."""

import vertexai
from vertexai.generative_models import GenerativeModel

from app.config import EMBEDDING_MODEL, GCP_PROJECT, GCP_REGION, GEMINI_MODEL

_initialized = False


def _init() -> None:
    global _initialized
    if not _initialized:
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        _initialized = True


async def generate(prompt: str, system_instruction: str | None = None) -> str:
    """Generate text using Gemini."""
    _init()
    model = GenerativeModel(GEMINI_MODEL, system_instruction=system_instruction)
    response = model.generate_content(prompt)
    return response.text


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks."""
    _init()
    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    embeddings = model.get_embeddings(texts)
    return [e.values for e in embeddings]
