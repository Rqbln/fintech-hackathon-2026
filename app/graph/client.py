"""Thin async Neo4j session wrapper used throughout the graph layer."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncSession


@asynccontextmanager
async def session(driver: AsyncDriver) -> AsyncGenerator[AsyncSession, None]:
    async with driver.session() as s:
        yield s


async def run_write(driver: AsyncDriver, query: str, **params: Any) -> list[dict]:
    async with session(driver) as s:
        result = await s.run(query, **params)
        return [r.data() async for r in result]


async def run_read(driver: AsyncDriver, query: str, **params: Any) -> list[dict]:
    async with session(driver) as s:
        result = await s.run(query, **params)
        return [r.data() async for r in result]
