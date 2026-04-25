"""
EvaluatorAgent — maps DORA Art. 30 requirements to vendor contract clauses
via RAG corpus query + Gemini classification.

Flow for each DORA article:
  1. query_corpus("[VendorName | category] <requirement text>") → top-5 chunks
  2. Pass chunks as clause evidence to CLASSIFICATION_PROMPT
  3. Gemini → compliance_status + score + evidence
  4. Aggregate 8 article scores → overall_score
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
)
from app.services.rag_engine import get_or_create_corpus, query_corpus
from app.services.vertex_ai import generate

# Mirrors chunker._CATEGORY_PATTERNS — maps DORA articles to their chunk category
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
_ARTICLE_TO_CATEGORY = {v: k for k, v in _CATEGORY_TO_ARTICLE.items()}


def _parse_json(text: str) -> dict:
    """Strip optional markdown fences then parse JSON."""
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
    """
    Evaluates a vendor's compliance against DORA Article 30 by querying
    the RAG corpus (which contains pre-indexed contract chunks + DORA/ISO reference)
    and classifying each requirement with Gemini.
    """

    async def evaluate(
        self,
        vendor_name: str,
        document_id: str,
    ) -> EvaluationResult:
        """
        Evaluate vendor compliance for all 8 DORA Art. 30 sub-requirements.

        Uses query_corpus() to retrieve the most relevant contract chunks for
        each DORA article, then asks Gemini to classify compliance.
        The corpus already contains:
          - Chunks from all uploaded contracts (prefixed "[VendorName | category]")
          - DORA Art. 30 reference items
          - ISO 27001 controls
          - Bank internal rules
        """
        corpus_name = get_or_create_corpus()
        mappings: list[ComplianceMapping] = []
        missing_articles: list[str] = []

        for article, req in DORA_ARTICLE_30_TO_ISO.items():
            category = _ARTICLE_TO_CATEGORY.get(article, "general")

            # Query mirrors the chunk format written by extractor._format_for_rag():
            # "[VendorName | category] requirement check-points"
            # The vendor prefix steers the RAG toward that vendor's chunks.
            query = (
                f"[{vendor_name} | {category}] "
                f"{req['description']}. "
                f"{'. '.join(req['check_points'])}"
            )
            chunks = query_corpus(corpus_name, query, top_k=5)

            if not chunks:
                missing_articles.append(article)
                mappings.append(ComplianceMapping(
                    dora_article=article,
                    iso_control=req.get("iso_control"),
                    clause_id="MISSING",
                    status=ComplianceStatus.NON_COMPLIANT,
                    evidence="No relevant clause found in the corpus for this vendor.",
                    score=0.0,
                ))
                continue

            # Concatenate top-3 chunks as evidence for Gemini (most relevant first)
            clause_text = "\n\n---\n\n".join(c["text"] for c in chunks[:3])
            # Extract SLA values from chunk text if present (numeric patterns)
            sla_matches = re.findall(
                r"(?:RTO|RPO|availability|uptime|SLA)[^\d]*(\d+[\.,]?\d*\s*(?:h|hours?|%|min))",
                clause_text, re.I,
            )
            sla_text = ", ".join(sla_matches) if sla_matches else "Not explicitly stated"

            prompt = CLASSIFICATION_PROMPT.format(
                requirement_article=article,
                requirement_title=req["description"],
                requirement_text=req["iso_description"],
                check_points=", ".join(req["check_points"]),
                vendor_name=vendor_name,
                clause_text=clause_text[:2500],
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

            # clause_id encodes the source: document + article for traceability
            article_slug = article.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "")
            mappings.append(ComplianceMapping(
                dora_article=article,
                iso_control=req.get("iso_control"),
                clause_id=f"{document_id}_{article_slug}",
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
