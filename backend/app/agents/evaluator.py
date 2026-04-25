"""
Agent Evaluateur -- Moteur de conformité DORA Article 30.

Pour chaque contrat indexé :
1. Recherche RAG par catégorie DORA → chunks pertinents
2. Prompt dynamique Gemini (clause + exigence DORA + règle banque)
3. JSON structuré : status, severity, gap, justification, page
4. Score global 0-100 pondéré par criticité
"""

import json
import logging
from pathlib import Path

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from app.agents.extractor import ExtractorAgent
from app.agents.prompts import GAP_ANALYSIS_PROMPT, SYSTEM_INSTRUCTION
from app.config import GCP_PROJECT, GCP_REGION, GEMINI_MODEL
from app.models.dora_mapping import DORA_ARTICLE_30_TO_ISO
from app.models.schemas import Alert, ComplianceMapping, ComplianceStatus, Severity

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference data (loaded once at import)
# ---------------------------------------------------------------------------

_REF = Path(__file__).parent.parent.parent.parent / "reference_data"

def _load_json(name: str) -> list:
    path = _REF / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    log.warning("Reference file not found: %s", path)
    return []

_DORA_REQUIREMENTS: list[dict] = _load_json("dora_article_30.json")
_BANK_RULES: list[dict]        = _load_json("bank_rules_sample.json")

# Map category → dora requirement + bank rule for fast lookup
_DORA_BY_CATEGORY: dict[str, dict] = {r["category"]: r for r in _DORA_REQUIREMENTS}
_BANK_BY_CATEGORY: dict[str, dict] = {r["category"]: r for r in _BANK_RULES}

# Criticality weights for scoring
_WEIGHTS = {"critical": 3, "high": 2, "medium": 1, "low": 1}

# Status → numeric score contribution
_STATUS_SCORE = {
    ComplianceStatus.COMPLIANT:     1.0,
    ComplianceStatus.PARTIAL:       0.5,
    ComplianceStatus.NON_COMPLIANT: 0.0,
    ComplianceStatus.NOT_ASSESSED:  0.5,  # neutral when no clause found
}

# DORA categories to evaluate (maps to chunker categories)
_CATEGORIES = [
    "rto_rpo",
    "audit_rights",
    "data_residency",
    "subcontracting",
    "incident_reporting",
    "exit_strategy",
]


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

_gemini_initialized = False

def _get_model() -> GenerativeModel:
    global _gemini_initialized
    if not _gemini_initialized:
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        _gemini_initialized = True
    return GenerativeModel(
        GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
    )


