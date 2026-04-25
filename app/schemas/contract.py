from pydantic import BaseModel, Field


class EvidenceSpan(BaseModel):
    text: str
    page: int
    document_id: str
    node_id: str  # LlamaIndex chunk node_id


class ServiceClause(BaseModel):
    service_name: str  # e.g. "DNS hosting", "CDN"
    sla_hours: float | None = None  # RTO/RPO in hours if present
    evidence: EvidenceSpan | None = None


class ContractExtraction(BaseModel):
    contract_id: str
    vendor_name: str
    vendor_country: str | None = None  # ISO 3166-1 alpha-2 or full name
    services: list[ServiceClause] = Field(default_factory=list)
    # DORA Art.30 clauses present (obligation ids from dora_obligations.yaml)
    covered_obligation_ids: list[str] = Field(default_factory=list)
    # Key excerpts that evidence specific obligations
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    # Dependency chain — other vendors named in the contract (4th-party)
    sub_vendors: list[str] = Field(default_factory=list)
    raw_text_preview: str = ""  # first 500 chars for debug
