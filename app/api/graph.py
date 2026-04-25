from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/graph", summary="Return Sigma.js-compatible graph JSON")
async def get_graph(root_vendor: str | None = None, depth: int = 2):
    # TODO(Phase 5): query Neo4j → compute criticality scores → return Sigma JSON
    return JSONResponse(status_code=501, content={"error": "not_implemented", "phase": "Phase 5"})
