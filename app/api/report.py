"""Report export — serves the last assembled ReportArtifact as JSON or Markdown."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas import ReportArtifact

router = APIRouter()

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
