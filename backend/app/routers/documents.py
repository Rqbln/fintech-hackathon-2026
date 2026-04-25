import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.agents.extractor import ExtractorAgent

router = APIRouter()
_extractor = ExtractorAgent()
_store: dict[str, dict] = {}    # document_id → VendorDocument dict
_batches: dict[str, dict] = {}  # batch_id → batch status


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
        "clause_count": len(vendor_doc.clauses),
        "sla_entry_count": len(vendor_doc.sla_entries),
        "gcs_uri": vendor_doc.gcs_uri,
    }


@router.post("/upload/batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    vendor_name: str = Form(default="Unknown Vendor"),
):
    """
    Upload multiple PDFs. Files processed sequentially in background.
    Poll GET /upload/batch/{batch_id} for progress.
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
        "status": "pending",
        "total": len(items),
        "completed": 0,
        "results": [],
        "errors": [],
    }

    background_tasks.add_task(_process_batch, batch_id, items, vendor_name)

    return {"batch_id": batch_id, "total": len(items), "status": "pending"}


@router.get("/upload/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Poll the processing status of a batch upload."""
    if batch_id not in _batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batches[batch_id]


@router.get("/")
async def list_documents():
    """List all indexed documents with their metadata."""
    docs = []
    for doc in _store.values():
        docs.append({
            "document_id": doc.get("document_id"),
            "vendor_name": doc.get("vendor_name"),
            "filename": doc.get("filename"),
            "clause_count": len(doc.get("clauses", [])),
        })
    return docs


@router.get("/{document_id}")
async def get_document(document_id: str):
    if document_id not in _store:
        raise HTTPException(status_code=404, detail="Document not found")
    return _store[document_id]


# ---------------------------------------------------------------------------
# Background batch processor — sequential, one file at a time
# ---------------------------------------------------------------------------

async def _process_batch(batch_id: str, items: list[dict], vendor_name: str) -> None:
    _batches[batch_id]["status"] = "processing"

    for item in items:
        filename = item["filename"]
        content = item["content"]
        try:
            vendor_doc = await _extractor.extract(content, filename, vendor_name)
            _store[vendor_doc.document_id] = vendor_doc.model_dump()
            _batches[batch_id]["results"].append({
                "document_id": vendor_doc.document_id,
                "vendor_name": vendor_name,
                "filename": filename,
                "clause_count": len(vendor_doc.clauses),
                "sla_entry_count": len(vendor_doc.sla_entries),
                "gcs_uri": vendor_doc.gcs_uri,
            })
        except Exception as e:
            _batches[batch_id]["errors"].append({"filename": filename, "error": str(e)})

        _batches[batch_id]["completed"] += 1

    _batches[batch_id]["status"] = "done"
