#!/usr/bin/env python
"""Wipe all graph data — use before a fresh demo run."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from neo4j import AsyncGraphDatabase


async def main() -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    async with driver.session() as session:
        result = await session.run("MATCH (n) DETACH DELETE n")
        summary = await result.consume()
        print(f"Deleted {summary.counters.nodes_deleted} nodes and "
              f"{summary.counters.relationships_deleted} relationships.")
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
