from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/report/{client_id}", summary="Return the assembled audit report (JSON or Markdown)")
async def get_report(client_id: str):
    # TODO(Phase 8): ReportAssembler → Markdown + JSON with full citation appendix
    return JSONResponse(status_code=501, content={"error": "not_implemented", "phase": "Phase 8"})
