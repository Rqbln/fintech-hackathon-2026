"""GapAnalysisAgent — evaluates DORA Art.30 obligations against a contract.

Each obligation is an independent LLM call. A semaphore caps concurrency so
we don't burst-hit Cerebras's rate limit. Results are yielded as they complete
so the caller can stream them to the frontend immediately.
"""

import asyncio
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
_CONCURRENCY = 4  # max simultaneous LLM calls — stays under Cerebras 100 RPM burst

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
    obligation: dict,
    contract_id: str,
    contract_text_preview: str,
) -> ObligationFinding:
    """Single obligation evaluation — one LLM call, no RAG (contract text is primary)."""
    ob_id = obligation["id"]

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
            "rationale": f"Parse error: {exc}",
            "gap_description": "",
            "risk_level": "medium",
            "evidence_quotes": [],
        }

    evidence_spans = [
        EvidenceSpan(text=q, page=0, document_id=contract_id, node_id="")
        for q in data.get("evidence_quotes", [])
    ]

    try:
        verdict = Verdict(data.get("verdict", "unknown"))
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


async def stream_gap_analysis(
    llm: LLM,
    contract_id: str,
    contract_text_preview: str,
    obligation_ids: list[str] | None = None,
):
    """Async generator that yields ObligationFinding as each evaluation completes.

    Uses a semaphore to cap concurrency at _CONCURRENCY simultaneous calls.
    Drop the citation_engine dependency — contract text is the primary source,
    which is faster and avoids nested asyncio issues with Vertex AI VS.
    """
    obligations = _load_obligations()
    if obligation_ids:
        obligations = [o for o in obligations if o["id"] in obligation_ids]

    log.info("gap_analysis_start", obligations=len(obligations), contract_id=contract_id)
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def eval_with_sem(ob: dict) -> ObligationFinding:
        async with sem:
            return await _evaluate_one(llm, ob, contract_id, contract_text_preview)

    tasks = [asyncio.create_task(eval_with_sem(ob)) for ob in obligations]

    for coro in asyncio.as_completed(tasks):
        try:
            finding = await coro
            yield finding
        except Exception as exc:
            log.warning("gap_finding_failed", error=str(exc)[:120])

    log.info("gap_analysis_complete", contract_id=contract_id)


# Kept for backward compat (scripts/test_pipeline.py etc.)
async def run_gap_analysis(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    contract_id: str,
    contract_text_preview: str,
    obligation_ids: list[str] | None = None,
) -> list[ObligationFinding]:
    findings: list[ObligationFinding] = []
    async for f in stream_gap_analysis(llm, contract_id, contract_text_preview, obligation_ids):
        findings.append(f)
    return findings
