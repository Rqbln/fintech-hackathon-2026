"""Verify the sovereign alternatives YAML loads and has the expected shape."""

import yaml
import pytest
from pathlib import Path

ALTERNATIVES_PATH = (
    Path(__file__).parent.parent.parent / "app" / "data" / "sovereign_alternatives.yaml"
)


@pytest.fixture
def alternatives():
    with ALTERNATIVES_PATH.open() as f:
        return yaml.safe_load(f)["alternatives"]


def test_alternatives_load(alternatives):
    assert len(alternatives) > 0


def test_alternatives_have_required_fields(alternatives):
    required = {"vendor", "vendor_aliases", "jurisdiction", "proposals"}
    for alt in alternatives:
        missing = required - alt.keys()
        assert not missing, f"{alt['vendor']} missing fields: {missing}"


def test_every_proposal_has_name_and_country(alternatives):
    for alt in alternatives:
        for proposal in alt["proposals"]:
            assert "name" in proposal, f"proposal in {alt['vendor']} missing 'name'"
            assert "hq_country" in proposal, f"proposal in {alt['vendor']} missing 'hq_country'"


def test_aws_has_eu_sovereign_alternatives(alternatives):
    aws = next(a for a in alternatives if a["vendor"] == "AWS")
    eu_proposals = [p for p in aws["proposals"] if p.get("eu_sovereign")]
    assert len(eu_proposals) >= 1
