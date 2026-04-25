"""Idempotent MERGE upserts for every node and edge type in the graph schema."""

from neo4j import AsyncDriver

from app.schemas import ContractExtraction

from .client import run_write


async def upsert_vendor(driver: AsyncDriver, vendor_id: str, name: str, country: str | None = None) -> None:
    await run_write(
        driver,
        """
        MERGE (v:Vendor {id: $id})
        SET v.name = $name,
            v.country = $country,
            v.criticality_score = coalesce(v.criticality_score, 0.0),
            v.is_critical_provider = coalesce(v.is_critical_provider, false)
        """,
        id=vendor_id,
        name=name,
        country=country or "unknown",
    )


async def upsert_service(driver: AsyncDriver, service_id: str, name: str, vendor_id: str) -> None:
    await run_write(
        driver,
        """
        MERGE (s:Service {id: $id})
        SET s.name = $name
        WITH s
        MATCH (v:Vendor {id: $vendor_id})
        MERGE (v)-[:PROVIDES]->(s)
        """,
        id=service_id,
        name=name,
        vendor_id=vendor_id,
    )


async def upsert_contract(driver: AsyncDriver, contract_id: str, vendor_id: str, gcs_uri: str = "") -> None:
    await run_write(
        driver,
        """
        MERGE (c:Contract {id: $id})
        SET c.gcs_uri = $gcs_uri,
            c.ingested_at = timestamp()
        WITH c
        MATCH (v:Vendor {id: $vendor_id})
        MERGE (c)-[:COVERS]->(v)
        """,
        id=contract_id,
        vendor_id=vendor_id,
        gcs_uri=gcs_uri,
    )


async def upsert_obligation(driver: AsyncDriver, obligation_id: str, article: str, paragraph: str, text: str) -> None:
    await run_write(
        driver,
        """
        MERGE (o:DORAObligation {id: $id})
        SET o.article = $article, o.paragraph = $paragraph, o.text = $text
        """,
        id=obligation_id,
        article=article,
        paragraph=paragraph,
        text=text,
    )


async def upsert_evidence_edge(
    driver: AsyncDriver,
    contract_id: str,
    obligation_id: str,
    strength: str,        # met / partially_met / unmet
    evidence_text: str,
) -> None:
    await run_write(
        driver,
        """
        MATCH (c:Contract {id: $contract_id})
        MATCH (o:DORAObligation {id: $obligation_id})
        MERGE (c)-[r:EVIDENCES {obligation_id: $obligation_id}]->(o)
        SET r.strength = $strength, r.evidence_text = $evidence_text
        """,
        contract_id=contract_id,
        obligation_id=obligation_id,
        strength=strength,
        evidence_text=evidence_text,
    )


async def upsert_dependency_edge(driver: AsyncDriver, vendor_id: str, sub_vendor_id: str, context: str = "") -> None:
    await run_write(
        driver,
        """
        MATCH (v:Vendor {id: $vendor_id})
        MATCH (sv:Vendor {id: $sub_vendor_id})
        MERGE (v)-[r:DEPENDS_ON {sub_vendor_id: $sub_vendor_id}]->(sv)
        SET r.context = $context
        """,
        vendor_id=vendor_id,
        sub_vendor_id=sub_vendor_id,
        context=context,
    )


async def upsert_extraction(driver: AsyncDriver, extraction: ContractExtraction, slug: str) -> None:
    """Materialise a full ContractExtraction into Neo4j in one call."""
    vendor_id = f"vendor:{slug}"
    await upsert_vendor(driver, vendor_id, extraction.vendor_name, extraction.vendor_country)
    await upsert_contract(driver, extraction.contract_id, vendor_id)

    for clause in extraction.services:
        service_slug = clause.service_name.lower().replace(" ", "_")
        await upsert_service(driver, f"service:{slug}:{service_slug}", clause.service_name, vendor_id)

    for sub_name in extraction.sub_vendors:
        sub_slug = sub_name.lower().replace(" ", "_")
        sub_id = f"vendor:{sub_slug}"
        await upsert_vendor(driver, sub_id, sub_name)
        await upsert_dependency_edge(driver, vendor_id, sub_id)
