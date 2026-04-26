"""Unit tests for gap_analysis parsing logic — no LLM calls."""

import json
from app.agents.gap_analysis import (
    _build_evidence_spans,
    _load_obligations,
    _parse_verdict_json,
    _render_context_block,
)
from app.schemas import Verdict


def test_load_obligations_returns_12():
    obs = _load_obligations()
    assert len(obs) == 12


def test_obligations_have_id_and_text():
    for ob in _load_obligations():
        assert ob.get("id")
        assert ob.get("text")
        assert ob.get("article") == "30"


def test_parse_verdict_json_plain():
    data = {
        "verdict": "partially_met",
        "rationale": "Clause 4 covers it partially.",
        "gap_description": "Missing RTO specification.",
        "risk_level": "high",
        "evidence_quotes": ["The vendor shall..."],
    }
    result = _parse_verdict_json(json.dumps(data))
    assert result["verdict"] == "partially_met"


def test_parse_verdict_json_strips_fence():
    data = {"verdict": "unmet", "rationale": "Not present.", "gap_description": "All missing.",
            "risk_level": "critical", "evidence_quotes": []}
    raw = f"```json\n{json.dumps(data)}\n```"
    result = _parse_verdict_json(raw)
    assert result["verdict"] == "unmet"


def test_verdict_enum_values():
    assert Verdict.MET.value == "met"
    assert Verdict.PARTIALLY_MET.value == "partially_met"
    assert Verdict.UNMET.value == "unmet"
    assert Verdict.UNKNOWN.value == "unknown"


def test_build_evidence_spans_maps_page_and_node_id():
    chunks = [
        {
            "text": "The vendor grants audit rights and incident reporting within 4 hours.",
            "page": 7,
            "document_id": "contract-123",
            "node_id": "node-abc",
        }
    ]
    spans = _build_evidence_spans(
        evidence_quotes=["incident reporting within 4 hours"],
        retrieved_chunks=chunks,
        contract_id="contract-123",
    )
    assert len(spans) == 1
    assert spans[0].page == 7
    assert spans[0].node_id == "node-abc"


def test_render_context_block_contains_page_and_excerpt_index():
    block = _render_context_block(
        [
            {
                "text": "Sample contract text",
                "page": 2,
                "document_id": "contract-1",
                "node_id": "node-1",
            }
        ],
        [],
    )
    assert "[Contract Excerpt 1]" in block
    assert "page=2" in block
