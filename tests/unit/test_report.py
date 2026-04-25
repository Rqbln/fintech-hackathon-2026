"""Unit tests for report assembly helpers."""

import pytest

from app.api.report import _to_markdown, store_report, _reports
from app.schemas import ObligationFinding, ReportArtifact, Verdict


def _make_report(session_id="s-1") -> ReportArtifact:
    findings = [
        ObligationFinding(
            obligation_id="dora-art30-2a",
            article="30",
            paragraph="2a",
            description="Description of services",
            verdict=Verdict.MET,
            rationale="Clause 2 covers it fully.",
        ),
        ObligationFinding(
            obligation_id="dora-art30-2b",
            article="30",
            paragraph="2b",
            description="Data location",
            verdict=Verdict.UNMET,
            rationale="No mention of data residency.",
            gap_description="Missing data location clause.",
            risk_level="high",
        ),
    ]
    return ReportArtifact(
        session_id=session_id,
        contract_ids=["c-1"],
        executive_summary="Two obligations assessed.",
        findings=findings,
        obligations_met=1,
        obligations_partial=0,
        obligations_unmet=1,
        overall_risk_level="high",
    )


def test_to_markdown_contains_session():
    md = _to_markdown(_make_report("sess-abc"))
    assert "sess-abc" in md


def test_to_markdown_contains_findings():
    md = _to_markdown(_make_report())
    assert "Art.30" in md
    assert "Clause 2 covers it fully" in md


def test_to_markdown_gap_present():
    md = _to_markdown(_make_report())
    assert "Missing data location" in md


def test_store_and_retrieve():
    report = _make_report("sess-store-test")
    store_report(report)
    assert _reports["sess-store-test"] is report


def test_overall_risk_critical():
    report = _make_report()
    report.obligations_unmet = 3
    report.overall_risk_level = "critical"
    md = _to_markdown(report)
    assert "CRITICAL" in md
