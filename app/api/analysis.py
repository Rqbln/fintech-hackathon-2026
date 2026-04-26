"""Gap analysis endpoint with SSE streaming and in-memory result cache."""

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import sessions
from app.agents.gap_analysis import run_gap_analysis, stream_gap_analysis
from app.agents.remediation import run_remediation
from app.agents.report_assembler import (
    _EXEC_SUMMARY_PROMPT,
    _findings_text,
    assemble_report,
)
from app.api.report import store_report
from app.config import settings
from app.deps import get_citation_engine, get_llm
from app.llm.retry import chat_with_retry
from app.schemas import ObligationFinding, ReportArtifact

router = APIRouter()

# Simple in-memory cache: (vendor_name, contract_ids_key) → ReportArtifact
_cache: dict[str, ReportArtifact] = {}
_DEFAULT_OBLIGATIONS_TOTAL = 6 if settings.fast_mode else 12


def _cache_key(vendor_name: str, contract_ids: list[str]) -> str:
    return f"{vendor_name}|{','.join(sorted(contract_ids))}"


# ── Streaming endpoint (used by the frontend) ─────────────────────────────────

@router.post("/gap-analysis-stream", summary="Stream gap analysis results via SSE")
async def gap_analysis_stream(
    request: Request,
    contract_ids: Annotated[list[str], Body(embed=True)],
    vendor_name: Annotated[str, Body(embed=True)],
    contract_text_preview: Annotated[str, Body(embed=True)] = "",
    obligation_ids: Annotated[list[str] | None, Body(embed=True)] = None,
    primary_contract_id: Annotated[str | None, Body(embed=True)] = None,
    use_cache: Annotated[bool, Body(embed=True)] = False,
    llm=Depends(get_llm),
    citation_engine=Depends(get_citation_engine),
):
    contract_id = primary_contract_id or (contract_ids[0] if contract_ids else "unknown")
    effective_contract_ids = [contract_id]
    ck = _cache_key(vendor_name, effective_contract_ids)
    if use_cache and ck in _cache:
        # Serve cached report instantly
        cached = _cache[ck]
        async def replay():
            for f in cached.findings:
                yield f"data: {json.dumps({'type': 'finding', 'data': json.loads(f.model_dump_json())})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'report': json.loads(cached.model_dump_json())})}\n\n"
        return StreamingResponse(replay(), media_type="text/event-stream",
                                 headers={"X-Cache": "HIT"})

    async def generate():
        session_id = str(uuid.uuid4())
        findings: list[ObligationFinding] = []
        total_obligations = len(obligation_ids) if obligation_ids else _DEFAULT_OBLIGATIONS_TOTAL

        progress_start = {
            "type": "progress",
            "stage": "analysis",
            "completed": 0,
            "total": total_obligations,
            "message": "Starting live compliance analysis...",
        }
        yield f"data: {json.dumps(progress_start)}\n\n"

        # Phase 1 — stream findings as each obligation completes
        async for finding in stream_gap_analysis(
            llm=llm,
            citation_engine=citation_engine,
            contract_id=contract_id,
            contract_text_preview=contract_text_preview,
            obligation_ids=obligation_ids,
            fast_mode=settings.fast_mode,
            concurrency=settings.gap_concurrency,
            batch_size=settings.gap_batch_size,
        ):
            findings.append(finding)
            yield f"data: {json.dumps({'type': 'finding', 'data': json.loads(finding.model_dump_json())})}\n\n"
            progress_tick = {
                "type": "progress",
                "stage": "analysis",
                "completed": len(findings),
                "total": total_obligations,
                "message": "Analyzing obligations...",
            }
            yield f"data: {json.dumps(progress_tick)}\n\n"

        progress_remediation = {
            "type": "progress",
            "stage": "remediation",
            "completed": total_obligations,
            "total": total_obligations,
            "message": "Generating remediation and executive summary...",
        }
        yield f"data: {json.dumps(progress_remediation)}\n\n"

        # Phase 2 — remediation + exec summary in parallel (all findings available now)
        try:
            from llama_index.core.llms import ChatMessage
            proposals, exec_summary = await asyncio.gather(
                run_remediation(llm=llm, findings=findings, vendor_name=vendor_name),
                _build_exec_summary(llm, findings),
            )
            report = await assemble_report(
                llm=llm, session_id=session_id, contract_ids=effective_contract_ids,
                findings=findings, proposals=proposals,
                prebuilt_exec_summary=exec_summary,
            )
            _cache[ck] = report
            store_report(report)
            sessions.record(report)
            progress_done = {
                "type": "progress",
                "stage": "done",
                "completed": total_obligations,
                "total": total_obligations,
                "message": "Analysis completed.",
            }
            yield f"data: {json.dumps(progress_done)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'report': json.loads(report.model_dump_json())})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)[:300]})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Non-streaming endpoint (kept for CLI scripts / test_pipeline.py) ──────────

@router.post("/gap-analysis", response_model=ReportArtifact,
             summary="Run DORA gap analysis (blocking, for scripts)")
async def gap_analysis(
    request: Request,
    contract_ids: Annotated[list[str], Body(embed=True)],
    vendor_name: Annotated[str, Body(embed=True)],
    contract_text_preview: Annotated[str, Body(embed=True)] = "",
    obligation_ids: Annotated[list[str] | None, Body(embed=True)] = None,
    llm=Depends(get_llm),
    citation_engine=Depends(get_citation_engine),
):
    effective_contract_ids = [contract_ids[0]] if contract_ids else ["unknown"]
    ck = _cache_key(vendor_name, effective_contract_ids)
    if ck in _cache:
        return _cache[ck]

    session_id = str(uuid.uuid4())
    try:
        findings = await run_gap_analysis(
            llm=llm, citation_engine=citation_engine,
            contract_id=effective_contract_ids[0],
            contract_text_preview=contract_text_preview,
            obligation_ids=obligation_ids,
            fast_mode=settings.fast_mode,
            concurrency=settings.gap_concurrency,
            batch_size=settings.gap_batch_size,
        )
        proposals, exec_summary = await asyncio.gather(
            run_remediation(llm=llm, findings=findings, vendor_name=vendor_name),
            _build_exec_summary(llm, findings),
        )
        report = await assemble_report(
            llm=llm, session_id=session_id, contract_ids=effective_contract_ids,
            findings=findings, proposals=proposals, prebuilt_exec_summary=exec_summary,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "gap_analysis_failed", "message": str(exc)[:500]}) from exc

    _cache[ck] = report
    store_report(report)
    sessions.record(report)
    return report


async def _build_exec_summary(llm, findings: list[ObligationFinding]) -> str:
    from llama_index.core.llms import ChatMessage
    prompt = _EXEC_SUMMARY_PROMPT.format(findings_text=_findings_text(findings))
    try:
        resp = await chat_with_retry(llm, [ChatMessage(role="user", content=prompt)])
        return resp.message.content.strip()
    except Exception:
        return ""
