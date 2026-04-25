"""GapAnalysisAgent — evaluates each DORA Art.30 obligation against a contract.

For each obligation the agent:
  1. Queries the CitationQueryEngine with the obligation text + contract_id filter.
  2. Asks the LLM to produce a structured verdict (met / partially_met / unmet).
  3. Returns a list of ObligationFinding with source citations.

JSON-mode prompting — same pattern as ExtractionAgent.
"""

import json
import re
from pathlib import Path

import structlog
import yaml
from llama_index.core.llms import ChatMessage, LLM
from llama_index.core.query_engine import BaseQueryEngine

from app.llm.retry import chat_with_retry
from app.schemas import EvidenceSpan, ObligationFinding, Verdict

log = structlog.get_logger()

_OBLIGATIONS_PATH = Path(__file__).parent.parent / "data" / "dora_obligations.yaml"

_SYSTEM = """\
You are a DORA (EU 2022/2554) compliance analyst. Given a DORA obligation and excerpts
from a vendor contract, assess whether the contract satisfies the obligation.

Return ONLY a valid JSON object — no markdown fences:
{
  "verdict": "met" | "partially_met" | "unmet" | "unknown",
  "rationale": "one to three sentence explanation citing specific contract language",
  "gap_description": "what is missing or weak (empty string if verdict is met)",
  "risk_level": "low" | "medium" | "high" | "critical",
  "evidence_quotes": ["verbatim excerpt from contract that is most relevant, ≤ 150 chars"]
}

Be strict: 'met' requires explicit contractual language. 'partially_met' if present but incomplete.
'unmet' if the obligation is not addressed at all.
"""


def _load_obligations() -> list[dict]:
    data = yaml.safe_load(_OBLIGATIONS_PATH.read_text())
    return data["obligations"]


def _parse_verdict_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


async def _evaluate_one(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    obligation: dict,
    contract_id: str,
    contract_text_preview: str,
) -> ObligationFinding:
    ob_id = obligation["id"]

    # Step 1: retrieve relevant contract chunks via RAG (DORA regulation context only)
    # Use aquery — sync query() calls GoogleGenAI._chat() → asyncio.run() which
    # raises RuntimeError when called from FastAPI's running event loop.
    query = f"DORA Article {obligation['article']} paragraph {obligation['paragraph']}: {obligation['text']}"
    rag_response = await citation_engine.aquery(query)
    rag_context = str(rag_response)[:800]

    # Step 2: LLM verdict — contract text is the primary evidence source
    user_msg = (
        f"DORA Obligation (Art.{obligation['article']} §{obligation['paragraph']}):\n"
        f"{obligation['text']}\n\n"
        f"Pass criteria: {obligation.get('pass_criteria', '')[:300]}\n\n"
        f"Contract text:\n{contract_text_preview[:3000]}"
    )
    messages = [
        ChatMessage(role="system", content=_SYSTEM),
        ChatMessage(role="user", content=user_msg),
    ]
    resp = await chat_with_retry(llm, messages)
    raw = resp.message.content.strip()

    try:
        data = _parse_verdict_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("gap_analysis_json_failed", obligation_id=ob_id, error=str(exc))
        data = {
            "verdict": "unknown",
            "rationale": f"LLM parse error: {exc}",
            "gap_description": "",
            "risk_level": "medium",
            "evidence_quotes": [],
        }

    evidence_spans = [
        EvidenceSpan(text=q, page=0, document_id=contract_id, node_id="")
        for q in data.get("evidence_quotes", [])
    ]

    verdict_str = data.get("verdict", "unknown")
    try:
        verdict = Verdict(verdict_str)
    except ValueError:
        verdict = Verdict.UNKNOWN

    finding = ObligationFinding(
        obligation_id=ob_id,
        article=obligation["article"],
        paragraph=obligation["paragraph"],
        description=obligation["text"],
        verdict=verdict,
        rationale=data.get("rationale", ""),
        evidence_spans=evidence_spans,
        gap_description=data.get("gap_description", ""),
        risk_level=data.get("risk_level", "medium"),
    )
    log.info("gap_finding", obligation_id=ob_id, verdict=verdict.value, risk=finding.risk_level)
    return finding


async def run_gap_analysis(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    contract_id: str,
    contract_text_preview: str,
    obligation_ids: list[str] | None = None,
) -> list[ObligationFinding]:
    """Evaluate all (or a subset of) DORA Art.30 obligations against a contract."""
    obligations = _load_obligations()
    if obligation_ids:
        obligations = [o for o in obligations if o["id"] in obligation_ids]

    findings = []
    for ob in obligations:
        finding = await _evaluate_one(llm, citation_engine, ob, contract_id, contract_text_preview)
        findings.append(finding)

    return findings
