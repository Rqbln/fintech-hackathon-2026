"""FastAPI dependency providers.

All state is populated during lifespan startup and read from app.state here.
"""

from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_citation_engine(request: Request):
    return request.app.state.citation_engine


def get_vector_store(request: Request):
    return request.app.state.vector_store


def get_embed_model(request: Request):
    return request.app.state.embed_model


def get_llm(request: Request):
    return request.app.state.llm


def get_ingestion_workflow(request: Request):
    return request.app.state.ingestion_workflow
