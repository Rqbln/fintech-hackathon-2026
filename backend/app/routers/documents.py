from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from google.api_core.exceptions import GoogleAPIError

from app.agents.extractor import ExtractorAgent
from app.services.storage import list_objects

router = APIRouter()
_extractor = ExtractorAgent()
_store: dict[str, dict] = {}  # In-memory for hackathon MVP

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _validate_pdf(file: UploadFile) -> None:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"Only PDF files are accepted (got: {file.filename!r})")
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content-type: {file.content_type}")


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    vendor_name: str = Form(default="Unknown Vendor"),
):
    """Upload one or more vendor PDFs: GCS → Document AI → chunker → RAG corpus."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    for f in files:
        _validate_pdf(f)

    results = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{f.filename} exceeds the 50 MB limit")
        try:
            vendor_doc = await _extractor.extract(content, f.filename, vendor_name)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Extraction failed for {f.filename}: {exc}") from exc

        _store[vendor_doc.document_id] = vendor_doc.model_dump()
        results.append({
            "document_id": vendor_doc.document_id,
            "filename": f.filename,
            "vendor_name": vendor_name,
            "status": "extracted",
            "total_clauses": len(vendor_doc.clauses),
            "total_sla_entries": len(vendor_doc.sla_entries),
        })

    return {"uploaded": results, "count": len(results)}


@router.get("/")
async def list_documents():
    """List uploaded documents — GCS objects and in-memory extraction results."""
    try:
        gcs_objects = list_objects(prefix="uploads/")
    except GoogleAPIError:
        gcs_objects = []
    return {
        "documents": list(_store.values()),
        "total": len(_store),
        "gcs_objects": gcs_objects,
    }


@router.get("/{document_id}")
async def get_document(document_id: str):
    if document_id not in _store:
        raise HTTPException(status_code=404, detail="Document not found")
    return _store[document_id]
