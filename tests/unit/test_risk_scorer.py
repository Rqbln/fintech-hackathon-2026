"""Unit tests for risk_scorer logic — no Neo4j required."""

import pytest

from app.agents.risk_scorer import _country_risk, _EU_EEA_COUNTRIES


def test_eu_country_zero_risk():
    assert _country_risk("FR") == 0.0
    assert _country_risk("DE") == 0.0
    assert _country_risk("NO") == 0.0  # EEA


def test_non_eu_country_full_risk():
    assert _country_risk("US") == 1.0
    assert _country_risk("CN") == 1.0
    assert _country_risk("IN") == 1.0


def test_unknown_country_moderate_risk():
    assert _country_risk(None) == 0.5
    assert _country_risk("") == 0.5


def test_eea_countries_present():
    assert "IS" in _EU_EEA_COUNTRIES
    assert "LI" in _EU_EEA_COUNTRIES
    assert "NO" in _EU_EEA_COUNTRIES


def test_all_eu27_present():
    eu27 = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
            "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
            "NL", "PL", "PT", "RO", "SE", "SI", "SK"}
    assert eu27.issubset(_EU_EEA_COUNTRIES)
