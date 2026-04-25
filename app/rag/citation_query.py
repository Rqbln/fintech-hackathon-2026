"""CitationQueryEngine wrapper — every answer must cite sources."""

from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import CitationQueryEngine


def make_citation_engine(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
    citation_chunk_size: int = 512,
) -> CitationQueryEngine:
    """Return a CitationQueryEngine that requires source citations for every response.

    The engine retrieves top-k chunks, inserts them as numbered sources into the
    prompt, then asks the LLM to cite [1], [2], etc. in its answer. Source nodes
    in the response carry page and metadata for EvidenceSpan construction.
    """
    return CitationQueryEngine.from_args(
        index,
        similarity_top_k=similarity_top_k,
        citation_chunk_size=citation_chunk_size,
    )
