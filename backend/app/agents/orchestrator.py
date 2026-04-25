"""
Agent Orchestrateur -- Detects subcontractors from contract text via RAG + Gemini,
then assembles the full analysis (evaluation + graph) for a document.
"""

import json
import logging

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from app.agents.extractor import ExtractorAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.prompts import SYSTEM_INSTRUCTION
from app.config import GCP_PROJECT, GCP_REGION, GEMINI_MODEL
from app.services.graph_builder import build_graph

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini (lazy init, shared with evaluator but separate instance)
# ---------------------------------------------------------------------------

_gemini_initialized = False

def _get_model() -> GenerativeModel:
    global _gemini_initialized
    if not _gemini_initialized:
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        _gemini_initialized = True
    return GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION)


_SUBCONTRACTOR_PROMPT = """You are analyzing a vendor ICT contract to identify all subcontractors (sous-traitants / fourth-party providers) mentioned.

CONTRACT EXCERPT (subcontracting clauses):
{clause_text}

TASK: Extract every subcontractor/sub-processor explicitly named or described.

Respond ONLY with valid JSON:
{{
  "subcontractors": [
    {{
      "name": "<subcontractor legal name or 'Unknown' if unnamed>",
      "service": "<service provided to the main vendor>",
      "data_location": "<country/region where data is processed, or 'Not specified'>",
      "risk_flag": <true if: no prior approval required, data outside EEA, or subcontracting chain opaque>,
      "evidence": "<verbatim excerpt that reveals this subcontractor>"
    }}
  ]
}}

If no subcontractors are mentioned, return {{"subcontractors": []}}.
risk_flag = true if any of:
- Vendor can change subcontractors without prior bank approval
- Data processed outside EEA (not FR/DE/NL/BE/LU/IE etc.)
- Subcontractor chain is described as unlimited or not enumerated
"""


async def _detect_subcontractors(chunks: list[dict]) -> list[dict]:
    """Call Gemini to extract subcontractors from subcontracting chunks."""
    import asyncio

    if not chunks:
        return []

    clause_text = "\n---\n".join(
        f"[page {c['page']}] {c['text']}" for c in chunks
    )[:3000]

    prompt = _SUBCONTRACTOR_PROMPT.format(clause_text=clause_text)

    model = _get_model()
    config = GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1,
        max_output_tokens=8192,
    )

    def _sync():
        return model.generate_content(prompt, generation_config=config)

    try:
        response = await asyncio.to_thread(_sync)
        raw = response.text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1:
                data = {}
            else:
                candidate = raw[start:end + 1]
                candidate = re.sub(r"//[^\n]*", "", candidate)
                candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
                data = json.loads(candidate)
        subs = data.get("subcontractors", [])
        for sub in subs:
            if "page" not in sub:
                sub["page"] = chunks[0]["page"] if chunks else 1
        return subs
    except Exception as e:
        log.error("Subcontractor detection failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class OrchestratorAgent:
    """
    Full analysis pipeline for one contract:
    1. EvaluatorAgent → DORA compliance score + alerts
    2. RAG subcontracting chunks → Gemini → subcontractors list
    3. graph_builder → React Flow graph
    """

    def __init__(self) -> None:
        self._extractor  = ExtractorAgent()
        self._evaluator  = EvaluatorAgent()

    async def analyze(
        self,
        doc_id: str,
        vendor_name: str,
        filename: str,
    ) -> dict:
        """
        Full analysis for one indexed contract.

        Returns:
            {
                "doc_id": str,
                "vendor_name": str,
                "filename": str,
                "evaluation": { compliance_score, status, alerts, mappings, category_scores },
                "subcontractors": [ { name, service, data_location, risk_flag, page, evidence } ],
                "graph": { nodes, edges, meta },   # React Flow ready
            }
        """
        # 1. DORA compliance evaluation (RAG + Gemini x6 categories)
        log.info("Evaluating DORA compliance for doc_id=%s", doc_id)
        evaluation = await self._evaluator.evaluate(doc_id, vendor_name)

        # 2. Subcontractor detection (RAG on subcontracting category)
        log.info("Detecting subcontractors for doc_id=%s", doc_id)
        sub_chunks = await self._extractor.search(
            query="sous-traitant subcontractor third-party provider approbation chain",
            doc_id=doc_id,
            top_k=5,
        )
        # Only keep chunks actually classified as subcontracting
        sub_chunks = [c for c in sub_chunks if c.get("category") == "subcontracting"] or sub_chunks[:3]
        subcontractors = await _detect_subcontractors(sub_chunks)

        # 3. Build React Flow graph
        log.info("Building relationship graph for doc_id=%s", doc_id)
        graph = build_graph(
            doc_id=doc_id,
            vendor_name=vendor_name,
            filename=filename,
            evaluation=evaluation,
            subcontractors=subcontractors,
        )

        return {
            "doc_id":         doc_id,
            "vendor_name":    vendor_name,
            "filename":       filename,
            "evaluation":     evaluation,
            "subcontractors": subcontractors,
            "graph":          graph,
        }

    # Legacy stubs kept for backwards compatibility
    async def gap_analysis(self, vendor_evaluation: dict, bank_rules: dict) -> dict:
        return {"gaps": [], "alerts": [], "summary": ""}

    async def generate_roi_entry(self, vendor_data: dict) -> dict:
        return {"roi_entry": {}}
