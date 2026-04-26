#!/usr/bin/env python
"""Load DORA regulation PDF from GCS and run it through the ingestion pipeline.

Usage:
    uv run python scripts/seed_dora.py          # fetch from GCS + ingest
    uv run python scripts/seed_dora.py --force  # re-ingest even if already done
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.gcs_dora import fetch_dora_pdf_bytes
from app.llm.embeddings import make_embed_model
from app.rag.ingestion_pipeline import ingest_pdf
from app.rag.store import get_or_create_vector_store
from app.tracing.logger import configure_logging

configure_logging(settings.log_level)
log = structlog.get_logger()

DORA_DOC_ID = "DORA-2022-2554-EN"


async def main(force: bool = False) -> None:
    file_bytes, bucket_name, object_name = fetch_dora_pdf_bytes(settings)
    log.info("dora_pdf_loaded_from_gcs", bucket=bucket_name, object_name=object_name, bytes=len(file_bytes))

    log.info("vector_store_init")
    vector_store = get_or_create_vector_store(settings)
    embed_model = make_embed_model(settings)

    log.info("ingestion_start", doc_id=DORA_DOC_ID)
    node_ids = await ingest_pdf(
        file_bytes=file_bytes,
        document_id=DORA_DOC_ID,
        doc_type="DORA",
        vector_store=vector_store,
        embed_model=embed_model,
        llama_parse_api_key=settings.llama_parse_api_key,
        use_llamaparse=settings.llama_parse_enabled,
    )
    log.info("ingestion_complete", nodes=len(node_ids))
    print(f"\n✓ DORA regulation indexed: {len(node_ids)} chunks in Vertex AI Vector Search.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(main(force=force))