async def _call_gemini(prompt: str) -> dict:
    """Call Gemini with JSON mode. Returns parsed dict or error dict."""
    import asyncio
    model = _get_model()
    config = GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1,
        max_output_tokens=8192,
    )
    def _sync_call():
        return model.generate_content(prompt, generation_config=config)

    try:
        response = await asyncio.to_thread(_sync_call)
        return json.loads(response.text)
    except Exception as e:
        log.error("Gemini call failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_gap_prompt(
    vendor_name: str,
    category: str,
    chunks: list[dict],
    doc_id: str,
) -> str:
    """Build a GAP_ANALYSIS_PROMPT for one DORA category."""
    dora_req  = _DORA_BY_CATEGORY.get(category, {})
    bank_rule = _BANK_BY_CATEGORY.get(category, {})
    iso_info  = DORA_ARTICLE_30_TO_ISO.get(dora_req.get("article", ""), {})

    vendor_clause = "\n---\n".join(
        f"[page {c['page']}] {c['text']}" for c in chunks
    ) if chunks else "NO CLAUSE FOUND IN CONTRACT"

    # Build specific values section for RTO/RPO rules
    specific_values = ""
    if "rto_hours" in bank_rule:
        specific_values = f"- Required RTO: {bank_rule['rto_hours']}h / RPO: {bank_rule.get('rpo_hours', 'N/A')}h"

    return GAP_ANALYSIS_PROMPT.format(
        rule_id=bank_rule.get("rule_id", f"DORA-{category.upper()}"),
        rule_category=category,
        rule_function=bank_rule.get("function", "All Critical Functions"),
        rule_criticality=bank_rule.get("criticality", dora_req.get("criticality", "high")),
        rule_requirement=bank_rule.get("requirement", dora_req.get("requirement", "")),
        rule_specific_values=specific_values,
        vendor_name=vendor_name,
        contract_ref=doc_id,
        vendor_clause_text=vendor_clause[:2000],  # cap to avoid token overflow
        vendor_sla_values="See clause above",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class EvaluatorAgent:
    """Evaluates vendor compliance against DORA Art. 30 using RAG + Gemini."""

    def __init__(self) -> None:
        self._extractor = ExtractorAgent()

    async def evaluate(
        self,
        doc_id: str,
        vendor_name: str,
    ) -> dict:
        """
        Full evaluation pipeline for one contract.

        Returns:
            {
                "doc_id": str,
                "vendor_name": str,
                "compliance_score": float (0-100),
                "status": "compliant" | "partial" | "non_compliant",
                "alerts": [Alert],
                "mappings": [ComplianceMapping],
                "category_scores": {category: score},
            }
        """
        alerts:   list[dict] = []
        mappings: list[dict] = []
        category_scores: dict[str, float] = {}
        weighted_sum   = 0.0
        weight_total   = 0.0

        for category in _CATEGORIES:
            dora_req  = _DORA_BY_CATEGORY.get(category, {})
            criticality = dora_req.get("criticality", "high")
            weight = _WEIGHTS.get(criticality, 1)

            # 1. RAG — retrieve top-3 chunks for this category
            chunks = await self._extractor.search(
                query=_category_query(category),
                doc_id=doc_id,
                top_k=3,
            )

            # 2. Build prompt + call Gemini
            prompt = _build_gap_prompt(vendor_name, category, chunks, doc_id)
            result = await _call_gemini(prompt)

            if "error" in result:
                status = ComplianceStatus.NOT_ASSESSED
                cat_score = 0.5
            else:
                gap_exists = result.get("gap_exists", False)
                severity_str = result.get("severity", "medium")
                status = _gap_to_status(gap_exists, severity_str)
                cat_score = _STATUS_SCORE[status]

                # Build Alert if gap found
                if gap_exists:
                    page = chunks[0]["page"] if chunks else 0
                    alerts.append({
                        "alert_id": f"{doc_id}_{category}",
                        "vendor_name": vendor_name,
                        "severity": severity_str,
                        "title": result.get("title", f"Gap: {category}"),
                        "description": result.get("description", ""),
                        "dora_reference": dora_req.get("article", ""),
                        "bank_requirement": result.get("bank_requirement_summary", ""),
                        "vendor_guarantee": result.get("vendor_guarantee_summary", ""),
                        "gap_details": result.get("quantitative_gap", ""),
                        "page": page,
                        "category": category,
                        "remediation": result.get("recommended_action", ""),
                    })

            # Build ComplianceMapping
            mappings.append({
                "dora_article": dora_req.get("article", category),
                "iso_control": DORA_ARTICLE_30_TO_ISO.get(
                    dora_req.get("article", ""), {}
                ).get("iso_control"),
                "clause_id": chunks[0]["chunk_id"] if chunks else None,
                "status": status,
                "evidence": chunks[0]["text"][:300] if chunks else "No clause found",
                "score": cat_score,
            })

            category_scores[category] = round(cat_score * 100)
            weighted_sum  += cat_score * weight
            weight_total  += weight

        # Global score 0-100
        global_score = round((weighted_sum / weight_total) * 100) if weight_total else 0
        global_status = _score_to_status(global_score)

        return {
            "doc_id":           doc_id,
            "vendor_name":      vendor_name,
            "compliance_score": global_score,
            "status":           global_status,
            "alerts":           alerts,
            "mappings":         mappings,
            "category_scores":  category_scores,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _category_query(category: str) -> str:
    """Natural language query to retrieve relevant chunks for a DORA category."""
    return {
        "rto_rpo":            "RTO RPO recovery time objective continuité disponibilité service",
        "audit_rights":       "droit audit inspection contrôle fournisseur accès",
        "data_residency":     "localisation données hébergement datacenter pays région",
        "subcontracting":     "sous-traitant prestataire tiers approbation chaîne",
        "incident_reporting": "incident notification signalement délai rapport",
        "exit_strategy":      "résiliation sortie portabilité transition données",
    }.get(category, category)


def _gap_to_status(gap_exists: bool, severity: str) -> ComplianceStatus:
    if not gap_exists:
        return ComplianceStatus.COMPLIANT
    if severity in ("critical", "high"):
        return ComplianceStatus.NON_COMPLIANT
    return ComplianceStatus.PARTIAL


def _score_to_status(score: float) -> str:
    if score >= 80:
        return "compliant"
    if score >= 50:
        return "partial"
    return "non_compliant"
