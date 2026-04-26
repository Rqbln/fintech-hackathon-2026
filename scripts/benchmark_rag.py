#!/usr/bin/env python
"""Lightweight RAG benchmark for DORA obligation retrieval.

What it measures (per obligation):
- contract_hit@k: at least one retrieved chunk belongs to target contract
- contract_precision@k: ratio of retrieved chunks from target contract
- dora_hit@k: at least one retrieved chunk from DORA corpus

Usage:
  uv run python scripts/benchmark_rag.py --contract-id demo-aws-001 --top-k 8
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings as LlamaSettings, VectorStoreIndex

from app.agents.gap_analysis import (
    _apply_evidence_guardrails,
    _load_obligations,
    _retrieve_contract_chunks,
    _retrieve_dora_chunks,
)
from app.config import settings
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.rag.citation_query import make_citation_engine
from app.rag.store import get_or_create_vector_store


def _is_dora_node(metadata: dict) -> bool:
    doc_id = str(metadata.get("document_id", ""))
    doc_type = str(metadata.get("doc_type", ""))
    return doc_type.upper() == "DORA" or doc_id.startswith("DORA-")


async def _run(args) -> int:
    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model

    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    engine = make_citation_engine(index=index, similarity_top_k=args.top_k, citation_chunk_size=512)

    obligations = _load_obligations()
    per_obligation: list[dict] = []

    for ob in obligations:
        q = (
            f"Contract {args.contract_id}. Find evidence for DORA Article {ob['article']} "
            f"paragraph {ob['paragraph']} obligation: {ob['text']}"
        )
        resp = engine.query(q)
        src = getattr(resp, "source_nodes", []) or []
        total = len(src)

        contract_nodes = 0
        dora_nodes = 0
        for s in src:
            meta = getattr(s, "metadata", {}) or {}
            source_contract_id = str(meta.get("contract_id", meta.get("document_id", "")))
            if source_contract_id == args.contract_id:
                contract_nodes += 1
            if _is_dora_node(meta):
                dora_nodes += 1

        strict_chunks = await _retrieve_contract_chunks(
            citation_engine=engine,
            contract_id=args.contract_id,
            obligation=ob,
        )
        dora_chunks = await _retrieve_dora_chunks(engine, ob)
        effective_contract, effective_dora = _apply_evidence_guardrails(strict_chunks, dora_chunks)

        per_obligation.append(
            {
                "id": ob["id"],
                "total": total,
                "contract_hit": int(contract_nodes > 0),
                "contract_precision": (contract_nodes / total) if total else 0.0,
                "dora_hit": int(dora_nodes > 0),
                "strict_contract_chunks": len(strict_chunks),
                "effective_contract_chunks": len(effective_contract),
                "effective_dora_chunks": len(effective_dora),
            }
        )

    contract_hit_rate = statistics.mean(row["contract_hit"] for row in per_obligation) if per_obligation else 0.0
    dora_hit_rate = statistics.mean(row["dora_hit"] for row in per_obligation) if per_obligation else 0.0
    avg_contract_precision = (
        statistics.mean(row["contract_precision"] for row in per_obligation) if per_obligation else 0.0
    )
    avg_strict_contract_chunks = (
        statistics.mean(row["strict_contract_chunks"] for row in per_obligation) if per_obligation else 0.0
    )
    effective_contract_precision = (
        statistics.mean(1.0 if row["effective_contract_chunks"] > 0 else 0.0 for row in per_obligation)
        if per_obligation
        else 0.0
    )
    contract_evidence_coverage = (
        statistics.mean(1.0 if row["effective_contract_chunks"] >= 2 else 0.0 for row in per_obligation)
        if per_obligation
        else 0.0
    )
    dora_reference_coverage = (
        statistics.mean(1.0 if row["effective_dora_chunks"] > 0 else 0.0 for row in per_obligation)
        if per_obligation
        else 0.0
    )

    print("=== RAG Benchmark (Contract vs DORA retrieval) ===")
    print(f"contract_id: {args.contract_id}")
    print(f"obligations: {len(per_obligation)}")
    print(f"top_k      : {args.top_k}")
    print()
    print(f"contract_hit@{args.top_k}   : {contract_hit_rate:.3f}")
    print(f"dora_hit@{args.top_k}       : {dora_hit_rate:.3f}")
    print(f"contract_precision@{args.top_k}: {avg_contract_precision:.3f}")
    print(f"strict_contract_chunks(avg): {avg_strict_contract_chunks:.3f}")
    print(f"effective_contract_precision: {effective_contract_precision:.3f}")
    print(f"contract_evidence_coverage : {contract_evidence_coverage:.3f}")
    print(f"dora_reference_coverage    : {dora_reference_coverage:.3f}")
    print()
    print("Per-obligation:")
    for row in per_obligation:
        print(
            f"- {row['id']}: hit={row['contract_hit']} "
            f"precision={row['contract_precision']:.2f} dora_hit={row['dora_hit']} total={row['total']} "
            f"strict_chunks={row['strict_contract_chunks']} "
            f"effective_contract={row['effective_contract_chunks']} effective_dora={row['effective_dora_chunks']}"
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark contract-vs-DORA retrieval quality.")
    parser.add_argument("--contract-id", required=True, help="Contract identifier to benchmark (e.g. demo-aws-001).")
    parser.add_argument("--top-k", type=int, default=8, help="Retrieved chunks per query.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))
