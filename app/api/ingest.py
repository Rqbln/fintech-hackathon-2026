import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.deps import get_embed_model, get_settings, get_vector_store
from app.rag.ingestion_pipeline import ingest_pdf

router = APIRouter()

# Path to bundled DORA regulation PDF (committed to repo under tests/fixtures/)
_DORA_PDF_PATH = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "dora_regulation.pdf"
_DORA_DOC_ID = "DORA-2022-2554-EN"
_DORA_INGESTED_FLAG = Path("/tmp/dora_ingested.flag")


@router.post("/ingest/dora", summary="Seed DORA regulation into the vector store (idempotent)")
async def ingest_dora(
    vector_store=Depends(get_vector_store),
    embed_model=Depends(get_embed_model),
    settings=Depends(get_settings),
    force: bool = False,
):
    if _DORA_INGESTED_FLAG.exists() and not force:
        return {"status": "already_ingested", "document_id": _DORA_DOC_ID}

    if not _DORA_PDF_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"DORA PDF not found at {_DORA_PDF_PATH}. Run scripts/seed_dora.py first.",
        )

    file_bytes = _DORA_PDF_PATH.read_bytes()
    node_ids = await ingest_pdf(
        file_bytes=file_bytes,
        document_id=_DORA_DOC_ID,
        doc_type="DORA",
        vector_store=vector_store,
        embed_model=embed_model,
        llama_parse_api_key=settings.llama_parse_api_key,
    )

    _DORA_INGESTED_FLAG.touch()
    return {"status": "ingested", "document_id": _DORA_DOC_ID, "nodes": len(node_ids)}


@router.post("/ingest", summary="Ingest a vendor contract PDF")
async def ingest_contract(
    file: UploadFile,
    contract_id: str | None = None,
    vector_store=Depends(get_vector_store),
    embed_model=Depends(get_embed_model),
    settings=Depends(get_settings),
):
    # TODO(Phase 3): after ingestion, trigger ExtractionAgent → GraphBuilder → RiskScorer
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    doc_id = contract_id or hashlib.md5(file_bytes).hexdigest()[:12]

    node_ids = await ingest_pdf(
        file_bytes=file_bytes,
        document_id=doc_id,
        doc_type="contract",
        vector_store=vector_store,
        embed_model=embed_model,
        contract_id=doc_id,
        llama_parse_api_key=settings.llama_parse_api_key,
    )

    return {
        "status": "ingested",
        "contract_id": doc_id,
        "nodes": len(node_ids),
        "note": "ExtractionAgent + GraphBuilder not yet wired (Phase 3)",
    }
