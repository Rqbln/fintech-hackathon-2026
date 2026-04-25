"""
One-time bootstrap: load DORA/ISO/bank reference data into the RAG corpus.
Run from repo root: python3 data_pipeline/reference/load_reference.py
"""
import json
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.rag_engine import get_or_create_corpus, upload_text_to_corpus

REFERENCE_DIR = Path(__file__).parent.parent.parent / "reference_data"


def _to_text_dora(item: dict) -> str:
    # Fields: id, article, title, requirement, category, criticality
    parts = [f"DORA {item.get('article', item.get('id', ''))} — {item.get('title', '')}"]
    if req := item.get("requirement"):
        parts.append(f"Requirement: {req}")
    if cat := item.get("category"):
        parts.append(f"Category: {cat}")
    if crit := item.get("criticality"):
        parts.append(f"Criticality: {crit}")
    return "\n".join(parts)


def _to_text_iso(item: dict) -> str:
    # Fields: id, title, description, dora_mapping, check_points
    parts = [f"ISO 27001 Control {item.get('id', '')} — {item.get('title', '')}"]
    if desc := item.get("description"):
        parts.append(f"Description: {desc}")
    if dora := item.get("dora_mapping"):
        mapping = dora if isinstance(dora, str) else ", ".join(dora)
        parts.append(f"DORA mapping: {mapping}")
    if pts := item.get("check_points"):
        pts_text = pts if isinstance(pts, str) else "; ".join(pts)
        parts.append(f"Check points: {pts_text}")
    return "\n".join(parts)


def _to_text_bank_rule(item: dict) -> str:
    # Fields: rule_id, category, function, criticality, requirement, rto_hours, rpo_hours
    parts = [f"Bank Internal Rule {item.get('rule_id', '')} — {item.get('function', item.get('category', ''))}"]
    if req := item.get("requirement"):
        parts.append(f"Requirement: {req}")
    if cat := item.get("category"):
        parts.append(f"Category: {cat}")
    if crit := item.get("criticality"):
        parts.append(f"Criticality: {crit}")
    if rto := item.get("rto_hours"):
        parts.append(f"RTO Hours: {rto}")
    if rpo := item.get("rpo_hours"):
        parts.append(f"RPO Hours: {rpo}")
    return "\n".join(parts)


_FILES: dict[str, tuple[str, Callable[[dict], str]]] = {
    "dora_article_30.json": ("dora_article_30", _to_text_dora),
    "iso27001_controls.json": ("iso27001_controls", _to_text_iso),
    "bank_rules_sample.json": ("bank_rules", _to_text_bank_rule),
}


def load_all() -> None:
    corpus_name = get_or_create_corpus()
    print(f"Corpus: {corpus_name}")
    for filename, (display_name, formatter) in _FILES.items():
        filepath = REFERENCE_DIR / filename
        if not filepath.exists():
            print(f"SKIP {filename} (not found)")
            continue
        raw = json.loads(filepath.read_text())
        items = raw if isinstance(raw, list) else [raw]
        text = "\n---\n".join(formatter(item) for item in items)
        rag_name = upload_text_to_corpus(
            corpus_name=corpus_name,
            text=text,
            display_name=display_name,
            chunk_size=600,
            chunk_overlap=80,
        )
        print(f"  {filename} → {rag_name}")


if __name__ == "__main__":
    load_all()
