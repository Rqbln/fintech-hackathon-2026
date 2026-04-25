"""Cypher constraints and indexes — applied once at startup."""

from neo4j import AsyncDriver

from .client import run_write

_CONSTRAINTS = [
    "CREATE CONSTRAINT vendor_id IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT biz_fn_id IF NOT EXISTS FOR (b:BusinessFunction) REQUIRE b.id IS UNIQUE",
    "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT obligation_id IF NOT EXISTS FOR (o:DORAObligation) REQUIRE o.id IS UNIQUE",
]

_INDEXES = [
    "CREATE INDEX vendor_name IF NOT EXISTS FOR (v:Vendor) ON (v.name)",
    "CREATE INDEX service_name IF NOT EXISTS FOR (s:Service) ON (s.name)",
]


async def apply_schema(driver: AsyncDriver) -> None:
    for stmt in _CONSTRAINTS + _INDEXES:
        await run_write(driver, stmt)
