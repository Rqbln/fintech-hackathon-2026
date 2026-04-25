from pydantic import BaseModel, Field


class AlternativeVendor(BaseModel):
    name: str
    hq_country: str
    eu_sovereign: bool
    certification: str = ""     # e.g. "SecNumCloud", "ISO 27001", "BSI C5"
    services_covered: list[str] = Field(default_factory=list)
    cost_delta: str = ""        # e.g. "+15%", "-10%", "comparable"
    feature_delta: str = ""     # prose summary of feature gaps/gains
    website: str = ""


class RemediationProposal(BaseModel):
    obligation_id: str
    vendor_name: str
    priority: str               # critical / high / medium / low
    summary: str                # one-sentence action
    detail: str                 # full LLM-generated remediation plan
    sovereign_alternatives: list[AlternativeVendor] = Field(default_factory=list)
    estimated_effort_days: int | None = None
    references: list[str] = Field(default_factory=list)  # DORA article refs
