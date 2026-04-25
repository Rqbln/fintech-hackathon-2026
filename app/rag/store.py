"""Vertex AI Vector Search v2.0 — collection lifecycle management.

Creates the collection if it doesn't exist, then returns a configured
VertexAIVectorStore ready for upserts and queries.
"""

import structlog
from google.api_core import exceptions as gcp_exceptions
from google.cloud import vectorsearch_v1beta as vs
from llama_index.vector_stores.vertexaivectorsearch import VertexAIVectorStore

from app.config import Settings

log = structlog.get_logger()


def _collection_parent(settings: Settings) -> str:
    return f"projects/{settings.gcp_project}/locations/{settings.gcp_region}"


def _collection_name(settings: Settings) -> str:
    return f"{_collection_parent(settings)}/collections/{settings.vertex_ai_vs_collection}"


def get_or_create_vector_store(settings: Settings) -> VertexAIVectorStore:
    """Return VertexAIVectorStore v2, creating the collection on first run."""
    client = vs.VectorSearchServiceClient()

    collection_name = _collection_name(settings)
    try:
        client.get_collection(name=collection_name)
        log.info("vs_collection_found", name=collection_name)
    except gcp_exceptions.NotFound:
        log.info("vs_collection_creating", name=collection_name)
        collection = vs.Collection(
            display_name="DORA Analyst Documents",
            description="DORA regulation and third-party vendor contracts for compliance analysis.",
            vector_schema={
                "embedding": vs.VectorField(
                    dense_vector=vs.DenseVectorField(dimensions=settings.gemini_embed_dim)
                )
            },
        )
        op = client.create_collection(
            parent=_collection_parent(settings),
            collection_id=settings.vertex_ai_vs_collection,
            collection=collection,
        )
        op.result()
        log.info("vs_collection_created", name=collection_name)

    return VertexAIVectorStore(
        project_id=settings.gcp_project,
        region=settings.gcp_region,
        collection_id=settings.vertex_ai_vs_collection,
        api_version="v2",
    )
