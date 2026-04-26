"""Report export — serves assembled reports and compliant draft exports."""

import asyncio
import io
import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from llama_index.core.llms import ChatMessage
import pymupdf

from app.deps import get_llm
from app.llm.retry import chat_with_retry
from app.rag.ingestion_pipeline import get_contract_pdf_path
from app.schemas import ReportArtifact

router = APIRouter()
_SPACE_RE = re.compile(r"\s+")
_FRENCH_MARKERS = {
    " le ",
    " la ",
    " les ",
    " des ",
    " du ",
    " et ",
    " est ",
    " avec ",
    " sans ",
    " contrat ",
    " fournisseur ",
    " sous-trait",
    " résiliation ",
    " données ",
    " prestation ",
}

# In-memory store: session_id → ReportArtifact
# TODO(Phase 9 polish): persist to GCS / Neo4j for durability across restarts
_reports: dict[str, ReportArtifact] = {}


def store_report(report: ReportArtifact) -> None:
    _reports[report.session_id] = report


@router.get("/report/{session_id}", summary="Return assembled audit report as JSON")
async def get_report_json(session_id: str):
    report = _reports.get(session_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": "report_not_found"})
    return report


@router.get("/report/{session_id}/markdown", summary="Return assembled audit report as Markdown")
async def get_report_markdown(session_id: str):
    report = _reports.get(session_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": "report_not_found"})
    return PlainTextResponse(_to_markdown(report), media_type="text/markdown")


@router.post(
    "/report/{session_id}/compliant-draft",
    summary="Generate DORA-compliant negotiation draft as Markdown",
)
async def generate_compliant_draft_markdown(session_id: str, vendor_name: str | None = None, llm=Depends(get_llm)):
    report = _reports.get(session_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": "report_not_found"})
    markdown = await _to_compliant_draft_markdown(report, llm=llm, vendor_name=vendor_name)
    return PlainTextResponse(markdown, media_type="text/markdown")


@router.post(
    "/report/{session_id}/compliant-draft.pdf",
    summary="Generate DORA-compliant negotiation draft as edited PDF",
)
async def generate_compliant_draft_pdf(session_id: str, vendor_name: str | None = None, llm=Depends(get_llm)):
    report = _reports.get(session_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": "report_not_found"})
    contract_id = report.contract_ids[0] if report.contract_ids else None
    if not contract_id:
        return JSONResponse(status_code=400, content={"error": "contract_id_missing"})
    path = get_contract_pdf_path(contract_id)
    if not path:
        return JSONResponse(status_code=404, content={"error": "contract_pdf_not_found"})

    payload = await _build_compliant_pdf_bytes(path=str(path), report=report, llm=llm, vendor_name=vendor_name)
    return StreamingResponse(
        io.BytesIO(payload),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dora_compliant_{contract_id}.pdf"},
    )


def _to_markdown(r: ReportArtifact) -> str:
    lines = [
        f"# DORA Compliance Audit Report",
        f"**Session:** {r.session_id}  ",
        f"**Generated:** {r.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Contracts analysed:** {', '.join(r.contract_ids)}",
        "",
        "## Executive Summary",
        r.executive_summary,
        "",
        "## Results Overview",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| ✅ Met | {r.obligations_met} |",
        f"| ⚠️ Partially met | {r.obligations_partial} |",
        f"| ❌ Unmet | {r.obligations_unmet} |",
        f"| **Overall risk** | **{r.overall_risk_level.upper()}** |",
        "",
        "## Findings",
    ]

    for f in r.findings:
        icon = {"met": "✅", "partially_met": "⚠️", "unmet": "❌"}.get(f.verdict.value, "❓")
        lines += [
            f"### {icon} Art.{f.article} §{f.paragraph}",
            f"**Verdict:** {f.verdict.value}  **Risk:** {f.risk_level}",
            "",
            f.rationale,
        ]
        if f.gap_description:
            lines += ["", f"**Gap:** {f.gap_description}"]
        if f.evidence_spans:
            lines += ["", "**Evidence:**"]
            for span in f.evidence_spans[:2]:
                lines.append(f'> “{span.text}”  _(p.{span.page})_')
        lines.append("")

    if r.remediation_proposals:
        lines += ["## Remediation Proposals"]
        for p in r.remediation_proposals:
            lines += [
                f"### [{p.priority.upper()}] {p.summary}",
                p.detail,
            ]
            if p.sovereign_alternatives:
                lines += ["", "**EU-sovereign alternatives:**"]
                for alt in p.sovereign_alternatives[:2]:
                    cert = f" ({alt.certification})" if alt.certification else ""
                    lines.append(f"- **{alt.name}** ({alt.hq_country}){cert} — {alt.cost_delta} cost")
            lines.append("")

    return "\n".join(lines)


def _fallback_clause(finding) -> str:
    return (
        f"The Supplier shall implement and maintain controls ensuring compliance with DORA Art.{finding.article} §{finding.paragraph}. "
        f"The Supplier shall provide documented evidence of implementation, notify material changes without undue delay, and cooperate with audit/testing requirements."
    )


def _detect_report_language(r: ReportArtifact) -> str:
    sample_parts: list[str] = []
    for f in r.findings[:10]:
        sample_parts.append(f.description or "")
        sample_parts.append(f.rationale or "")
        sample_parts.append(f.gap_description or "")
        if f.evidence_spans:
            sample_parts.append(f.evidence_spans[0].text or "")
    sample = f" {' '.join(sample_parts).lower()} "
    if not sample.strip():
        return "en"
    hits = sum(1 for marker in _FRENCH_MARKERS if marker in sample)
    return "fr" if hits >= 3 else "en"


async def _draft_clause_text(llm, finding, proposal_detail: str | None = None, language: str = "en") -> str:
    language_instruction = (
        "Return only one concise contract clause in French (90-180 words), formal legal style, no markdown."
        if language == "fr"
        else "Return only one concise contract clause in English (90-180 words), formal legal style, no markdown."
    )
    prompt = (
        "You are drafting legal contract clause language for DORA compliance.\n"
        f"{language_instruction}\n"
        f"DORA reference: Article {finding.article} paragraph {finding.paragraph}\n"
        f"Finding description: {finding.description}\n"
        f"Gap: {finding.gap_description or 'n/a'}\n"
        f"Rationale: {finding.rationale}\n"
        f"Suggested remediation: {proposal_detail or 'n/a'}\n"
    )
    try:
        resp = await chat_with_retry(llm, [ChatMessage(role="user", content=prompt)])
        text = (resp.message.content or "").strip()
        if not text:
            return _fallback_clause(finding)
        return text.replace("\n", " ").strip()
    except Exception:
        return _fallback_clause(finding)


async def _to_compliant_draft_markdown(r: ReportArtifact, *, llm, vendor_name: str | None = None) -> str:
    findings = [f for f in r.findings if f.verdict.value != "met"]
    findings = findings[:10]
    language = _detect_report_language(r)
    proposal_by_obligation = {p.obligation_id: p for p in r.remediation_proposals}
    clause_tasks = [
        _draft_clause_text(
            llm,
            finding=f,
            proposal_detail=proposal_by_obligation.get(f.obligation_id).detail
            if proposal_by_obligation.get(f.obligation_id)
            else None,
            language=language,
        )
        for f in findings
    ]
    clauses = await asyncio.gather(*clause_tasks) if clause_tasks else []

    lines = [
        "# DORA-Compliant Contract Negotiation Draft",
        f"**Session:** {r.session_id}  ",
        f"**Generated:** {r.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Target vendor:** {vendor_name or 'Current supplier'}  ",
        f"**Base contracts:** {', '.join(r.contract_ids)}",
        "",
        "## How To Use This Draft",
        "- Use each proposed clause as redline replacement text for the related obligation.",
        "- Keep business/commercial terms unchanged and negotiate only legal/control language.",
        "- Validate final wording with legal counsel before signature.",
        "",
        "## Priority Renegotiation Items",
    ]

    if not findings:
        lines += [
            "All obligations are currently met in this session. No mandatory renegotiation clause is required.",
            "",
            "## Suggested Governance Clause",
            "The Parties agree to maintain an annual DORA control review and promptly amend this Agreement as needed to reflect regulatory updates.",
        ]
        return "\n".join(lines)

    for i, finding in enumerate(findings, start=1):
        icon = "❌" if finding.verdict.value == "unmet" else "⚠️"
        proposal = proposal_by_obligation.get(finding.obligation_id)
        evidence = finding.evidence_spans[0].text if finding.evidence_spans else "No direct excerpt available in this run."
        lines += [
            f"### {i}. {icon} {finding.obligation_id} (Art.{finding.article} §{finding.paragraph})",
            f"**Current status:** {finding.verdict.value}  ",
            f"**Risk level:** {finding.risk_level}",
            "",
            "**Issue to renegotiate**",
            finding.gap_description or finding.description,
            "",
            "**Current contract excerpt**",
            f"> {evidence}",
            "",
            "**Proposed DORA-compliant clause**",
            clauses[i - 1],
            "",
            "**Negotiation note**",
            proposal.summary if proposal else "Align this clause with DORA requirements and internal policy baselines.",
            "",
        ]

    lines += [
        "## Finalization Checklist",
        "- Legal validation complete",
        "- Vendor acceptance tracked by clause",
        "- Updated annexes and notification timelines confirmed",
        "- Governance owner and review cadence documented",
    ]
    return "\n".join(lines)


def _phrase_candidates(phrase: str) -> list[str]:
    cleaned = _SPACE_RE.sub(" ", phrase or "").strip()
    if not cleaned:
        return []
    words = cleaned.split(" ")
    out = [cleaned]
    if len(words) > 14:
        out.append(" ".join(words[:14]))
    if len(words) > 8:
        out.append(" ".join(words[:8]))
    if len(words) > 6:
        mid = max(0, len(words) // 2 - 3)
        out.append(" ".join(words[mid : mid + 7]))
    if len(words) > 5:
        out.append(" ".join(words[-6:]))
    return list(dict.fromkeys([x for x in out if x]))


def _find_rects_for_phrase(page: pymupdf.Page, phrase: str) -> tuple[list[pymupdf.Rect], str | None]:
    for candidate in _phrase_candidates(phrase):
        rects = page.search_for(candidate)
        if rects:
            return rects, candidate
    return [], None


def _replace_rect_with_text(page: pymupdf.Page, rect: pymupdf.Rect, new_text: str) -> bool:
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()
    for size in (8.5, 8.0, 7.5, 7.0, 6.5):
        remaining = page.insert_textbox(
            rect,
            new_text,
            fontsize=size,
            color=(0.08, 0.11, 0.16),
            lineheight=1.15,
            align=0,
            fontname="helv",
        )
        if remaining >= 0:
            return True
    return False


def _add_appendix_page(doc: pymupdf.Document, title: str, body: str) -> None:
    page = doc.new_page()
    margin = 48
    content = f"{title}\n\n{body}"
    page.insert_textbox(
        pymupdf.Rect(margin, margin, page.rect.width - margin, page.rect.height - margin),
        content,
        fontsize=10,
        fontname="helv",
        color=(0.08, 0.11, 0.16),
        lineheight=1.2,
    )


async def _build_compliant_pdf_bytes(path: str, report: ReportArtifact, llm, vendor_name: str | None = None) -> bytes:
    findings = [f for f in report.findings if f.verdict.value != "met"][:10]
    language = _detect_report_language(report)
    proposal_by_obligation = {p.obligation_id: p for p in report.remediation_proposals}
    clauses = (
        await asyncio.gather(
            *[
                _draft_clause_text(
                    llm,
                    finding=f,
                    proposal_detail=proposal_by_obligation.get(f.obligation_id).detail
                    if proposal_by_obligation.get(f.obligation_id)
                    else None,
                    language=language,
                )
                for f in findings
            ]
        )
        if findings
        else []
    )

    with pymupdf.open(path) as doc:
        for idx, finding in enumerate(findings):
            replacement = clauses[idx]
            source_quote = finding.evidence_spans[0].text if finding.evidence_spans else ""
            replaced = False

            if source_quote:
                for page in doc:
                    rects, _ = _find_rects_for_phrase(page, source_quote)
                    if not rects:
                        continue
                    # Merge close rectangles into one clause block
                    block = rects[0]
                    for r in rects[1:]:
                        block |= r
                    block.x0 = max(24, block.x0 - 4)
                    block.y0 = max(24, block.y0 - 2)
                    block.x1 = min(page.rect.width - 24, block.x1 + 4)
                    block.y1 = min(page.rect.height - 24, block.y1 + 36)

                    clipped = replacement
                    if len(clipped) > 980:
                        clipped = clipped[:980].rsplit(" ", 1)[0] + " ... [see DORA appendix]"

                    ok = _replace_rect_with_text(page, block, clipped)
                    if not ok:
                        page.insert_text(
                            pymupdf.Point(block.x0, block.y0 + 10),
                            "[DORA compliant clause - see appendix]",
                            fontsize=8,
                            fontname="helv",
                            color=(0.1, 0.2, 0.6),
                        )
                    replaced = True
                    break

            if not replaced:
                # keep fidelity: do not force arbitrary edits if no reliable anchor found
                _add_appendix_page(
                    doc,
                    f"Appendix - {finding.obligation_id} Art.{finding.article} §{finding.paragraph}",
                    replacement,
                )
            else:
                _add_appendix_page(
                    doc,
                    f"Appendix - Full replacement clause ({finding.obligation_id})",
                    replacement,
                )

        _add_appendix_page(
            doc,
            "Negotiation Notes",
            "\n".join(
                [
                    f"- Target vendor: {vendor_name or 'Current supplier'}",
                    f"- Session: {report.session_id}",
                    f"- Generated from DORA findings and remediation guidance.",
                ]
            ),
        )
        return doc.tobytes()
