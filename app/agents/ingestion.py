"""ContractIngestionWorkflow — orchestrates the full ingest pipeline.

Flow:
  StartEvent
    → parse_and_index   → DocParsedEvent
    → extract           → ExtractedEvent
    → build_graph       → GraphUpdatedEvent
    → score_risks       → StopEvent(IngestionResult)
"""

import structlog
from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step

from app.rag.ingestion_pipeline import ingest_pdf, parse_pdf

from .events import DocParsedEvent, ExtractedEvent, GraphUpdatedEvent, IngestionResult
from .extraction import run_extraction
from .graph_builder import build_graph
from .risk_scorer import recompute_all

log = structlog.get_logger()


class ContractIngestionWorkflow(Workflow):
    """End-to-end contract ingest: PDF → VS index → extraction → graph → scoring."""

    def __init__(self, llm, extraction_llm, embed_model, vector_store, neo4j_driver, llama_parse_api_key=None, **kwargs):
        super().__init__(**kwargs)
        self._llm = llm
        self._extraction_llm = extraction_llm  # qwen — 65k context, used only here
        self._embed_model = embed_model
        self._vector_store = vector_store
        self._neo4j = neo4j_driver
        self._llama_parse_api_key = llama_parse_api_key

    @step
    async def parse_and_index(self, ev: StartEvent) -> DocParsedEvent:
        file_bytes: bytes = ev.get("file_bytes")
        contract_id: str = ev.get("contract_id")

        # Parse PDF to pages
        pages = parse_pdf(file_bytes, self._llama_parse_api_key)
        full_text = "\n\n".join(p["text"] for p in pages)

        # Embed + upsert into Vertex AI VS
        node_ids = await ingest_pdf(
            file_bytes=file_bytes,
            document_id=contract_id,
            doc_type="contract",
            vector_store=self._vector_store,
            embed_model=self._embed_model,
            contract_id=contract_id,
            llama_parse_api_key=self._llama_parse_api_key,
        )

        log.info("workflow_parsed_and_indexed", contract_id=contract_id, nodes=len(node_ids))
        return DocParsedEvent(contract_id=contract_id, full_text=full_text, node_ids=node_ids)

    @step
    async def extract(self, ev: DocParsedEvent) -> ExtractedEvent:
        extraction = await run_extraction(self._extraction_llm, ev.contract_id, ev.full_text)
        return ExtractedEvent(extraction=extraction, node_ids=ev.node_ids)

    @step
    async def build_graph_step(self, ev: ExtractedEvent) -> GraphUpdatedEvent:
        vendor_id = await build_graph(self._neo4j, ev.extraction)
        return GraphUpdatedEvent(extraction=ev.extraction, vendor_id=vendor_id, node_ids=ev.node_ids)

    @step
    async def score_risks(self, ev: GraphUpdatedEvent) -> StopEvent:
        scored = await recompute_all(self._neo4j)

        vendor_score = next(
            (v["criticality_score"] for v in scored if v["id"] == ev.vendor_id),
            0.0,
        )

        result = IngestionResult(
            contract_id=ev.extraction.contract_id,
            node_ids=ev.node_ids,
            vendor_id=ev.vendor_id,
            vendor_name=ev.extraction.vendor_name,
            criticality_score=vendor_score,
        )
        log.info(
            "workflow_complete",
            contract_id=result.contract_id,
            vendor=result.vendor_name,
            criticality_score=result.criticality_score,
        )
        return StopEvent(result=result)
