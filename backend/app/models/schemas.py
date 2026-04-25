"""Pydantic models for RegAgent domain objects."""

from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class ExtractedClause(BaseModel):
    clause_id: str
    text: str
    category: str  # e.g. "data_residency", "rto_rpo", "audit_rights", "subcontracting"
    source_page: int | None = None


class SLAEntry(BaseModel):
    metric: str  # e.g. "RTO", "RPO", "availability"
    value: str
    unit: str | None = None


class VendorDocument(BaseModel):
    document_id: str
    vendor_name: str
    document_type: str  # "contract", "soc2_report", "sla_annex"
    filename: str
    gcs_uri: str
    clauses: list[ExtractedClause] = []
    sla_entries: list[SLAEntry] = []


class ComplianceMapping(BaseModel):
    dora_article: str  # e.g. "Art. 30(2)(a)"
    iso_control: str | None = None  # e.g. "A.5.19"
    clause_id: str
    status: ComplianceStatus
    evidence: str
    score: float  # 0.0 to 1.0


class Alert(BaseModel):
    alert_id: str
    vendor_name: str
    severity: Severity
    title: str
    description: str
    dora_reference: str
    bank_requirement: str
    vendor_guarantee: str
    gap_details: str
    validated: bool = False


class RiskScore(BaseModel):
    vendor_id: str
    vendor_name: str
    overall_score: float
    concentration_score: float
    compliance_score: float
    alert_count: int


class RegisterEntry(BaseModel):
    """A single entry in the DORA Register of Information."""
    vendor_name: str
    lei_code: str | None = None
    service_description: str
    is_critical_function: bool
    data_location: str | None = None
    subcontractors: list[str] = []
    contract_start: str | None = None
    contract_end: str | None = None
    compliance_mappings: list[ComplianceMapping] = []


class EvaluationResult(BaseModel):
    document_id: str
    vendor_name: str
    overall_score: float  # 0.0 to 1.0 — mean of per-article scores
    compliance_mappings: list[ComplianceMapping]
    missing_articles: list[str]  # DORA articles with no matching clause in the document
    evaluated_at: str  # ISO 8601 UTC
