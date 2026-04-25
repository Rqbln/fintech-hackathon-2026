from fastapi import APIRouter, HTTPException, Query

import app.store as store
from app.agents.evaluator import EvaluatorAgent
from app.models.schemas import VendorDocument

router = APIRouter()
_evaluator = EvaluatorAgent()


@router.post("/gap")
async def run_gap_analysis(document_id: str):
    """
    Evaluate a freshly uploaded document against all DORA Art. 30 requirements.
    The document must have been uploaded first via POST /api/documents/upload.
    Queries the RAG corpus using the vendor name to retrieve relevant contract chunks.
    """
    if document_id not in store.documents:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found — upload it first via POST /api/documents/upload",
        )
    doc = VendorDocument(**store.documents[document_id])
    result = await _evaluator.evaluate(
        vendor_name=doc.vendor_name,
        document_id=document_id,
    )
    store.evaluations[document_id] = result.model_dump()
    return result


@router.post("/evaluate-vendor")
async def evaluate_vendor(
    vendor_name: str = Query(..., description="Vendor name as stored in the RAG corpus (e.g. 'AWS', 'Bloomberg')"),
):
    """
    Evaluate any vendor already indexed in the RAG corpus — no upload needed.
    Use this to evaluate the 24 contracts that were pre-loaded into the corpus.
    The vendor_name must match how it appears in the corpus chunks (case-sensitive).
    """
    doc_id = f"corpus_{vendor_name.lower().replace(' ', '_')}"
    result = await _evaluator.evaluate(
        vendor_name=vendor_name,
        document_id=doc_id,
    )
    store.evaluations[doc_id] = result.model_dump()
    return result


@router.get("/results/{document_id}")
async def get_analysis_results(document_id: str):
    """Retrieve a previously computed DORA compliance evaluation."""
    if document_id not in store.evaluations:
        raise HTTPException(
            status_code=404,
            detail=f"No evaluation for '{document_id}' — run POST /api/analysis/gap or /evaluate-vendor first",
        )
    return store.evaluations[document_id]


@router.get("/summary")
async def get_all_evaluations():
    """Return a compliance summary across all evaluated vendors."""
    evaluations = list(store.evaluations.values())
    return {
        "evaluations": [
            {
                "document_id": ev.get("document_id"),
                "vendor_name": ev.get("vendor_name"),
                "overall_score": ev.get("overall_score"),
                "missing_articles_count": len(ev.get("missing_articles", [])),
                "missing_articles": ev.get("missing_articles", []),
                "evaluated_at": ev.get("evaluated_at"),
            }
            for ev in evaluations
        ],
        "total": len(evaluations),
        "portfolio_score": round(
            sum(ev.get("overall_score", 0) for ev in evaluations) / len(evaluations), 3
        ) if evaluations else 0.0,
    }
