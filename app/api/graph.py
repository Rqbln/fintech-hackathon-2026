from fastapi import APIRouter, Depends, Request

from app.graph.queries import get_graph, get_vendor_concentration
from app.schemas import GraphResponse

router = APIRouter()


@router.get("/graph", response_model=GraphResponse, summary="Return Sigma.js-compatible graph JSON")
async def graph_endpoint(request: Request, root_vendor: str | None = None, depth: int = 2):
    driver = request.app.state.neo4j
    return await get_graph(driver, root_vendor=root_vendor, depth=depth)


@router.get("/graph/concentration", summary="Vendor concentration ranking")
async def concentration_endpoint(request: Request):
    driver = request.app.state.neo4j
    return await get_vendor_concentration(driver)
