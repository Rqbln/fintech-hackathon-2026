#!/usr/bin/env python
"""Wipe all graph data then re-apply schema constraints/indexes.

Use before a fresh demo run to start from a clean slate.

Usage:
    uv run python scripts/reset_neo4j.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase

from app.config import settings
from app.graph.schema import apply_schema


async def main() -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )

    async with driver.session() as session:
        result = await session.run("MATCH (n) DETACH DELETE n")
        summary = await result.consume()
        nodes_deleted = summary.counters.nodes_deleted
        rels_deleted = summary.counters.relationships_deleted

    print(f"Deleted {nodes_deleted} node(s) and {rels_deleted} relationship(s).")

    print("Re-applying schema constraints and indexes …")
    await apply_schema(driver)

    await driver.close()
    print("Graph reset complete.")


if __name__ == "__main__":
    asyncio.run(main())
