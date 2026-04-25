"""ReportAssembler — combines findings + proposals into a ReportArtifact.

Also asks the LLM to write a short executive summary.
"""

import structlog
from llama_index.core.llms import ChatMessage, LLM

from app.llm.retry import chat_with_retry
from app.schemas import ObligationFinding, RemediationProposal, ReportArtifact, Verdict

log = structlog.get_logger()

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
        lines.append(f"• Art.{f.article}/{f.paragraph}: {f.verdict.value} — {f.rationale[:120]}")
    return "\n".join(lines)


async def assemble_report(
    llm: LLM,
    session_id: str,
    contract_ids: list[str],
    findings: list[ObligationFinding],
    proposals: list[RemediationProposal],
) -> ReportArtifact:
    met = sum(1 for f in findings if f.verdict == Verdict.MET)
    partial = sum(1 for f in findings if f.verdict == Verdict.PARTIALLY_MET)
    unmet = sum(1 for f in findings if f.verdict == Verdict.UNMET)

    # Overall risk: worst verdict determines level
    if unmet > 2:
        overall = "critical"
    elif unmet > 0 or partial > 3:
        overall = "high"
    elif partial > 0:
        overall = "medium"
    else:
        overall = "low"

    # Executive summary via LLM
    prompt = _EXEC_SUMMARY_PROMPT.format(findings_text=_findings_text(findings))
    resp = await chat_with_retry(llm, [ChatMessage(role="user", content=prompt)])
    exec_summary = resp.message.content.strip()

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
    log.info(
        "report_assembled",
        session_id=session_id,
        met=met,
        partial=partial,
        unmet=unmet,
        risk=overall,
    )
    return report
