from fastapi import APIRouter, HTTPException, Request

from app.graph.queries import get_graph, get_vendor_concentration
from app.schemas import GraphResponse

router = APIRouter()


@router.get("/graph", response_model=GraphResponse, summary="Return Sigma.js-compatible graph JSON")
async def graph_endpoint(request: Request, root_vendor: str | None = None, depth: int = 2):
    try:
        return await get_graph(request.app.state.neo4j, root_vendor=root_vendor, depth=depth)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "graph_query_failed", "message": str(exc)[:400]}) from exc


@router.get("/graph/concentration", summary="Vendor concentration ranking")
async def concentration_endpoint(request: Request):
    try:
        return await get_vendor_concentration(request.app.state.neo4j)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "concentration_query_failed", "message": str(exc)[:400]}) from exc
