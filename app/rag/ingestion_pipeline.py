"""Parse PDF → chunk → embed → upsert into Vertex AI Vector Search v2."""

import hashlib
import tempfile
from typing import Any

import structlog
import pymupdf  # PyMuPDF
from llama_parse import LlamaParse
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
    parser = LlamaParse(api_key=api_key, result_type="markdown", verbose=False)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        docs = parser.load_data(tmp.name)

    pages: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        text = (getattr(doc, "text", "") or "").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    return pages


def parse_pdf(
    file_bytes: bytes,
    llama_parse_api_key: str | None,
    use_llamaparse: bool = False,
) -> list[dict[str, Any]]:
    """Parse PDF. Uses LlamaParse if key is set, else PyMuPDF."""
    if use_llamaparse and llama_parse_api_key:
        try:
            return _parse_pdf_llamaparse(file_bytes, llama_parse_api_key)
        except Exception as exc:
            log.warning("llamaparse_failed_fallback_pymupdf", error=str(exc)[:200])
            pass
    return _parse_pdf_pymupdf(file_bytes)


# Absolute path — independent of CWD so it works regardless of how uvicorn is started.
_PDF_STORE_PATH = (
    __import__("pathlib").Path(__file__).parent.parent.parent / "traces" / "contracts"
)


def save_contract_pdf(contract_id: str, file_bytes: bytes) -> None:
    """Persist raw PDF bytes to disk for the citation viewer endpoint."""
    _PDF_STORE_PATH.mkdir(parents=True, exist_ok=True)
    dest = _PDF_STORE_PATH / f"{contract_id}.pdf"
    dest.write_bytes(file_bytes)
    log.info("pdf_saved", contract_id=contract_id, path=str(dest), size=len(file_bytes))


def get_contract_pdf_path(contract_id: str) -> "__import__('pathlib').Path | None":
    path = _PDF_STORE_PATH / f"{contract_id}.pdf"
    return path if path.exists() else None


async def ingest_pdf(
    file_bytes: bytes,
    document_id: str,
    doc_type: str,  # "DORA" | "contract"
    vector_store,
    embed_model,
    contract_id: str | None = None,
    llama_parse_api_key: str | None = None,
    use_llamaparse: bool = False,
) -> list[str]:
    """Parse, chunk, embed, and upsert one PDF. Returns list of upserted node IDs."""
    # Persist PDF for citation viewer
    if doc_type == "contract" and contract_id:
        save_contract_pdf(contract_id, file_bytes)

    pages = parse_pdf(file_bytes, llama_parse_api_key, use_llamaparse=use_llamaparse)
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
