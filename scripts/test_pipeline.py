#!/usr/bin/env python
"""Integration test — runs the full AI pipeline against the demo AWS contract fixture.

Requires: running Neo4j, Cerebras API key, Gemini API key.
Usage:
    uv run python scripts/test_pipeline.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from llama_index.core import Settings as LlamaSettings

from app.config import settings
from app.llm.client import make_llm
from app.llm.embeddings import make_embed_model
from app.rag.citation_query import make_citation_engine
from app.rag.store import get_or_create_vector_store
from app.graph.schema import apply_schema
from app.agents.extraction import run_extraction
from app.agents.graph_builder import build_graph
from app.agents.risk_scorer import recompute_all
from app.agents.gap_analysis import run_gap_analysis
from app.agents.remediation import run_remediation
from app.agents.report_assembler import assemble_report
from llama_index.core import VectorStoreIndex

DEMO_CONTRACT = Path(__file__).parent.parent / "tests" / "fixtures" / "demo_aws_contract.txt"
CONTRACT_ID = "demo-aws-001"


async def main():
    print("=== DORA AI Analyst — Full Pipeline Integration Test ===\n")
    errors = []

    # ── Setup ──
    llm = make_llm(settings)
    embed_model = make_embed_model(settings)
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model

    vector_store = get_or_create_vector_store(settings)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
    citation_engine = make_citation_engine(index)

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    await apply_schema(driver)

    contract_text = DEMO_CONTRACT.read_text()
    print(f"Contract: {DEMO_CONTRACT.name} ({len(contract_text)} chars)\n")

    # ── Step 1: Extraction ──
    print("── Step 1: ExtractionAgent ──")
    try:
        extraction = await run_extraction(llm, CONTRACT_ID, contract_text)
        print(f"  Vendor: {extraction.vendor_name} ({extraction.vendor_country})")
        print(f"  Services: {[s.service_name for s in extraction.services]}")
        print(f"  Obligations covered: {extraction.covered_obligation_ids}")
        print(f"  Sub-vendors: {extraction.sub_vendors}")
        print("  ✓ Extraction ok\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"extraction: {e}")
        extraction = None

    # ── Step 2: Graph Builder ──
    print("── Step 2: GraphBuilder ──")
    try:
        vendor_id = await build_graph(driver, extraction)
        print(f"  Vendor id: {vendor_id}")
        print("  ✓ Graph built\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"graph_builder: {e}")

    # ── Step 3: Risk Scorer ──
    print("── Step 3: RiskScorer ──")
    try:
        scored = await recompute_all(driver)
        for v in scored:
            print(f"  {v['name']}: score={v['criticality_score']}")
        print("  ✓ Risk scores updated\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"risk_scorer: {e}")

    # ── Step 4: Gap Analysis (2 obligations for speed) ──
    print("── Step 4: GapAnalysisAgent (2 obligations) ──")
    try:
        findings = await run_gap_analysis(
            llm=llm,
            citation_engine=citation_engine,
            contract_id=CONTRACT_ID,
            contract_text_preview=contract_text[:3000],
            obligation_ids=["DORA-Art30-2-a", "DORA-Art30-2-b"],
        )
        for f in findings:
            print(f"  Art.{f.article}/{f.paragraph}: {f.verdict.value} ({f.risk_level})")
        assert len(findings) == 2
        print("  ✓ Gap analysis ok\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"gap_analysis: {e}")
        findings = []

    # ── Step 5: Remediation ──
    print("── Step 5: RemediationAgent ──")
    try:
        proposals = await run_remediation(llm=llm, findings=findings, vendor_name="AWS")
        print(f"  Proposals generated: {len(proposals)}")
        for p in proposals:
            print(f"  [{p.priority}] {p.summary[:60]}")
        print("  ✓ Remediation ok\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"remediation: {e}")
        proposals = []

    # ── Step 6: Report ──
    print("── Step 6: ReportAssembler ──")
    try:
        report = await assemble_report(
            llm=llm,
            session_id="demo-session-001",
            contract_ids=[CONTRACT_ID],
            findings=findings,
            proposals=proposals,
        )
        print(f"  Risk level: {report.overall_risk_level}")
        print(f"  Met={report.obligations_met} Partial={report.obligations_partial} Unmet={report.obligations_unmet}")
        print(f"  Exec summary (first 200 chars): {report.executive_summary[:200]}")
        print("  ✓ Report assembled\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        errors.append(f"report: {e}")

    await driver.close()

    status = f"All steps passed ✓" if not errors else f"{len(errors)} step(s) failed ✗"
    print(f"=== {status} ===")
    if errors:
        for err in errors:
            print(f"  - {err}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    asyncio.run(main())
