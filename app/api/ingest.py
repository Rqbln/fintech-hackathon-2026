import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.agents import ContractIngestionWorkflow
from app.deps import get_embed_model, get_ingestion_workflow, get_settings, get_vector_store
from app.rag.ingestion_pipeline import ingest_pdf

router = APIRouter()

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


@router.post("/ingest", summary="Ingest a vendor contract PDF — triggers full AI pipeline")
async def ingest_contract(
    file: UploadFile,
    contract_id: str | None = None,
    workflow: ContractIngestionWorkflow = Depends(get_ingestion_workflow),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    doc_id = contract_id or hashlib.md5(file_bytes).hexdigest()[:12]

    result = await workflow.run(file_bytes=file_bytes, contract_id=doc_id)

    return {
        "status": "ingested",
        "contract_id": result.contract_id,
        "vendor_name": result.vendor_name,
        "vendor_id": result.vendor_id,
        "criticality_score": result.criticality_score,
        "node_ids_count": len(result.node_ids),
    }
