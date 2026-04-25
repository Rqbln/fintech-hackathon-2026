import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.agents.extractor import ExtractorAgent

router = APIRouter()
_extractor = ExtractorAgent()
_store: dict[str, dict] = {}       # document_id → VendorDocument
_batches: dict[str, dict] = {}     # batch_id → batch status


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    vendor_name: str = Form(default="Unknown Vendor"),
):
    """Upload a single vendor PDF: GCS → Document AI → chunker → vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    content = await file.read()
    vendor_doc = await _extractor.extract(content, file.filename, vendor_name)
    _store[vendor_doc.document_id] = vendor_doc.model_dump()
    return {
        "document_id": vendor_doc.document_id,
        "filename": file.filename,
        "vendor_name": vendor_name,
        "status": "extracted",
        "total_clauses": len(vendor_doc.clauses),
        "total_sla_entries": len(vendor_doc.sla_entries),
    }


@router.post("/upload/batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    vendor_name: str = Form(default="Unknown Vendor"),
):
    """
    Upload a folder of PDFs. Files are processed one by one sequentially.
    Returns a batch_id to poll for progress via GET /upload/batch/{batch_id}.
    """
    pdfs = [f for f in files if f.filename and f.filename.lower().endswith(".pdf")]
    if not pdfs:
        raise HTTPException(status_code=400, detail="No PDF files found in upload")

    items = []
    for f in pdfs:
        content = await f.read()
        items.append({"filename": f.filename, "content": content})

    batch_id = uuid.uuid4().hex[:8]
    _batches[batch_id] = {
        "batch_id": batch_id,
        "total": len(items),
        "processed": 0,
        "status": "pending",
        "results": [],
    }

    background_tasks.add_task(_process_batch, batch_id, items, vendor_name)

    return {
        "batch_id": batch_id,
        "total": len(items),
        "status": "pending",
        "poll_url": f"/api/documents/upload/batch/{batch_id}",
    }


@router.get("/upload/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Poll the processing status of a batch upload."""
    if batch_id not in _batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batches[batch_id]


@router.get("/")
async def list_documents():
    return {"documents": list(_store.values()), "total": len(_store)}


@router.get("/{document_id}")
async def get_document(document_id: str):
    if document_id not in _store:
        raise HTTPException(status_code=404, detail="Document not found")
    return _store[document_id]


# ---------------------------------------------------------------------------
# Internal batch processor — runs in background, one file at a time
# ---------------------------------------------------------------------------

async def _process_batch(
    batch_id: str,
    items: list[dict],
    vendor_name: str,
) -> None:
    _batches[batch_id]["status"] = "processing"

    for item in items:
        filename = item["filename"]
        content = item["content"]

        _batches[batch_id]["results"].append({
            "filename": filename,
            "status": "processing",
            "document_id": None,
            "total_clauses": None,
            "error": None,
        })
        current = _batches[batch_id]["results"][-1]

        try:
            vendor_doc = await _extractor.extract(content, filename, vendor_name)
            _store[vendor_doc.document_id] = vendor_doc.model_dump()
            current["status"] = "done"
            current["document_id"] = vendor_doc.document_id
            current["total_clauses"] = len(vendor_doc.clauses)
        except Exception as e:
            current["status"] = "error"
            current["error"] = str(e)

        _batches[batch_id]["processed"] += 1

    _batches[batch_id]["status"] = "done"
