"""ExtractionAgent — pulls structured ContractExtraction from raw contract text.

Uses JSON-mode prompting (not function-calling) because Cerebras inference
is OpenAI-compatible but tool-calling reliability varies by model.
The LLM is asked to return a strict JSON block; we parse + validate with
Pydantic. On failure we retry once with an explicit correction prompt.
"""

import json
import re
import structlog

from llama_index.core.llms import LLM

from app.schemas import ContractExtraction, EvidenceSpan, ServiceClause

log = structlog.get_logger()

_SYSTEM = """\
You are a legal-tech AI specialised in DORA (EU 2022/2554) compliance.
Your task is to extract structured information from a vendor/ICT contract.
Return ONLY a valid JSON object matching the schema below. No markdown fences.

Schema:
{
  "vendor_name": "string — official vendor company name",
  "vendor_country": "string — ISO 3166-1 alpha-2 or full country name, or null",
  "services": [
    {"service_name": "string", "sla_hours": float_or_null}
  ],
  "covered_obligation_ids": ["list of DORA Art.30 obligation ids present in the contract"],
  "evidence_spans": [
    {"text": "verbatim excerpt ≤ 200 chars", "page": integer_or_0}
  ],
  "sub_vendors": ["list of third-party vendor names mentioned as sub-processors or sub-contractors"]
}

Available DORA Art.30 obligation ids (use only these):
dora-art30-2a, dora-art30-2b, dora-art30-2c, dora-art30-2d, dora-art30-2e,
dora-art30-3a, dora-art30-3b, dora-art30-3c, dora-art30-3d, dora-art30-3e,
dora-art30-3f, dora-art30-3g
"""

_MAX_CONTRACT_CHARS = 12_000  # ~3 k tokens — keep within Cerebras context budget


def _truncate(text: str) -> str:
    if len(text) > _MAX_CONTRACT_CHARS:
        return text[:_MAX_CONTRACT_CHARS] + "\n[... truncated ...]"
    return text


def _parse_json_from_response(raw: str) -> dict:
    """Strip markdown fences if LLM wraps the JSON despite instruction."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


def _build_extraction(contract_id: str, data: dict) -> ContractExtraction:
    services = [
        ServiceClause(
            service_name=s.get("service_name", ""),
            sla_hours=s.get("sla_hours"),
        )
        for s in data.get("services", [])
    ]
    spans = [
        EvidenceSpan(
            text=e.get("text", ""),
            page=int(e.get("page", 0)),
            document_id=contract_id,
            node_id="",  # resolved in indexing phase
        )
        for e in data.get("evidence_spans", [])
    ]
    return ContractExtraction(
        contract_id=contract_id,
        vendor_name=data.get("vendor_name", "Unknown"),
        vendor_country=data.get("vendor_country"),
        services=services,
        covered_obligation_ids=data.get("covered_obligation_ids", []),
        evidence_spans=spans,
        sub_vendors=data.get("sub_vendors", []),
        raw_text_preview=data.get("_preview", ""),
    )


async def run_extraction(llm: LLM, contract_id: str, full_text: str) -> ContractExtraction:
    """Extract structured ContractExtraction from contract text using the LLM."""
    user_msg = f"Contract text:\n\n{_truncate(full_text)}"

    from llama_index.core.llms import ChatMessage

    messages = [
        ChatMessage(role="system", content=_SYSTEM),
        ChatMessage(role="user", content=user_msg),
    ]

    response = await llm.achat(messages)
    raw = response.message.content.strip()
    log.debug("extraction_raw_response", contract_id=contract_id, chars=len(raw))

    try:
        data = _parse_json_from_response(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("extraction_json_parse_failed", contract_id=contract_id, error=str(exc))
        # Retry with explicit correction prompt
        correction = [
            *messages,
            ChatMessage(role="assistant", content=raw),
            ChatMessage(
                role="user",
                content="Your response was not valid JSON. Return ONLY the JSON object, no markdown.",
            ),
        ]
        response2 = await llm.achat(correction)
        data = _parse_json_from_response(response2.message.content.strip())

    extraction = _build_extraction(contract_id, data)
    log.info(
        "extraction_complete",
        contract_id=contract_id,
        vendor=extraction.vendor_name,
        services=len(extraction.services),
        obligations=len(extraction.covered_obligation_ids),
    )
    return extraction
