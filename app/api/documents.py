"""Serve raw contract PDFs for the frontend citation viewer."""

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.rag.ingestion_pipeline import get_contract_pdf_path

router = APIRouter()

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_\-]+$")


@router.get("/documents/{contract_id}/pdf", summary="Serve raw contract PDF")
async def get_pdf(contract_id: str):
    if not _SAFE_ID.match(contract_id):
        raise HTTPException(status_code=400, detail="Invalid contract ID")

    path = get_contract_pdf_path(contract_id)
    if not path:
        raise HTTPException(
            status_code=404,
            detail=f"PDF for contract '{contract_id}' not found. Re-ingest the document.",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=f"{contract_id}.pdf",
        headers={"Content-Disposition": "inline"},
    )
