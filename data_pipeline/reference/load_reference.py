"""Load DORA/ISO reference framework into Vector Search."""

import json
from pathlib import Path

REFERENCE_DIR = Path(__file__).parent.parent.parent / "reference_data"


def load_reference_data() -> list[dict]:
    """Load all reference JSON files and prepare them for vectorization."""
    reference_files = [
        "dora_article_30.json",
        "iso27001_controls.json",
        "iso27005_methodology.json",
        "bank_rules_sample.json",
    ]
    documents = []
    for filename in reference_files:
        filepath = REFERENCE_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                documents.extend(data if isinstance(data, list) else [data])
    return documents
