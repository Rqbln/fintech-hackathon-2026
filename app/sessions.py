"""In-memory session store.

A session is created when a gap analysis runs. It links the session_id
from ReportArtifact to the contract_ids, vendor, and a findings summary
so the UI can list and revisit past analyses without re-running them.
"""

from datetime import datetime, timezone

from app.schemas import ReportArtifact

_sessions: dict[str, dict] = {}


def record(report: ReportArtifact) -> None:
    _sessions[report.session_id] = {
        "session_id": report.session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ids": report.contract_ids,
        "overall_risk_level": report.overall_risk_level,
        "obligations_met": report.obligations_met,
        "obligations_partial": report.obligations_partial,
        "obligations_unmet": report.obligations_unmet,
        "vendor_names": list({p.vendor_name for p in report.remediation_proposals}),
    }


def get(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def list_all() -> list[dict]:
    return sorted(_sessions.values(), key=lambda s: s["created_at"], reverse=True)
