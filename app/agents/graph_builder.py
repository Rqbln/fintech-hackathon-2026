"""GraphBuilderAgent — upserts a ContractExtraction into Neo4j.

Uses entity resolution (resolver.py) to deduplicate vendor names before
writing. Returns the canonical vendor_id.
"""

import structlog
from neo4j import AsyncDriver

from app.graph.client import run_read
from app.graph.resolver import resolve_vendor_id
from app.graph.upsert import upsert_extraction
from app.schemas import ContractExtraction

log = structlog.get_logger()


async def _load_known_vendors(driver: AsyncDriver) -> dict[str, str]:
    """Return {normalised_name: vendor_id} for all Vendor nodes in Neo4j."""
    rows = await run_read(driver, "MATCH (v:Vendor) RETURN v.name AS name, v.id AS id")
    return {row["name"].lower().strip(): row["id"] for row in rows if row.get("name")}


async def build_graph(driver: AsyncDriver, extraction: ContractExtraction) -> str:
    """Upsert extraction into Neo4j. Returns canonical vendor_id."""
    known = await _load_known_vendors(driver)
    vendor_id = resolve_vendor_id(extraction.vendor_name, known)
    slug = vendor_id.removeprefix("vendor:")

    # Patch the extraction's contract_id into sub-vendor resolution too
    await upsert_extraction(driver, extraction, slug)

    log.info(
        "graph_built",
        contract_id=extraction.contract_id,
        vendor_id=vendor_id,
        services=len(extraction.services),
        sub_vendors=len(extraction.sub_vendors),
    )
    return vendor_id
