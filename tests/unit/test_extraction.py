"""Unit tests for extraction.py parsing logic — no LLM calls."""

import json
import pytest

from app.agents.extraction import _build_extraction, _parse_json_from_response, _truncate


def _sample_data():
    return {
        "vendor_name": "Cloudflare Inc.",
        "vendor_country": "US",
        "services": [
            {"service_name": "CDN", "sla_hours": 4.0},
            {"service_name": "DNS", "sla_hours": None},
        ],
        "covered_obligation_ids": ["dora-art30-2a", "dora-art30-3b"],
        "evidence_spans": [
            {"text": "The vendor shall notify within 24 hours.", "page": 3}
        ],
        "sub_vendors": ["Google Cloud", "Amazon Route 53"],
    }


def test_parse_plain_json():
    data = _sample_data()
    raw = json.dumps(data)
    result = _parse_json_from_response(raw)
    assert result["vendor_name"] == "Cloudflare Inc."


def test_parse_strips_markdown_fence():
    data = _sample_data()
    raw = f"```json\n{json.dumps(data)}\n```"
    result = _parse_json_from_response(raw)
    assert result["vendor_country"] == "US"


def test_build_extraction_services():
    extraction = _build_extraction("c-1", _sample_data())
    assert extraction.vendor_name == "Cloudflare Inc."
    assert len(extraction.services) == 2
    assert extraction.services[0].sla_hours == 4.0
    assert extraction.services[1].sla_hours is None


def test_build_extraction_evidence_spans():
    extraction = _build_extraction("c-1", _sample_data())
    assert len(extraction.evidence_spans) == 1
    assert extraction.evidence_spans[0].page == 3
    assert extraction.evidence_spans[0].document_id == "c-1"


def test_build_extraction_obligations():
    extraction = _build_extraction("c-1", _sample_data())
    assert "dora-art30-2a" in extraction.covered_obligation_ids
    assert "dora-art30-3b" in extraction.covered_obligation_ids


def test_build_extraction_sub_vendors():
    extraction = _build_extraction("c-1", _sample_data())
    assert "Google Cloud" in extraction.sub_vendors


def test_truncate_keeps_short_text():
    text = "short"
    assert _truncate(text) == "short"


def test_truncate_clips_long_text():
    text = "x" * 50_000  # beyond the 40k limit
    result = _truncate(text)
    assert len(result) < 42_000
    assert result.endswith("[... truncated ...]")
