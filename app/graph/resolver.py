"""Entity resolution — deduplicate vendor names before upsert.

Strategy (cheapest to most expensive):
1. Exact match on normalised name → reuse existing id.
2. Fuzzy token-sort ratio ≥ 90 (rapidfuzz) → reuse existing id.
3. Otherwise → new vendor, new id.

Embedding-based cosine similarity is deferred to a future phase
(requires storing embeddings in Neo4j or a side-store).
"""

from rapidfuzz import fuzz

_FUZZY_THRESHOLD = 90.0


def _normalise(name: str) -> str:
    return name.lower().strip()


def resolve_vendor_id(candidate: str, known_vendors: dict[str, str]) -> str:
    """Return the canonical vendor id for `candidate`.

    Args:
        candidate: Vendor name extracted from a contract.
        known_vendors: Mapping of {normalised_name: vendor_id} for all
                       vendors already in the graph.

    Returns:
        Existing vendor_id if a match is found, otherwise a new slug-based id.
    """
    norm = _normalise(candidate)

    if norm in known_vendors:
        return known_vendors[norm]

    for known_norm, known_id in known_vendors.items():
        if fuzz.token_sort_ratio(norm, known_norm) >= _FUZZY_THRESHOLD:
            return known_id

    slug = norm.replace(" ", "_").replace(".", "_")
    return f"vendor:{slug}"
