from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/remediation", summary="Generate remediation proposals for gap findings")
async def remediation(findings: list[dict]):
    # TODO(Phase 7): RemediationAgent → sovereign EU alternatives from sovereign_alternatives.yaml
    return JSONResponse(status_code=501, content={"error": "not_implemented", "phase": "Phase 7"})
