#!/usr/bin/env python
"""Benchmark gap-analysis latency for different concurrency values.

Usage:
  uv run python scripts/benchmark_gap_speed.py --contract-id demo-aws-001 --vendor "AWS"
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings as LlamaSettings, VectorStoreIndex

from app.agents.gap_analysis import run_gap_analysis
from app.config import settings
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.rag.citation_query import make_citation_engine
from app.rag.store import get_or_create_vector_store


async def _measure_once(contract_id: str, concurrency: int, fast_mode: bool) -> tuple[float, int]:
    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model
    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    citation_engine = make_citation_engine(index)

    t0 = time.perf_counter()
    findings = await run_gap_analysis(
        llm=llm,
        citation_engine=citation_engine,
        contract_id=contract_id,
        contract_text_preview="",
        fast_mode=fast_mode,
        concurrency=concurrency,
        batch_size=settings.gap_batch_size,
    )
    elapsed = time.perf_counter() - t0
    return elapsed, len(findings)


async def _main(args) -> int:
    runs = []
    for c in args.concurrency:
        samples = []
        findings_count = 0
        for _ in range(args.repeats):
            elapsed, findings_count = await _measure_once(args.contract_id, c, args.fast_mode)
            samples.append(elapsed)
        runs.append((c, statistics.mean(samples), min(samples), max(samples), findings_count))

    print("=== Gap Speed Benchmark ===")
    print(f"provider={settings.llm_provider} model={settings.gemini_llm_model if settings.llm_provider == 'gemini' else settings.cerebras_model}")
    print(f"contract_id={args.contract_id} fast_mode={args.fast_mode} repeats={args.repeats}")
    print()
    for c, avg_s, min_s, max_s, nfindings in runs:
        print(f"- concurrency={c}: avg={avg_s:.2f}s min={min_s:.2f}s max={max_s:.2f}s findings={nfindings}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark gap-analysis runtime by concurrency.")
    parser.add_argument("--contract-id", required=True, help="Contract identifier.")
    parser.add_argument("--concurrency", nargs="+", type=int, default=[2, 4, 6], help="Concurrency values to test.")
    parser.add_argument("--repeats", type=int, default=1, help="Runs per concurrency.")
    parser.add_argument("--fast-mode", action="store_true", help="Enable fast mode.")
    cli_args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(cli_args)))
