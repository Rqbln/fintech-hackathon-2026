"""Unit tests for Pydantic schema shapes — no external deps needed."""

import pytest

from app.schemas import (
    ContractExtraction,
    EvidenceSpan,
    GraphEdge,
    GraphNode,
    GraphResponse,
    ObligationFinding,
    RemediationProposal,
    ServiceClause,
    Verdict,
)


def test_evidence_span_roundtrip():
    span = EvidenceSpan(text="The vendor shall…", page=3, document_id="doc-1", node_id="n-42")
    assert span.page == 3
    assert span.node_id == "n-42"


def test_contract_extraction_defaults():
    ce = ContractExtraction(contract_id="c-1", vendor_name="AWS")
    assert ce.services == []
    assert ce.covered_obligation_ids == []
    assert ce.vendor_country is None


def test_contract_extraction_with_services():
    clause = ServiceClause(service_name="DNS hosting", sla_hours=4.0)
    ce = ContractExtraction(
        contract_id="c-2",
        vendor_name="Cloudflare",
        vendor_country="US",
        services=[clause],
        sub_vendors=["Amazon Route 53"],
    )
    assert ce.services[0].service_name == "DNS hosting"
    assert ce.sub_vendors == ["Amazon Route 53"]


def test_obligation_finding_verdict_enum():
    finding = ObligationFinding(
        obligation_id="30-2a",
        article="30",
        paragraph="2a",
        description="Sub-contracting notification",
        verdict=Verdict.PARTIALLY_MET,
        rationale="Clause 4.2 covers notification but lacks timelines.",
        risk_level="high",
    )
    assert finding.verdict == Verdict.PARTIALLY_MET
    assert finding.verdict.value == "partially_met"


def test_graph_node_default_size():
    node = GraphNode(
        key="vendor:aws",
        attributes={
            "label": "AWS",
            "node_type": "Vendor",
            "criticality_score": 0.9,
        },
    )
    assert node.attributes.size == 10.0  # default
    assert node.key == "vendor:aws"


def test_graph_response_empty():
    resp = GraphResponse()
    assert resp.nodes == []
    assert resp.edges == []


def test_remediation_proposal_sovereign_alternatives():
    proposal = RemediationProposal(
        obligation_id="30-2a",
        vendor_name="AWS",
        priority="high",
        summary="Replace with EU-sovereign cloud",
        detail="Migrate workloads to OVHcloud SecNumCloud zone.",
    )
    assert proposal.sovereign_alternatives == []
    assert proposal.priority == "high"
