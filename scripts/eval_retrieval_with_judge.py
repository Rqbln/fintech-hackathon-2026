#!/usr/bin/env python
"""Evaluate retrieval quality with an LLM judge.

Flow:
1) Retrieve top-k chunks for a question (vector similarity).
2) Optionally filter chunks by contract_id.
3) Ask LLM judge if each chunk is relevant to the question.
4) Print precision-like metrics and chunk-level verdicts.

Usage:
  uv run python scripts/eval_retrieval_with_judge.py \
    --question "What are the audit rights obligations?" \
    --top-k 8 \
    --contract-id demo-aws-001
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings as LlamaSettings, VectorStoreIndex
from llama_index.core.llms import ChatMessage

from app.config import settings
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.llm.retry import chat_with_retry
from app.rag.store import get_or_create_vector_store

JUDGE_SYSTEM = """You are a strict retrieval evaluator.
Given a QUESTION and one CHUNK, decide whether the CHUNK is relevant enough to support answering the QUESTION.
Return ONLY JSON:
{
  "relevant": true/false,
  "score": 0.0-1.0,
  "reason": "short reason"
}
Rules:
- true only if chunk directly contains facts or clauses helpful for the question.
- false if only generic, tangential, or unrelated context.
"""

CRITICAL_QUESTIONS = [
    "Quel est le Délai de Rétablissement (RTO) garanti par ce contrat et respecte-t-il un maximum de 4 heures ?",
    "Le contrat autorise-t-il explicitement des droits d'audit pour l'entité financière ?",
    "Le contrat impose-t-il une notification préalable en cas de changement de sous-traitant critique ?",
]


def _parse_json(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


def _extract_node_text(node) -> str:
    text = ""
    try:
        text = node.get_content(metadata_mode="none") or ""
    except Exception:
        text = ""
    text = text.strip()
    if text:
        return text

    # Vertex/LlamaIndex v2 sometimes stores payload in metadata["_node_content"] JSON.
    meta = getattr(node, "metadata", {}) or {}
    raw = meta.get("_node_content")
    if isinstance(raw, str) and raw.strip():
        try:
            payload = json.loads(raw)
            t = (payload.get("text") or "").strip()
            if t:
                return t
        except Exception:
            pass
    return ""


async def _judge_chunk(llm, question: str, chunk_text: str) -> dict[str, Any]:
    user = f"QUESTION:\n{question}\n\nCHUNK:\n{chunk_text[:1500]}"
    resp = await chat_with_retry(
        llm,
        [
            ChatMessage(role="system", content=JUDGE_SYSTEM),
            ChatMessage(role="user", content=user),
        ],
    )
    raw = (resp.message.content or "").strip()
    try:
        parsed = _parse_json(raw)
    except Exception:
        parsed = {"relevant": False, "score": 0.0, "reason": "judge_json_parse_failed"}
    parsed["relevant"] = bool(parsed.get("relevant", False))
    parsed["score"] = float(parsed.get("score", 0.0) or 0.0)
    parsed["reason"] = str(parsed.get("reason", ""))[:180]
    return parsed


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate vector retrieval with LLM chunk judge.")
    parser.add_argument("--question", default="", help="Question to evaluate.")
    parser.add_argument("--top-k", type=int, default=8, help="Number of retrieved chunks.")
    parser.add_argument("--contract-id", default="", help="Optional target contract_id filter for analysis.")
    parser.add_argument(
        "--batch-critical",
        action="store_true",
        help="Run a predefined batch of critical compliance questions.",
    )
    args = parser.parse_args()
    if not args.batch_critical and not args.question:
        raise SystemExit("Provide --question or use --batch-critical")

    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model

    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    retriever = index.as_retriever(similarity_top_k=args.top_k)
    questions = CRITICAL_QUESTIONS if args.batch_critical else [args.question]
    overall_scores: list[float] = []
    overall_relevance: list[float] = []

    for question in questions:
        nodes = retriever.retrieve(question)
        rows: list[dict[str, Any]] = []
        for n in nodes:
            node = n.node
            meta = node.metadata or {}
            text = _extract_node_text(node)
            contract_id = str(meta.get("contract_id", meta.get("document_id", "")))
            is_target_contract = bool(args.contract_id and contract_id == args.contract_id)
            judge = await _judge_chunk(llm, question, text)
            rows.append(
                {
                    "score": float(getattr(n, "score", 0.0) or 0.0),
                    "doc_type": str(meta.get("doc_type", "")),
                    "document_id": str(meta.get("document_id", "")),
                    "contract_id": contract_id,
                    "page": int(meta.get("page", 0) or 0),
                    "is_target_contract": is_target_contract,
                    "judge_relevant": judge["relevant"],
                    "judge_score": judge["score"],
                    "judge_reason": judge["reason"],
                }
            )

        total = len(rows)
        relevant = sum(1 for r in rows if r["judge_relevant"])
        precision_like = (relevant / total) if total else 0.0
        avg_judge = (sum(r["judge_score"] for r in rows) / total) if total else 0.0
        target_contract_ratio = (
            sum(1 for r in rows if r["is_target_contract"]) / total if (total and args.contract_id) else 0.0
        )
        overall_scores.append(avg_judge)
        overall_relevance.append(precision_like)

        print("=== Retrieval + LLM Judge ===")
        print(f"question             : {question}")
        print(f"top_k                : {args.top_k}")
        if args.contract_id:
            print(f"target_contract_id   : {args.contract_id}")
        print()
        print(f"judge_relevant_ratio : {precision_like:.3f}")
        print(f"judge_avg_score      : {avg_judge:.3f}")
        if args.contract_id:
            print(f"target_contract_ratio: {target_contract_ratio:.3f}")
        print()
        print("Chunks:")
        for i, r in enumerate(rows, 1):
            print(
                f"{i:02d}. sim={r['score']:.3f} judge={r['judge_score']:.2f} rel={int(r['judge_relevant'])} "
                f"doc_type={r['doc_type']} contract={r['contract_id']} page={r['page']} reason={r['judge_reason']}"
            )
        print()

    if len(questions) > 1:
        print("=== Batch summary ===")
        print(f"questions_count      : {len(questions)}")
        print(f"avg_judge_relevance  : {sum(overall_relevance)/len(overall_relevance):.3f}")
        print(f"avg_judge_score      : {sum(overall_scores)/len(overall_scores):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
