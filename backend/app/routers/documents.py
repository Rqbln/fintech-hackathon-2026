from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.extractor import ExtractorAgent

router = APIRouter()
_extractor = ExtractorAgent()
_store: dict[str, dict] = {}  # In-memory for hackathon MVP


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    vendor_name: str = Form(default="Unknown Vendor"),
):
    """Upload a vendor PDF: GCS → Document AI → chunker → RAG corpus."""
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


@router.get("/")
async def list_documents():
    return {"documents": list(_store.values()), "total": len(_store)}


@router.get("/{document_id}")
async def get_document(document_id: str):
    if document_id not in _store:
        raise HTTPException(status_code=404, detail="Document not found")
    return _store[document_id]
