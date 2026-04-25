from fastapi import APIRouter, HTTPException

import app.store as store
from app.agents.evaluator import EvaluatorAgent
from app.models.schemas import VendorDocument

router = APIRouter()
_evaluator = EvaluatorAgent()


@router.post("/gap")
async def run_gap_analysis(document_id: str):
    """Evaluate a document's clauses against all DORA Art. 30 requirements."""
    if document_id not in store.documents:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found — upload it first via POST /api/documents/upload",
        )

    doc = VendorDocument(**store.documents[document_id])
    result = await _evaluator.evaluate(
        clauses=doc.clauses,
        sla_entries=doc.sla_entries,
        vendor_name=doc.vendor_name,
        document_id=document_id,
    )

    store.evaluations[document_id] = result.model_dump()
    return result


@router.get("/results/{document_id}")
async def get_analysis_results(document_id: str):
    """Retrieve a previously computed DORA compliance evaluation."""
    if document_id not in store.evaluations:
        raise HTTPException(
            status_code=404,
            detail=f"No evaluation for '{document_id}' — run POST /api/analysis/gap first",
        )
    return store.evaluations[document_id]


@router.get("/summary")
async def get_all_evaluations():
    """Return a summary of all evaluated documents."""
    return {
        "evaluations": [
            {
                "document_id": doc_id,
                "vendor_name": ev.get("vendor_name"),
                "overall_score": ev.get("overall_score"),
                "missing_articles": ev.get("missing_articles", []),
                "evaluated_at": ev.get("evaluated_at"),
            }
            for doc_id, ev in store.evaluations.items()
        ],
        "total": len(store.evaluations),
    }
