#!/usr/bin/env python
"""Ingest the demo fixture contracts for the hackathon pitch demo.

Expects PDFs at:
  tests/fixtures/demo_contracts/*.pdf

Usage:
    uv run python scripts/seed_demo_contracts.py
"""

import asyncio
import sys
from pathlib import Path

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.llm.embeddings import make_embed_model
from app.rag.ingestion_pipeline import ingest_pdf
from app.rag.store import get_or_create_vector_store
from app.tracing.logger import configure_logging

configure_logging(settings.log_level)
log = structlog.get_logger()

CONTRACTS_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "demo_contracts"


async def main() -> None:
    pdfs = list(CONTRACTS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {CONTRACTS_DIR}. Add demo contract PDFs and retry.")
        sys.exit(1)

    vector_store = get_or_create_vector_store(settings)
    embed_model = make_embed_model(settings)

    for pdf_path in pdfs:
        contract_id = pdf_path.stem  # filename without extension
        log.info("ingesting_contract", contract_id=contract_id, path=str(pdf_path))
        file_bytes = pdf_path.read_bytes()
        node_ids = await ingest_pdf(
            file_bytes=file_bytes,
            document_id=contract_id,
            doc_type="contract",
            vector_store=vector_store,
            embed_model=embed_model,
            contract_id=contract_id,
            llama_parse_api_key=settings.llama_parse_api_key,
        )
        print(f"  ✓ {contract_id}: {len(node_ids)} chunks")

    print(f"\n✓ Ingested {len(pdfs)} contract(s).")


if __name__ == "__main__":
    asyncio.run(main())
