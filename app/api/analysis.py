import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

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
    contract_text_preview: Annotated[str, Body(embed=True, default="")],
    obligation_ids: Annotated[list[str] | None, Body(embed=True)] = None,
    llm=Depends(get_llm),
    citation_engine=Depends(get_citation_engine),
):
    session_id = str(uuid.uuid4())

    findings = await run_gap_analysis(
        llm=llm,
        citation_engine=citation_engine,
        contract_id=contract_ids[0] if contract_ids else "unknown",
        contract_text_preview=contract_text_preview,
        obligation_ids=obligation_ids,
    )

    proposals = await run_remediation(llm=llm, findings=findings, vendor_name=vendor_name)

    report = await assemble_report(
        llm=llm,
        session_id=session_id,
        contract_ids=contract_ids,
        findings=findings,
        proposals=proposals,
    )

    store_report(report)
    return report
