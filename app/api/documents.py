"""Serve raw contract PDFs for the frontend citation viewer."""

import re

import pymupdf
import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, FileResponse

from app import contract_store
from app.rag.ingestion_pipeline import get_contract_pdf_path

log = structlog.get_logger()
router = APIRouter()

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_\-]+$")


@router.get("/documents/{contract_id}/pdf", summary="Serve raw contract PDF")
async def get_pdf(
    contract_id: str,
    highlight: str = Query(default="", description="Text phrase to highlight"),
):
    if not _SAFE_ID.match(contract_id):
        raise HTTPException(status_code=400, detail="Invalid contract ID")

    path = get_contract_pdf_path(contract_id)
    if not path:
        raise HTTPException(
            status_code=404,
            detail=f"PDF for contract '{contract_id}' not found. Re-ingest the document.",
        )

    if not highlight:
        return FileResponse(
            path=path,
            media_type="application/pdf",
            filename=f"{contract_id}.pdf",
            headers={"Content-Disposition": "inline"},
        )

    # Bake highlight annotations into an in-memory copy
    doc = pymupdf.open(str(path))
    phrase = highlight.strip()
    hit_count = 0
    for page in doc:
        for rect in page.search_for(phrase):
            page.add_highlight_annot(rect)
            hit_count += 1

    log.info("pdf_highlight", contract_id=contract_id, phrase=phrase[:60], hits=hit_count)
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline", "Cache-Control": "no-store"},
    )


@router.get("/contracts/{contract_id}/preview", summary="Return stored contract text preview for gap analysis")
async def get_contract_preview(contract_id: str):
    if not _SAFE_ID.match(contract_id):
        raise HTTPException(status_code=400, detail="Invalid contract ID")
    text = contract_store.get(contract_id)
    return {"contract_id": contract_id, "text": text, "chars": len(text)}


@router.get("/documents/{contract_id}/find-text", summary="Find the page containing a text phrase")
async def find_text_page(
    contract_id: str,
    q: str = Query(..., description="Text phrase to search for"),
):
    if not _SAFE_ID.match(contract_id):
        raise HTTPException(status_code=400, detail="Invalid contract ID")

    path = get_contract_pdf_path(contract_id)
    if not path:
        raise HTTPException(status_code=404, detail=f"PDF for contract '{contract_id}' not found.")

    doc = pymupdf.open(str(path))
    phrase = q.strip()
    for i, page in enumerate(doc):
        if page.search_for(phrase):
            doc.close()
            return {"page": i + 1}
    doc.close()
    return {"page": 1}
