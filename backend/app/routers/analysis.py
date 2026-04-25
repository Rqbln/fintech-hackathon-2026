"""
Analysis router — runs the full orchestration pipeline for a document and
returns the React Flow graph + DORA compliance evaluation.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import OrchestratorAgent
from app.services.vector_store import get_store

log = logging.getLogger(__name__)
router = APIRouter()

_orchestrator = OrchestratorAgent()


@router.get("/{doc_id}")
async def analyze_document(doc_id: str, vendor_name: str = "", filename: str = ""):
    """
    Full DORA analysis for an already-indexed document.

    - Runs RAG + Gemini evaluation across 6 DORA categories
    - Detects subcontractors via Gemini
    - Returns React Flow graph + compliance data

    Query params:
        vendor_name : ICT provider name (used in prompts and graph labels)
        filename    : original PDF filename (used in graph on_click payload)
    """
    # Verify the document is indexed in the vector store
    store = get_store()
    if store.count(doc_id=doc_id) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found in vector store. Upload it first via POST /api/documents/upload",
        )

    try:
        result = await _orchestrator.analyze(
            doc_id=doc_id,
            vendor_name=vendor_name or doc_id,
            filename=filename or f"{doc_id}.pdf",
        )
        return result
    except Exception as e:
        log.exception("Analysis failed for doc_id=%s", doc_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}/graph")
async def get_graph(doc_id: str, vendor_name: str = "", filename: str = ""):
    """
    Same as GET /{doc_id} but returns only the React Flow graph portion.
    Useful for lightweight re-fetches when the evaluation result is already cached client-side.
    """
    result = await analyze_document(doc_id, vendor_name=vendor_name, filename=filename)
    return result["graph"]
