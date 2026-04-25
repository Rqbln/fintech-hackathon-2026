"""Unit tests for remediation vendor matching — no LLM calls."""

import pytest

from app.agents.remediation import _build_alternatives, _load_alternatives, _match_vendor


def test_load_alternatives_not_empty():
    alts = _load_alternatives()
    assert len(alts) >= 3


def test_match_exact_vendor():
    alts = _load_alternatives()
    entry = _match_vendor("AWS", alts)
    assert entry is not None
    assert entry["vendor"] == "AWS"


def test_match_alias():
    alts = _load_alternatives()
    entry = _match_vendor("Amazon Web Services", alts)
    assert entry is not None
    assert entry["vendor"] == "AWS"


def test_match_fuzzy_alias():
    alts = _load_alternatives()
    entry = _match_vendor("Microsoft Azure", alts)
    assert entry is not None
    assert "Microsoft" in entry["vendor"]


def test_no_match_returns_none():
    alts = _load_alternatives()
    entry = _match_vendor("UnknownXYZVendor12345", alts)
    assert entry is None


def test_build_alternatives_has_fields():
    alts = _load_alternatives()
    entry = _match_vendor("AWS", alts)
    alternatives = _build_alternatives(entry)
    assert len(alternatives) >= 2
    for alt in alternatives:
        assert alt.name
        assert alt.hq_country
        assert isinstance(alt.eu_sovereign, bool)
