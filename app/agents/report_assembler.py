"""ReportAssembler — combines findings + proposals into a ReportArtifact."""

import structlog
from llama_index.core.llms import LLM

from app.schemas import ObligationFinding, RemediationProposal, ReportArtifact, Verdict

log = structlog.get_logger()

# Exported so analysis.py can pre-build the summary concurrently with remediation
_EXEC_SUMMARY_PROMPT = """\
You are a DORA compliance advisor writing an executive summary for a bank's board.
Summarise the findings below in 3–5 bullet points. Be specific about risks.
Use formal but accessible language. Maximum 200 words.

Findings:
{findings_text}
"""


def _findings_text(findings: list[ObligationFinding]) -> str:
    lines = []
    for f in findings:
        lines.append(f"• Art.{f.article}/{f.paragraph}: {f.verdict.value} — {f.rationale[:80]}")
    return "\n".join(lines[:12])


async def assemble_report(
    llm: LLM,
    session_id: str,
    contract_ids: list[str],
    findings: list[ObligationFinding],
    proposals: list[RemediationProposal],
    prebuilt_exec_summary: str = "",
) -> ReportArtifact:
    met = sum(1 for f in findings if f.verdict == Verdict.MET)
    partial = sum(1 for f in findings if f.verdict == Verdict.PARTIALLY_MET)
    unmet = sum(1 for f in findings if f.verdict == Verdict.UNMET)

    if unmet > 2:
        overall = "critical"
    elif unmet > 0 or partial > 3:
        overall = "high"
    elif partial > 0:
        overall = "medium"
    else:
        overall = "low"

    # Use pre-built summary if available (built concurrently with remediation)
    exec_summary = prebuilt_exec_summary or "(Summary unavailable)"

    report = ReportArtifact(
        session_id=session_id,
        contract_ids=contract_ids,
        executive_summary=exec_summary,
        findings=findings,
        remediation_proposals=proposals,
        obligations_met=met,
        obligations_partial=partial,
        obligations_unmet=unmet,
        overall_risk_level=overall,
    )
    log.info("report_assembled", session_id=session_id, met=met, partial=partial, unmet=unmet, risk=overall)
    return report
