#!/usr/bin/env python
"""Download the DORA regulation PDF and run it through the ingestion pipeline.

Usage:
    uv run python scripts/seed_dora.py          # download + ingest
    uv run python scripts/seed_dora.py --force  # re-ingest even if already done
"""

import asyncio
import sys
from pathlib import Path

import httpx
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.llm.embeddings import make_embed_model
from app.rag.ingestion_pipeline import ingest_pdf
from app.rag.store import get_or_create_vector_store
from app.tracing.logger import configure_logging

configure_logging(settings.log_level)
log = structlog.get_logger()

# Official DORA regulation PDF from EUR-Lex (Regulation EU 2022/2554)
DORA_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R2554"
DORA_DOC_ID = "DORA-2022-2554-EN"
DORA_PDF_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "dora_regulation.pdf"


def download_dora(force: bool = False) -> bytes:
    if DORA_PDF_PATH.exists() and not force:
        log.info("dora_pdf_cached", path=str(DORA_PDF_PATH))
        return DORA_PDF_PATH.read_bytes()

    log.info("dora_pdf_downloading", url=DORA_URL)
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        resp = client.get(DORA_URL, headers={"User-Agent": "DORA-Analyst/0.1"})
        resp.raise_for_status()

    file_bytes = resp.content
    DORA_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    DORA_PDF_PATH.write_bytes(file_bytes)
    log.info("dora_pdf_saved", path=str(DORA_PDF_PATH), bytes=len(file_bytes))
    return file_bytes


async def main(force: bool = False) -> None:
    file_bytes = download_dora(force=force)

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
    )
    log.info("ingestion_complete", nodes=len(node_ids))
    print(f"\n✓ DORA regulation indexed: {len(node_ids)} chunks in Vertex AI Vector Search.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(main(force=force))
