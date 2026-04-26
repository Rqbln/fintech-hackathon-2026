#!/usr/bin/env python
"""Ingest the demo AWS contract fixture through the full ContractIngestionWorkflow.

Reads tests/fixtures/demo_aws_contract.txt, converts it to a real PDF via
PyMuPDF, then runs the same end-to-end pipeline used by the API upload endpoint.

Usage:
    uv run python scripts/seed_demo_contracts.py
"""

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pymupdf  # PyMuPDF
import structlog
from neo4j import AsyncGraphDatabase
from llama_index.core import Settings as LlamaSettings

from app.config import settings
from app.graph.schema import apply_schema
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.rag.store import get_or_create_vector_store
from app.agents.ingestion import ContractIngestionWorkflow
from app.tracing.logger import configure_logging

configure_logging(settings.log_level)
log = structlog.get_logger()

FIXTURE_TXT = Path(__file__).parent.parent / "tests" / "fixtures" / "demo_aws_contract.txt"
CONTRACT_ID = "demo-aws-001"
TMP_PDF = Path(tempfile.gettempdir()) / "demo_aws_contract.pdf"


def text_to_pdf(text: str, dest: Path) -> bytes:
    """Create a minimal PDF from plain text using PyMuPDF and return its bytes."""
    doc = pymupdf.open()
    # PyMuPDF limits insert_text to ~3 500 chars per page; chunk across pages.
    chunk_size = 3000
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current = ""
    for line in lines:
        if len(current) + len(line) > chunk_size:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)

    for chunk in chunks:
        page = doc.new_page()
        page.insert_text((50, 50), chunk, fontsize=10)

    doc.save(str(dest))
    file_bytes = dest.read_bytes()
    log.info("pdf_created", path=str(dest), pages=len(doc), bytes=len(file_bytes))
    doc.close()
    return file_bytes


async def main() -> None:
    print("=== seed_demo_contracts — full ContractIngestionWorkflow ===\n")

    if not FIXTURE_TXT.exists():
        print(f"ERROR: fixture not found at {FIXTURE_TXT}")
        sys.exit(1)

    # ── Convert text fixture → PDF ──
    print(f"[1/5] Reading fixture: {FIXTURE_TXT.name}")
    contract_text = FIXTURE_TXT.read_text(encoding="utf-8")
    print(f"      {len(contract_text)} chars")

    print(f"[2/5] Converting to PDF → {TMP_PDF}")
    file_bytes = text_to_pdf(contract_text, TMP_PDF)
    print(f"      {len(file_bytes)} bytes, saved to {TMP_PDF}")

    # ── Setup ──
    print("[3/5] Initialising LLM, embeddings, vector store, Neo4j …")
    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model

    vector_store = get_or_create_vector_store(settings)

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    await apply_schema(driver)
    print("      Ready.")

    # ── Run workflow ──
    print(f"[4/5] Running ContractIngestionWorkflow for contract_id={CONTRACT_ID} …")
    workflow = ContractIngestionWorkflow(
        llm=llm,
        embed_model=embed_model,
        vector_store=vector_store,
        neo4j_driver=driver,
        llama_parse_api_key=settings.llama_parse_api_key,
        use_llamaparse=settings.llama_parse_enabled,
        timeout=300,
    )

    result = await workflow.run(file_bytes=file_bytes, contract_id=CONTRACT_ID)

    # ── Report ──
    print("[5/5] Ingestion complete.")
    print(f"      contract_id      : {result.contract_id}")
    print(f"      vendor_name      : {result.vendor_name}")
    print(f"      vendor_id        : {result.vendor_id}")
    print(f"      criticality_score: {result.criticality_score:.3f}")
    print(f"      node_ids         : {len(result.node_ids)} chunks indexed")

    await driver.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    asyncio.run(main())
