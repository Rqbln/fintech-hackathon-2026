from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .obligation import ObligationFinding
from .remediation import RemediationProposal


class ReportArtifact(BaseModel):
    session_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    contract_ids: list[str] = Field(default_factory=list)
    executive_summary: str = ""
    findings: list[ObligationFinding] = Field(default_factory=list)
    remediation_proposals: list[RemediationProposal] = Field(default_factory=list)
    # Aggregate stats
    obligations_met: int = 0
    obligations_partial: int = 0
    obligations_unmet: int = 0
    overall_risk_level: str = "unknown"
