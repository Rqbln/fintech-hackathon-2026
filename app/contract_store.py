"""In-memory contract text store — keyed by contract_id, populated during ingest."""

_store: dict[str, str] = {}
_MAX_CHARS = 20_000  # ~5 k tokens — enough context for gap analysis


def store(contract_id: str, full_text: str) -> None:
    _store[contract_id] = full_text[:_MAX_CHARS]


def get(contract_id: str) -> str:
    return _store.get(contract_id, "")
