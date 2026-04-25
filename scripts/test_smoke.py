#!/usr/bin/env python
"""Smoke test — verifies LLM, embeddings, and RAG are all working.

Usage:
    uv run python scripts/test_smoke.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings as LlamaSettings, VectorStoreIndex
from llama_index.core.llms import ChatMessage

from app.config import settings
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.rag.citation_query import make_citation_engine
from app.rag.store import get_or_create_vector_store


def test_llm():
    print(f"\n── LLM (Cerebras {settings.cerebras_model}) ──")
    llm = make_llm(settings)
    LlamaSettings.llm = llm  # set globally so RAG also uses it
    # Use chat() — Cerebras only exposes /v1/chat/completions, not /v1/completions
    resp = llm.chat([ChatMessage(role="user", content="Reply with exactly: OK")])
    text = resp.message.content.strip()
    print(f"  Response: {text}")
    assert text, "LLM returned empty response"
    print("  ✓ LLM ok")


def test_embed():
    print("\n── Embeddings (Gemini Embedding 2, 768-dim) ──")
    embed = make_embed_model(settings)
    vec = embed.get_text_embedding("DORA third-party ICT risk")
    print(f"  Vector dim: {len(vec)}")
    assert len(vec) == settings.gemini_embed_dim, f"Expected {settings.gemini_embed_dim}, got {len(vec)}"
    print("  ✓ Embeddings ok")


def test_rag():
    print("\n── RAG — Citation query against DORA ──")
    embed = make_embed_model(settings)
    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed)
    engine = make_citation_engine(index)

    resp = engine.query("What does DORA Article 30 require in vendor contracts?")
    print(f"  Answer (first 300 chars): {str(resp)[:300]}")
    print(f"  Source nodes: {len(resp.source_nodes)}")
    assert len(resp.source_nodes) > 0, "No sources returned — RAG retrieval failed"
    for i, node in enumerate(resp.source_nodes[:2], 1):
        meta = node.metadata
        print(f"    [{i}] doc={meta.get('document_id','?')} page={meta.get('page','?')}")
    print("  ✓ RAG ok")


if __name__ == "__main__":
    print("=== DORA Analyst Smoke Test ===")
    errors = []
    for fn in [test_llm, test_embed, test_rag]:
        try:
            fn()
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            errors.append(str(e))

    print(f"\n{'All tests passed ✓' if not errors else f'{len(errors)} test(s) failed ✗'}")
    sys.exit(1 if errors else 0)
