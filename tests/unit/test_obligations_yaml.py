"""Verify the static obligations YAML loads and has the expected shape."""

import yaml
import pytest
from pathlib import Path

OBLIGATIONS_PATH = Path(__file__).parent.parent.parent / "app" / "data" / "dora_obligations.yaml"


@pytest.fixture
def obligations():
    with OBLIGATIONS_PATH.open() as f:
        return yaml.safe_load(f)["obligations"]


def test_obligations_load(obligations):
    assert len(obligations) == 12


def test_obligations_have_required_fields(obligations):
    required = {"id", "article", "paragraph", "text", "keywords", "pass_criteria"}
    for ob in obligations:
        missing = required - ob.keys()
        assert not missing, f"{ob['id']} missing fields: {missing}"


def test_obligation_ids_are_unique(obligations):
    ids = [ob["id"] for ob in obligations]
    assert len(ids) == len(set(ids))


def test_all_ids_start_with_dora_art30(obligations):
    for ob in obligations:
        assert ob["id"].startswith("DORA-Art30"), f"Unexpected id: {ob['id']}"
