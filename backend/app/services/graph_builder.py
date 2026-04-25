"""
Graph builder — transforms a contract evaluation into a React Flow graph.

Output format is directly consumable by React Flow:
  { nodes: [...], edges: [...], meta: {...} }

Node types:
  - "bank"          : root node (the financial institution)
  - "vendor"        : main ICT provider (one per contract)
  - "subcontractor" : sub-processors detected in the contract

Each node carries:
  - compliance_score, risk_color, alerts, evidence (page + clause excerpt)
  - on_click payload for the Split-Screen (doc_id, page, chunk_id)
  - amendment_hints for contract correction generation
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Risk color scale (ready for React Flow node styling)
# ---------------------------------------------------------------------------

def _risk_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"   # green-500
    if score >= 50:
        return "#f97316"   # orange-500
    return "#ef4444"       # red-500


def _risk_label(score: int) -> str:
    if score >= 80:
        return "compliant"
    if score >= 50:
        return "partial"
    return "non_compliant"


# ---------------------------------------------------------------------------
# Bank root node (loaded from reference_data/bank_entity.json)
# ---------------------------------------------------------------------------

_BANK_REF = Path(__file__).parent.parent.parent.parent / "reference_data" / "bank_entity.json"

def _bank_node() -> dict:
    if _BANK_REF.exists():
        data = json.loads(_BANK_REF.read_text(encoding="utf-8"))
        entity = data.get("entity", {})
        name = entity.get("trading_name", entity.get("legal_name", "Financial Institution"))
        lei  = entity.get("lei_code", "")
        country = entity.get("country", "FR")
    else:
        name, lei, country = "Financial Institution", "", "FR"

    return {
        "id": "bank",
        "type": "bank",
        "data": {
            "label": name,
            "lei_code": lei,
            "country": country,
            "compliance_score": 100,
            "risk_color": "#3b82f6",   # blue — the bank itself
            "risk_label": "institution",
            "role": "Financial Institution (DORA Art. 30 obligee)",
        },
        "position": {"x": 0, "y": 0},
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_graph(
    doc_id: str,
    vendor_name: str,
    filename: str,
    evaluation: dict,
    subcontractors: list[dict],
) -> dict:
    """
    Build the full React Flow graph for one contract.

    Args:
        doc_id        : document identifier
        vendor_name   : ICT provider name
        filename      : original PDF filename
        evaluation    : output of EvaluatorAgent.evaluate()
        subcontractors: list of dicts from OrchestratorAgent
                        [{ name, service, data_location, page, evidence, risk_flag }]

    Returns:
        {
          "nodes": [...],   # React Flow nodes
          "edges": [...],   # React Flow edges
          "meta": { doc_id, vendor_name, compliance_score, alert_count, ... }
        }
    """
    nodes: list[dict] = []
    edges: list[dict] = []

    score  = evaluation.get("compliance_score", 0)
    alerts = evaluation.get("alerts", [])
    mappings = evaluation.get("mappings", [])
    category_scores = evaluation.get("category_scores", {})

    # --- Bank root node ---
    bank = _bank_node()
    nodes.append(bank)

    # --- Vendor node ---
    vendor_node = _vendor_node(
        doc_id=doc_id,
        vendor_name=vendor_name,
        filename=filename,
        score=score,
        alerts=alerts,
        mappings=mappings,
        category_scores=category_scores,
    )
    nodes.append(vendor_node)

    # Bank → Vendor edge
    edges.append(_edge("bank", f"vendor_{doc_id}", label="ICT service contract", critical=score < 50))

    # --- Subcontractor nodes ---
    for i, sub in enumerate(subcontractors):
        sub_id = f"sub_{doc_id}_{i}"
        sub_node = _subcontractor_node(sub_id, sub, doc_id)
        nodes.append(sub_node)
        edges.append(_edge(
            f"vendor_{doc_id}", sub_id,
            label=sub.get("service", "subcontracted service"),
            critical=sub.get("risk_flag", False),
        ))

    # --- Layout positions (simple vertical tree) ---
    _apply_layout(nodes)

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "doc_id": doc_id,
            "vendor_name": vendor_name,
            "filename": filename,
            "compliance_score": score,
            "risk_label": _risk_label(score),
            "risk_color": _risk_color(score),
            "alert_count": len(alerts),
            "subcontractor_count": len(subcontractors),
            "category_scores": category_scores,
        },
    }


# ---------------------------------------------------------------------------
# Node builders
# ---------------------------------------------------------------------------

def _vendor_node(
    doc_id: str,
    vendor_name: str,
    filename: str,
    score: int,
    alerts: list[dict],
    mappings: list[dict],
    category_scores: dict,
) -> dict:
    # Best evidence = highest-score RAG chunk with a page reference
    evidence = _best_evidence(mappings)

    # Amendment hints = categories that are non_compliant
    amendment_hints = [
        cat for cat, s in category_scores.items() if s < 50
    ]

    return {
        "id": f"vendor_{doc_id}",
        "type": "vendor",
        "data": {
            "label": vendor_name,
            "doc_id": doc_id,
            "filename": filename,
            "compliance_score": score,
            "risk_color": _risk_color(score),
            "risk_label": _risk_label(score),
            "category_scores": category_scores,
            # Alerts for the right panel of Split-Screen
            "alerts": [
                {
                    "alert_id":      a.get("alert_id"),
                    "severity":      a.get("severity"),
                    "title":         a.get("title"),
                    "dora_reference": a.get("dora_reference"),
                    "page":          a.get("page"),
                    "gap_details":   a.get("gap_details"),
                    "remediation":   a.get("remediation"),
                    "category":      a.get("category"),
                }
                for a in alerts
            ],
            # Click payload → opens Split-Screen at the right page
            "on_click": {
                "action": "open_split_screen",
                "doc_id": doc_id,
                "filename": filename,
                "page": evidence.get("page", 1),
            },
            # Textual evidence for audit trail
            "evidence": evidence,
            # Which DORA clauses need to be fixed → used by amendment generator
            "amendment_hints": amendment_hints,
        },
        "position": {"x": 0, "y": 150},
    }


def _subcontractor_node(sub_id: str, sub: dict, parent_doc_id: str) -> dict:
    risk_flag = sub.get("risk_flag", False)
    score = 30 if risk_flag else 75   # conservative default

    return {
        "id": sub_id,
        "type": "subcontractor",
        "data": {
            "label": sub.get("name", "Unknown subcontractor"),
            "service": sub.get("service", ""),
            "data_location": sub.get("data_location", ""),
            "compliance_score": score,
            "risk_color": _risk_color(score),
            "risk_label": _risk_label(score),
            "risk_flag": risk_flag,
            # Click payload → scrolls to the subcontracting clause in the PDF
            "on_click": {
                "action": "open_split_screen",
                "doc_id": parent_doc_id,
                "page": sub.get("page", 1),
            },
            "evidence": {
                "page": sub.get("page", 1),
                "excerpt": sub.get("evidence", ""),
            },
            # If flagged: no approval required or data outside EEA → amendment needed
            "amendment_hints": ["subcontracting"] if risk_flag else [],
        },
        "position": {"x": 0, "y": 300},
    }


def _edge(source: str, target: str, label: str = "", critical: bool = False) -> dict:
    return {
        "id": f"e_{source}_{target}",
        "source": source,
        "target": target,
        "label": label,
        "data": {"critical": critical},
        "style": {
            "stroke": "#ef4444" if critical else "#94a3b8",
            "strokeWidth": 2 if critical else 1,
        },
        "animated": critical,
    }


def _best_evidence(mappings: list[dict]) -> dict:
    """Return the mapping entry with the most useful evidence."""
    for m in mappings:
        if m.get("status") in ("non_compliant", "partial") and m.get("clause_id"):
            return {
                "clause_id": m.get("clause_id"),
                "dora_article": m.get("dora_article"),
                "page": 1,   # will be enriched by orchestrator
                "excerpt": m.get("evidence", "")[:300],
            }
    if mappings:
        return {"excerpt": mappings[0].get("evidence", "")[:300], "page": 1}
    return {"page": 1, "excerpt": ""}


def _apply_layout(nodes: list[dict]) -> None:
    """Simple left-to-right tree layout."""
    bank_nodes  = [n for n in nodes if n["type"] == "bank"]
    vendor_nodes = [n for n in nodes if n["type"] == "vendor"]
    sub_nodes   = [n for n in nodes if n["type"] == "subcontractor"]

    for i, n in enumerate(bank_nodes):
        n["position"] = {"x": 400, "y": 0}

    for i, n in enumerate(vendor_nodes):
        n["position"] = {"x": 400, "y": 180}

    n_subs = len(sub_nodes)
    for i, n in enumerate(sub_nodes):
        x = (i - (n_subs - 1) / 2) * 280 + 400
        n["position"] = {"x": x, "y": 380}
