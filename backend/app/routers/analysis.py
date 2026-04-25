from fastapi import APIRouter

router = APIRouter()


@router.post("/gap")
async def run_gap_analysis(document_id: str):
    """Run Gap Analysis: compare vendor guarantees against bank internal rules."""
    # TODO: Invoke Orchestrator Agent
    return {
        "document_id": document_id,
        "status": "analysis_pending",
        "gaps": [],
    }


@router.get("/results/{document_id}")
async def get_analysis_results(document_id: str):
    """Get Gap Analysis results for a specific document."""
    # TODO: Retrieve stored analysis results
    return {"document_id": document_id, "results": None}
