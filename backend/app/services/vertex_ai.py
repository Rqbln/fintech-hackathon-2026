"""Vertex AI client for Gemini generation and text embeddings."""

import vertexai
from vertexai.generative_models import GenerativeModel

from app.config import GCP_PROJECT, GCP_REGION, GEMINI_MODEL

vertexai.init(project=GCP_PROJECT, location=GCP_REGION)


def get_gemini_model() -> GenerativeModel:
    return GenerativeModel(GEMINI_MODEL)


async def generate(prompt: str, system_instruction: str | None = None) -> str:
    """Generate text using Gemini."""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks."""
    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
    embeddings = model.get_embeddings(texts)
    return [e.values for e in embeddings]
