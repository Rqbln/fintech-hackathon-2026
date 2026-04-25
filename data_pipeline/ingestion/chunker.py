"""CLI wrapper — delegates to backend/app/utils/chunker.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.utils.chunker import chunk_by_clause, _classify  # noqa: F401

if __name__ == "__main__":
    import json

    sample = [{"page": 1, "text": "Article 1. Test clause about RTO of 4 hours."}]
    print(json.dumps(chunk_by_clause(sample), ensure_ascii=False, indent=2))
