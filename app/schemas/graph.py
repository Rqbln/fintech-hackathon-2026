"""Sigma.js-compatible graph shapes.

Sigma expects:
  nodes: [{ key, attributes: { label, size, color, x?, y?, ... } }]
  edges: [{ key, source, target, attributes: { label, size, ... } }]
"""

from pydantic import BaseModel, Field


class NodeAttributes(BaseModel):
    label: str
    size: float = 10.0          # driven by criticality_score
    color: str = "#6366f1"      # hex
    node_type: str              # Vendor | Service | BusinessFunction | Contract | DORAObligation
    criticality_score: float = 0.0
    country: str | None = None
    is_critical_provider: bool = False
    x: float | None = None      # layout coords (optional; Sigma auto-lays out if absent)
    y: float | None = None


class GraphNode(BaseModel):
    key: str                    # e.g. "vendor:aws"
    attributes: NodeAttributes


class EdgeAttributes(BaseModel):
    label: str
    size: float = 2.0
    color: str = "#94a3b8"


class GraphEdge(BaseModel):
    key: str                    # e.g. "edge:vendor:aws->service:ec2"
    source: str
    target: str
    attributes: EdgeAttributes


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
