"""RiskScorer — recomputes criticality_score for all Vendor nodes after each ingest.

criticality_score ∈ [0, 1] is a weighted sum of:
  - contract_count (0.3)   — number of contracts with this vendor
  - service_count (0.3)    — number of services the vendor provides
  - sub_vendor_count (0.2) — number of vendors that depend on this one
  - country_risk (0.2)     — 1.0 if country outside EU/EEA, else 0.0

The score drives node size in the Sigma.js graph.
"""

import structlog
from neo4j import AsyncDriver

from app.graph.client import run_read, run_write

log = structlog.get_logger()

_EU_EEA_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",            # EU
    "IS", "LI", "NO",                                      # EEA
    "CH", "GB",                                            # common associates (grey)
}

_W_CONTRACTS = 0.3
_W_SERVICES = 0.3
_W_SUB_VENDORS = 0.2
_W_COUNTRY = 0.2

# Normalisation caps (beyond these values the component maxes at 1.0)
_CAP_CONTRACTS = 5
_CAP_SERVICES = 10
_CAP_SUB_VENDORS = 3


def _country_risk(country: str | None) -> float:
    if not country:
        return 0.5  # unknown → moderate
    code = country.strip().upper()[:2]
    return 0.0 if code in _EU_EEA_COUNTRIES else 1.0


async def recompute_all(driver: AsyncDriver) -> list[dict]:
    """Recompute and persist criticality_score for every Vendor."""
    rows = await run_read(
        driver,
        """
        MATCH (v:Vendor)
        OPTIONAL MATCH (c:Contract)-[:COVERS]->(v)
        OPTIONAL MATCH (v)-[:PROVIDES]->(s:Service)
        OPTIONAL MATCH (other:Vendor)-[:DEPENDS_ON]->(v)
        RETURN
            v.id AS id,
            v.name AS name,
            coalesce(v.country, null) AS country,
            count(DISTINCT c) AS contract_count,
            count(DISTINCT s) AS service_count,
            count(DISTINCT other) AS dependent_count
        """,
    )

    updated = []
    for row in rows:
        score = (
            _W_CONTRACTS * min(row["contract_count"], _CAP_CONTRACTS) / _CAP_CONTRACTS
            + _W_SERVICES * min(row["service_count"], _CAP_SERVICES) / _CAP_SERVICES
            + _W_SUB_VENDORS * min(row["dependent_count"], _CAP_SUB_VENDORS) / _CAP_SUB_VENDORS
            + _W_COUNTRY * _country_risk(row["country"])
        )
        score = round(min(score, 1.0), 4)

        await run_write(
            driver,
            "MATCH (v:Vendor {id: $id}) SET v.criticality_score = $score",
            id=row["id"],
            score=score,
        )

        updated.append({"id": row["id"], "name": row["name"], "criticality_score": score})
        log.debug("risk_score_updated", vendor_id=row["id"], score=score)

    log.info("risk_scorer_complete", vendors_updated=len(updated))
    return updated
