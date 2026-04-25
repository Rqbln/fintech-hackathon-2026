import os
import tempfile

import vertexai
from vertexai import rag

from app.config import GCP_PROJECT, RAG_REGION

_CORPUS_DISPLAY_NAME = "regagent-corpus-v1"


def _init() -> None:
    vertexai.init(project=GCP_PROJECT, location=RAG_REGION)


def get_or_create_corpus() -> str:
    """Return the resource name of the RegAgent RAG corpus, creating it if absent."""
    _init()
    for corpus in rag.list_corpora():
        if corpus.display_name == _CORPUS_DISPLAY_NAME:
            return corpus.name
    corpus = rag.create_corpus(
        display_name=_CORPUS_DISPLAY_NAME,
        description="RegAgent DORA compliance: vendor contract chunks + reference data",
    )
    return corpus.name


def upload_text_to_corpus(
    corpus_name: str,
    text: str,
    display_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> str:
    """Write text to a temp file, upload to the RAG corpus. Returns rag_file resource name."""
    _init()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        tmp_path = f.name
    try:
        rag_file = rag.upload_file(
            corpus_name=corpus_name,
            path=tmp_path,
            display_name=display_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return rag_file.name
    finally:
        os.unlink(tmp_path)


def query_corpus(corpus_name: str, query: str, top_k: int = 10) -> list[dict]:
    """Retrieve the top-k most relevant chunks from the RAG corpus."""
    _init()
    response = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
        text=query,
        similarity_top_k=top_k,
    )
    return [
        {"text": ctx.text, "source": ctx.source_uri, "score": ctx.score}
        for ctx in response.contexts.contexts
    ]
