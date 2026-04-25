"""RemediationAgent — generates sovereign EU remediation proposals for each gap finding.

For each unmet/partially_met finding:
  1. Looks up the vendor in sovereign_alternatives.yaml (fuzzy match).
  2. Asks the LLM for a concise remediation plan.
  3. Returns a list of RemediationProposal.
"""

import json
import re
from pathlib import Path

import structlog
import yaml
from llama_index.core.llms import ChatMessage, LLM
from rapidfuzz import fuzz

from app.llm.retry import chat_with_retry
from app.schemas import AlternativeVendor, ObligationFinding, RemediationProposal, Verdict

log = structlog.get_logger()

_SOVEREIGN_PATH = Path(__file__).parent.parent / "data" / "sovereign_alternatives.yaml"
_FUZZY_THRESHOLD = 80.0

_SYSTEM = """\
You are a DORA compliance consultant specialised in EU sovereign cloud and fintech regulation.
Given a DORA gap finding and an optional list of EU-sovereign alternative vendors,
write a concise remediation plan for the financial institution.

Return ONLY valid JSON — no markdown fences:
{
  "priority": "critical" | "high" | "medium" | "low",
  "summary": "one-sentence action (≤ 120 chars)",
  "detail": "2–4 paragraph remediation plan referencing the specific DORA obligation and timeline",
  "estimated_effort_days": integer_or_null,
  "references": ["DORA Art. XX", ...]
}
"""


def _load_alternatives() -> list[dict]:
    data = yaml.safe_load(_SOVEREIGN_PATH.read_text())
    return data["alternatives"]


def _match_vendor(vendor_name: str, alternatives: list[dict]) -> dict | None:
    """Find the best-matching entry in sovereign_alternatives.yaml."""
    norm = vendor_name.lower().strip()
    best_score, best_entry = 0.0, None
    for entry in alternatives:
        aliases = [entry["vendor"]] + entry.get("vendor_aliases", [])
        for alias in aliases:
            score = fuzz.token_sort_ratio(norm, alias.lower())
            if score > best_score:
                best_score, best_entry = score, entry
    return best_entry if best_score >= _FUZZY_THRESHOLD else None


def _build_alternatives(entry: dict) -> list[AlternativeVendor]:
    return [
        AlternativeVendor(
            name=p["name"],
            hq_country=p.get("hq_country", ""),
            eu_sovereign=p.get("eu_sovereign", False),
            certification="SecNumCloud" if p.get("secnumcloud_certified") else "",
            services_covered=p.get("services_covered", []),
            cost_delta=p.get("cost_delta", ""),
            feature_delta=p.get("feature_delta", ""),
            website=p.get("url", ""),
        )
        for p in entry.get("proposals", [])
    ]


def _parse_remediation_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


async def _remediate_one(
    llm: LLM,
    finding: ObligationFinding,
    vendor_name: str,
    alternatives_list: list[AlternativeVendor],
) -> RemediationProposal:
    alt_summary = "\n".join(
        f"- {a.name} ({a.hq_country}, sovereign={a.eu_sovereign}): {a.feature_delta[:100]}"
        for a in alternatives_list[:3]
    )

    user_msg = (
        f"DORA Art.{finding.article} §{finding.paragraph}: {finding.description[:300]}\n"
        f"Verdict: {finding.verdict.value} | Gap: {finding.gap_description[:200]}\n"
        f"Vendor: {vendor_name}\n\n"
        f"EU-sovereign alternatives:\n{alt_summary or 'None identified'}"
    )

    messages = [
        ChatMessage(role="system", content=_SYSTEM),
        ChatMessage(role="user", content=user_msg),
    ]
    resp = await chat_with_retry(llm, messages)
    raw = resp.message.content.strip()

    try:
        data = _parse_remediation_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("remediation_json_failed", obligation_id=finding.obligation_id, error=str(exc))
        data = {
            "priority": "medium",
            "summary": "Review and remediate contract gap",
            "detail": f"LLM parse error ({exc}). Manual review required.",
            "estimated_effort_days": None,
            "references": [f"DORA Art. {finding.article}"],
        }

    proposal = RemediationProposal(
        obligation_id=finding.obligation_id,
        vendor_name=vendor_name,
        priority=data.get("priority", "medium"),
        summary=data.get("summary", ""),
        detail=data.get("detail", ""),
        sovereign_alternatives=alternatives_list,
        estimated_effort_days=data.get("estimated_effort_days"),
        references=data.get("references", []),
    )
    log.info(
        "remediation_proposal",
        obligation_id=finding.obligation_id,
        priority=proposal.priority,
        alternatives=len(alternatives_list),
    )
    return proposal


async def run_remediation(
    llm: LLM,
    findings: list[ObligationFinding],
    vendor_name: str,
) -> list[RemediationProposal]:
    """Generate remediation proposals for all unmet/partially_met findings."""
    alternatives_db = _load_alternatives()
    matched_entry = _match_vendor(vendor_name, alternatives_db)
    alternatives_list = _build_alternatives(matched_entry) if matched_entry else []

    proposals = []
    for finding in findings:
        if finding.verdict in (Verdict.UNMET, Verdict.PARTIALLY_MET):
            proposal = await _remediate_one(llm, finding, vendor_name, alternatives_list)
            proposals.append(proposal)

    log.info("remediation_complete", vendor=vendor_name, proposals=len(proposals))
    return proposals
