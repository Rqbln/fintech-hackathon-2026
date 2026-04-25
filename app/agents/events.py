"""Shared event types for the ContractIngestionWorkflow."""

from llama_index.core.workflow import Event

from app.schemas import ContractExtraction


class DocParsedEvent(Event):
    contract_id: str
    full_text: str          # concatenated page text
    node_ids: list[str]     # Vertex AI VS node ids after embedding


class ExtractedEvent(Event):
    extraction: ContractExtraction


class GraphUpdatedEvent(Event):
    extraction: ContractExtraction
    vendor_id: str


class IngestionResult(Event):
    contract_id: str
    node_ids: list[str]
    vendor_id: str
    vendor_name: str
    criticality_score: float
