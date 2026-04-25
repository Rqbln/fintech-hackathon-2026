"""Unit tests for entity resolution (no Neo4j required)."""

import pytest

from app.graph.resolver import resolve_vendor_id


def test_exact_match():
    known = {"amazon web services": "vendor:aws"}
    result = resolve_vendor_id("Amazon Web Services", known)
    assert result == "vendor:aws"


def test_fuzzy_match():
    known = {"amazon web services": "vendor:aws"}
    # "AWS" won't fuzzy-match "amazon web services" (too different), new id expected
    result = resolve_vendor_id("Amazon Web  Services", known)  # extra space
    assert result == "vendor:aws"


def test_no_match_generates_slug():
    known = {"amazon web services": "vendor:aws"}
    result = resolve_vendor_id("OVHcloud", known)
    assert result == "vendor:ovhcloud"


def test_empty_known():
    result = resolve_vendor_id("Microsoft Azure", {})
    assert result == "vendor:microsoft_azure"


def test_dot_in_name():
    result = resolve_vendor_id("Google.com", {})
    assert result == "vendor:google_com"
