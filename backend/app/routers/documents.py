from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a vendor PDF (contract, SLA, SOC 2 report) for extraction."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # TODO: Store in GCS, trigger extraction agent
    return {
        "filename": file.filename,
        "status": "uploaded",
        "message": "Document queued for extraction",
    }


@router.get("/")
async def list_documents():
    """List all uploaded vendor documents."""
    # TODO: Query stored documents
    return {"documents": []}
