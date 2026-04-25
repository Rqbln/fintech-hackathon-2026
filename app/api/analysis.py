import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app import sessions
from app.agents.gap_analysis import run_gap_analysis
from app.agents.remediation import run_remediation
from app.agents.report_assembler import assemble_report
from app.api.report import store_report
from app.deps import get_citation_engine, get_llm
from app.schemas import ReportArtifact

router = APIRouter()


@router.post(
    "/gap-analysis",
    response_model=ReportArtifact,
    summary="Run DORA Article 30 gap analysis on uploaded contracts",
)
async def gap_analysis(
    request: Request,
    contract_ids: Annotated[list[str], Body(embed=True)],
    vendor_name: Annotated[str, Body(embed=True)],
    contract_text_preview: Annotated[str, Body(embed=True)] = "",
    obligation_ids: Annotated[list[str] | None, Body(embed=True)] = None,
    llm=Depends(get_llm),
    citation_engine=Depends(get_citation_engine),
):
    session_id = str(uuid.uuid4())

    try:
        # Phase 1 — gap analysis (all 12 obligations in parallel)
        findings = await run_gap_analysis(
            llm=llm,
            citation_engine=citation_engine,
            contract_id=contract_ids[0] if contract_ids else "unknown",
            contract_text_preview=contract_text_preview,
            obligation_ids=obligation_ids,
        )

        # Phase 2 — remediation + executive summary concurrently
        proposals, exec_summary_placeholder = await asyncio.gather(
            run_remediation(llm=llm, findings=findings, vendor_name=vendor_name),
            _build_exec_summary(llm, findings),
        )

        report = await assemble_report(
            llm=llm,
            session_id=session_id,
            contract_ids=contract_ids,
            findings=findings,
            proposals=proposals,
            prebuilt_exec_summary=exec_summary_placeholder,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "gap_analysis_failed", "message": str(exc)[:500]},
        ) from exc

    store_report(report)
    sessions.record(report)
    return report


async def _build_exec_summary(llm, findings) -> str:
    """Pre-build the executive summary while remediation runs in parallel."""
    from app.agents.report_assembler import _findings_text, _EXEC_SUMMARY_PROMPT
    from app.llm.retry import chat_with_retry
    from llama_index.core.llms import ChatMessage

    prompt = _EXEC_SUMMARY_PROMPT.format(findings_text=_findings_text(findings))
    try:
        resp = await chat_with_retry(llm, [ChatMessage(role="user", content=prompt)])
        return resp.message.content.strip()
    except Exception:
        return ""
