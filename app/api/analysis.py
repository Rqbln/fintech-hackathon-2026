from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/gap-analysis", summary="Run DORA Article 30 gap analysis on uploaded contracts")
async def gap_analysis(contract_ids: list[str]):
    # TODO(Phase 6): iterate obligations YAML → CitationQueryEngine → ObligationFinding per obligation
    return JSONResponse(status_code=501, content={"error": "not_implemented", "phase": "Phase 6"})
