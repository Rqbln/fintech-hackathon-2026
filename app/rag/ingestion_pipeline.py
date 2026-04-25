"""Parse PDF → chunk → embed → upsert into Vertex AI Vector Search v2."""

import hashlib
from typing import Any

import structlog
import pymupdf  # PyMuPDF
from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

log = structlog.get_logger()

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


def _parse_pdf_pymupdf(file_bytes: bytes) -> list[dict[str, Any]]:
    """Returns list of {page, text} dicts — one entry per page."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def _parse_pdf_llamaparse(file_bytes: bytes, api_key: str) -> list[dict[str, Any]]:
    # TODO(Phase 1 polish): async LlamaParse call; currently falls back to PyMuPDF
    raise NotImplementedError("LlamaParse parsing not yet implemented")


def parse_pdf(file_bytes: bytes, llama_parse_api_key: str | None) -> list[dict[str, Any]]:
    """Parse PDF. Uses LlamaParse if key is set, else PyMuPDF."""
    if llama_parse_api_key:
        try:
            return _parse_pdf_llamaparse(file_bytes, llama_parse_api_key)
        except NotImplementedError:
            pass
    return _parse_pdf_pymupdf(file_bytes)


async def ingest_pdf(
    file_bytes: bytes,
    document_id: str,
    doc_type: str,  # "DORA" | "contract"
    vector_store,
    embed_model,
    contract_id: str | None = None,
    llama_parse_api_key: str | None = None,
) -> list[str]:
    """Parse, chunk, embed, and upsert one PDF. Returns list of upserted node IDs."""
    pages = parse_pdf(file_bytes, llama_parse_api_key)
    log.info("pdf_parsed", document_id=document_id, pages=len(pages))

    base_metadata: dict[str, Any] = {"document_id": document_id, "doc_type": doc_type}
    if contract_id:
        base_metadata["contract_id"] = contract_id

    documents = [
        Document(
            text=p["text"],
            metadata={**base_metadata, "page": p["page"]},
            id_=f"{document_id}_p{p['page']}",
        )
        for p in pages
    ]

    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP),
            embed_model,
        ],
        vector_store=vector_store,
    )

    nodes = await pipeline.arun(documents=documents, show_progress=True)
    node_ids = [n.node_id for n in nodes]
    log.info("pdf_indexed", document_id=document_id, nodes=len(node_ids))
    return node_ids
