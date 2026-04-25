"""
EvaluatorAgent — maps each extracted clause to DORA Art. 30 requirements
via Gemini, classifies compliance, and computes a per-document score.
"""

import json
import re
from datetime import datetime, timezone

from app.agents.prompts import CLASSIFICATION_PROMPT, SYSTEM_INSTRUCTION
from app.models.dora_mapping import DORA_ARTICLE_30_TO_ISO
from app.models.schemas import (
    ComplianceMapping,
    ComplianceStatus,
    EvaluationResult,
    ExtractedClause,
    SLAEntry,
)
from app.services.vertex_ai import generate

# Chunker categories → DORA Art. 30 articles (mirrors chunker._CATEGORY_PATTERNS)
_CATEGORY_TO_ARTICLE: dict[str, str] = {
    "service_description": "Art. 30(2)(a)",
    "data_residency":      "Art. 30(2)(b)",
    "data_protection":     "Art. 30(2)(c)",
    "rto_rpo":             "Art. 30(2)(d)",
    "incident_reporting":  "Art. 30(2)(e)",
    "audit_rights":        "Art. 30(2)(f)",
    "exit_strategy":       "Art. 30(2)(g)",
    "subcontracting":      "Art. 30(3)",
}


def _parse_json(text: str) -> dict:
    """Strip optional markdown fences and parse JSON from Gemini response."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _to_status(raw: str, score: float) -> ComplianceStatus:
    try:
        return ComplianceStatus(raw)
    except ValueError:
        if score >= 0.8:
            return ComplianceStatus.COMPLIANT
        if score >= 0.4:
            return ComplianceStatus.PARTIAL
        return ComplianceStatus.NON_COMPLIANT


class EvaluatorAgent:
    """Evaluates vendor compliance against DORA Article 30 and ISO 27001:2022."""

    async def evaluate(
        self,
        clauses: list[ExtractedClause],
        sla_entries: list[SLAEntry],
        vendor_name: str,
        document_id: str,
    ) -> EvaluationResult:
        """
        For each DORA Art. 30 sub-requirement:
        1. Find the most relevant clause (by category, then by keyword fallback).
        2. Ask Gemini to classify compliance and score it.
        3. Aggregate per-article results into an overall compliance score.
        """
        # Index clauses by category
        by_category: dict[str, list[ExtractedClause]] = {}
        for clause in clauses:
            by_category.setdefault(clause.category, []).append(clause)
        general_fallback = by_category.get("general", [])

        sla_text = (
            ", ".join(f"{e.metric}={e.value}{e.unit or ''}" for e in sla_entries)
            or "None provided"
        )

        mappings: list[ComplianceMapping] = []
        missing_articles: list[str] = []

        for article, req in DORA_ARTICLE_30_TO_ISO.items():
            # Find the category that maps to this article
            category = next(
                (cat for cat, art in _CATEGORY_TO_ARTICLE.items() if art == article),
                None,
            )
            candidates = by_category.get(category or "", []) + general_fallback

            if not candidates:
                # No clause covers this requirement → hard non-compliant
                missing_articles.append(article)
                mappings.append(ComplianceMapping(
                    dora_article=article,
                    iso_control=req.get("iso_control"),
                    clause_id="MISSING",
                    status=ComplianceStatus.NON_COMPLIANT,
                    evidence="No clause found in the document covering this requirement.",
                    score=0.0,
                ))
                continue

            # Pick the most substantive clause (longest text, capped at 5 candidates)
            best = max(candidates[:5], key=lambda c: len(c.text))

            prompt = CLASSIFICATION_PROMPT.format(
                requirement_article=article,
                requirement_title=req["description"],
                requirement_text=req["iso_description"],
                check_points=", ".join(req["check_points"]),
                vendor_name=vendor_name,
                clause_text=best.text[:2000],
                sla_values=sla_text,
            )

            try:
                raw = await generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
                data = _parse_json(raw)
                score = max(0.0, min(1.0, float(data.get("score", 0.0))))
                status = _to_status(data.get("compliance_status", "non_compliant"), score)
                evidence = data.get("evidence", "—")
            except Exception as exc:
                score = 0.0
                status = ComplianceStatus.NOT_ASSESSED
                evidence = f"Evaluation error: {exc}"

            mappings.append(ComplianceMapping(
                dora_article=article,
                iso_control=req.get("iso_control"),
                clause_id=best.clause_id,
                status=status,
                evidence=evidence,
                score=score,
            ))

        overall_score = round(
            sum(m.score for m in mappings) / len(mappings) if mappings else 0.0,
            3,
        )

        return EvaluationResult(
            document_id=document_id,
            vendor_name=vendor_name,
            overall_score=overall_score,
            compliance_mappings=mappings,
            missing_articles=missing_articles,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def assess_concentration_risk(self, vendor_id: str) -> dict:
        return {
            "vendor_id": vendor_id,
            "concentration_score": 0.0,
            "dependencies": [],
        }
