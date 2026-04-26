"""Read queries — graph retrieval for the Sigma.js API endpoint."""

from neo4j import AsyncDriver

from app.schemas import EdgeAttributes, GraphEdge, GraphNode, GraphResponse, NodeAttributes

from .client import run_read

# Node color palette by type
_COLORS = {
    "Vendor": "#6366f1",
    "Service": "#22d3ee",
    "BusinessFunction": "#f59e0b",
    "Contract": "#4ade80",
    "DORAObligation": "#f87171",
}

_BASE_SIZE = 10.0
_MAX_SIZE = 40.0


def _vendor_size(score: float) -> float:
    return _BASE_SIZE + (_MAX_SIZE - _BASE_SIZE) * min(score, 1.0)


async def get_graph(driver: AsyncDriver, root_vendor: str | None = None, depth: int = 2) -> GraphResponse:
    """Return the full graph (or subgraph rooted at a vendor) as Sigma-ready JSON."""
    # Neo4j does not allow parameters in variable-length path bounds [*0..$depth].
    # depth is an integer from the API layer — safe to interpolate directly.
    d = max(1, min(int(depth), 10))
    if root_vendor:
        node_rows = await run_read(
            driver,
            f"""
            MATCH path = (root:Vendor {{name: $name}})-[*0..{d}]-(nb)
            UNWIND nodes(path) AS n
            RETURN DISTINCT
                labels(n)[0] AS label_type,
                n.id AS id,
                n.name AS name,
                coalesce(n.criticality_score, 0.0) AS criticality_score,
                coalesce(n.country, null) AS country,
                coalesce(n.is_critical_provider, false) AS is_critical_provider
            """,
            name=root_vendor,
        )
        edge_rows = await run_read(
            driver,
            f"""
            MATCH path = (root:Vendor {{name: $name}})-[*0..{d}]-(nb)
            UNWIND relationships(path) AS r
            RETURN DISTINCT
                id(r) AS eid,
                startNode(r).id AS source,
                endNode(r).id AS target,
                type(r) AS rel_type
            """,
            name=root_vendor,
        )
    else:
        node_rows = await run_read(
            driver,
            """
            MATCH (n:Vendor)
            RETURN
                'Vendor' AS label_type,
                n.id AS id,
                n.name AS name,
                coalesce(n.criticality_score, 0.0) AS criticality_score,
                coalesce(n.country, null) AS country,
                coalesce(n.is_critical_provider, false) AS is_critical_provider
            """,
        )
        edge_rows = await run_read(
            driver,
            """
            MATCH (a:Vendor)-[r:DEPENDS_ON]->(b:Vendor)
            RETURN
                id(r) AS eid,
                a.id AS source,
                b.id AS target,
                type(r) AS rel_type
            """,
        )

    nodes = [
        GraphNode(
            key=row["id"],
            attributes=NodeAttributes(
                label=row["name"] or row["id"],
                size=_vendor_size(row["criticality_score"]) if row["label_type"] == "Vendor" else _BASE_SIZE,
                color=_COLORS.get(row["label_type"], "#94a3b8"),
                node_type=row["label_type"],
                criticality_score=row["criticality_score"],
                country=row["country"],
                is_critical_provider=row["is_critical_provider"],
            ),
        )
        for row in node_rows
        if row.get("id")
    ]

    edges = [
        GraphEdge(
            key=f"edge:{row['eid']}",
            source=row["source"],
            target=row["target"],
            attributes=EdgeAttributes(label=row["rel_type"]),
        )
        for row in edge_rows
        if row.get("source") and row.get("target")
    ]

    return GraphResponse(nodes=nodes, edges=edges)


async def get_vendor_concentration(driver: AsyncDriver) -> list[dict]:
    """Return vendors sorted by criticality_score descending."""
    return await run_read(
        driver,
        """
        MATCH (v:Vendor)
        RETURN v.id AS id, v.name AS name, v.criticality_score AS score,
               v.country AS country, v.is_critical_provider AS is_critical
        ORDER BY score DESC
        """,
    )
