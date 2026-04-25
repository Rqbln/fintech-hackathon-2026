"""Shared in-memory store (hackathon MVP — resets on container restart)."""

# document_id -> VendorDocument.model_dump()
documents: dict[str, dict] = {}

# document_id -> EvaluationResult.model_dump()
evaluations: dict[str, dict] = {}
