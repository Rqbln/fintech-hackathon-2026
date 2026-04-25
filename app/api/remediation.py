from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app.agents.remediation import run_remediation
from app.api.report import _reports
from app.deps import get_llm
from app.schemas import RemediationProposal

router = APIRouter()


@router.post(
    "/remediation",
    response_model=list[RemediationProposal],
    summary="Generate sovereign EU remediation proposals for a session's gap findings",
)
async def remediation(
    session_id: Annotated[str, Body(embed=True)],
    vendor_name: Annotated[str, Body(embed=True)],
    llm=Depends(get_llm),
):
    report = _reports.get(session_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id!r} not found — run /api/gap-analysis first.",
        )

    proposals = await run_remediation(
        llm=llm,
        findings=report.findings,
        vendor_name=vendor_name,
    )
    return proposals
