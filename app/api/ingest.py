import hashlib
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app import jobs
from app.agents import ContractIngestionWorkflow
from app.deps import get_embed_model, get_ingestion_workflow, get_settings, get_vector_store
from app.gcs_contracts import upload_contract_file
from app.gcs_dora import fetch_dora_pdf_bytes
from app.rag.ingestion_pipeline import ingest_pdf

log = structlog.get_logger()
router = APIRouter()

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

    try:
        file_bytes, bucket_name, object_name = fetch_dora_pdf_bytes(settings)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"DORA PDF not found in configured GCS bucket: {exc}") from exc

    node_ids = await ingest_pdf(
        file_bytes=file_bytes,
        document_id=_DORA_DOC_ID,
        doc_type="DORA",
        vector_store=vector_store,
        embed_model=embed_model,
        llama_parse_api_key=settings.llama_parse_api_key,
        use_llamaparse=settings.llama_parse_enabled,
    )
    _DORA_INGESTED_FLAG.touch()
    return {
        "status": "ingested",
        "document_id": _DORA_DOC_ID,
        "nodes": len(node_ids),
        "source": f"gs://{bucket_name}/{object_name}",
    }


async def _run_pipeline(job_id: str, file_bytes: bytes, doc_id: str, workflow: ContractIngestionWorkflow) -> None:
    try:
        result = await workflow.run(file_bytes=file_bytes, contract_id=doc_id)
        jobs.complete(job_id, {
            "status": "ingested",
            "contract_id": result.contract_id,
            "vendor_name": result.vendor_name,
            "vendor_id": result.vendor_id,
            "criticality_score": result.criticality_score,
            "node_ids_count": len(result.node_ids),
        })
        log.info("job_complete", job_id=job_id, vendor=result.vendor_name)
    except Exception as exc:
        jobs.fail(job_id, str(exc)[:500])
        log.error("job_failed", job_id=job_id, error=str(exc)[:200])


@router.post("/ingest", summary="Ingest a vendor contract PDF — returns job_id immediately")
async def ingest_contract(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    contract_id: str | None = None,
    workflow: ContractIngestionWorkflow = Depends(get_ingestion_workflow),
    settings=Depends(get_settings),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    doc_id = contract_id or hashlib.md5(file_bytes).hexdigest()[:12]
    job_id = uuid.uuid4().hex[:8]

    gcs_uri = upload_contract_file(
        settings,
        contract_id=doc_id,
        file_name=file.filename or f"{doc_id}.pdf",
        file_bytes=file_bytes,
    )

    jobs.create(job_id, doc_id)
    background_tasks.add_task(_run_pipeline, job_id, file_bytes, doc_id, workflow)

    log.info("job_queued", job_id=job_id, contract_id=doc_id, gcs_uri=gcs_uri)
    return {"job_id": job_id, "status": "running", "contract_id": doc_id, "gcs_uri": gcs_uri}


@router.get("/jobs/{job_id}", summary="Poll ingest pipeline job status")
async def get_job(job_id: str):
    entry = jobs.get(job_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Job not found")
    return entry


@router.get("/jobs", summary="List all ingest jobs")
async def list_jobs():
    return jobs.list_all()
