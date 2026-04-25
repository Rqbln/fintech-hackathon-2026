import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from llama_index.core import Settings as LlamaSettings
from llama_index.core import VectorStoreIndex
from neo4j import AsyncGraphDatabase

from .config import settings
from .graph.schema import apply_schema
from .llm.client import make_llm
from .llm.embeddings import make_embed_model
from .rag.citation_query import make_citation_engine
from .rag.store import get_or_create_vector_store
from .tracing.logger import configure_logging
from .api import analysis, graph, ingest, remediation, report, sessions

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    os.makedirs(settings.traces_dir, exist_ok=True)
    app.state.settings = settings

    # Neo4j
    app.state.neo4j = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await apply_schema(app.state.neo4j)
    log.info("neo4j_driver_created", uri=settings.neo4j_uri)

    # LLM + embed model — set on LlamaIndex global Settings so all components pick them up
    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model
    app.state.llm = llm
    app.state.embed_model = embed_model
    log.info("llm_ready", model=settings.cerebras_model)

    # Vertex AI Vector Store + LlamaIndex index
    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    app.state.vector_store = vector_store
    app.state.index = index
    app.state.citation_engine = make_citation_engine(index)
    log.info("vector_store_ready", collection=settings.vertex_ai_vs_collection)

    yield

    await app.state.neo4j.close()
    log.info("shutdown_complete")


app = FastAPI(
    title="DORA AI Analyst",
    description="AI-powered DORA compliance analysis — explainable gap analysis with citations.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(remediation.router, prefix="/api", tags=["remediation"])
app.include_router(report.router, prefix="/api", tags=["report"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])


@app.get("/health", summary="Health check — pings all dependencies")
async def health():
    checks: dict[str, str] = {}

    try:
        await app.state.neo4j.verify_connectivity()
        checks["neo4j"] = "ok"
    except Exception as exc:
        checks["neo4j"] = f"error: {exc}"

    checks["llm_key"] = "ok" if settings.cerebras_api_key not in ("", "test-key-placeholder") else "placeholder"
    checks["gemini_key"] = "ok" if settings.gemini_api_key not in ("", "test-key-placeholder") else "placeholder"
    checks["gcp_project"] = "ok" if settings.gcp_project else "missing"
    checks["vector_store"] = "ok" if hasattr(app.state, "vector_store") else "not_initialized"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503
    return JSONResponse(status_code=status_code, content={"status": overall, "checks": checks})
