from enum import Enum

from pydantic import BaseModel, Field

from .contract import EvidenceSpan


class Verdict(str, Enum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    UNMET = "unmet"
    UNKNOWN = "unknown"


class ObligationFinding(BaseModel):
    obligation_id: str          # matches dora_obligations.yaml id
    article: str                # e.g. "30"
    paragraph: str              # e.g. "2a"
    description: str            # human-readable obligation text
    verdict: Verdict
    rationale: str              # LLM-generated explanation WHY this verdict
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    gap_description: str = ""   # populated when verdict != MET
    risk_level: str = "medium"  # low / medium / high / critical
