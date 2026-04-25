import { useState } from "react";
import type { GraphNode, GraphEdge, GraphMeta, Alert } from "../api";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: GraphMeta;
}

// ---------------------------------------------------------------------------
// Alert detail panel
// ---------------------------------------------------------------------------

function AlertPanel({ alert, onClose }: { alert: Alert; onClose: () => void }) {
  const sevColor: Record<string, { bg: string; text: string; border: string }> = {
    critical: { bg: "#fef2f2", text: "#991b1b", border: "#fca5a5" },
    high:     { bg: "#fff7ed", text: "#9a3412", border: "#fdba74" },
    medium:   { bg: "#fefce8", text: "#854d0e", border: "#fde047" },
    low:      { bg: "#f0fdf4", text: "#166534", border: "#86efac" },
  };
  const c = sevColor[alert.severity] ?? sevColor.medium;

  return (
    <div style={{ position: "absolute", top: 16, right: 16, width: 340, background: "#fff", borderRadius: 12, border: `1px solid ${c.border}`, boxShadow: "0 8px 24px rgba(0,0,0,.12)", zIndex: 20, overflow: "hidden" }}>
      <div style={{ background: c.bg, padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 12, color: c.text, textTransform: "uppercase" }}>{alert.severity}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 16, cursor: "pointer", color: c.text }}>&#10005;</button>
      </div>
      <div style={{ padding: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>{alert.title}</div>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, padding: "2px 8px", background: "#f1f5f9", borderRadius: 4, fontWeight: 600 }}>{alert.dora_reference}</span>
          {alert.page > 0 && <span style={{ fontSize: 11, padding: "2px 8px", background: "#eff6ff", color: "#1d4ed8", borderRadius: 4 }}>page {alert.page}</span>}
          <span style={{ fontSize: 11, padding: "2px 8px", background: "#f8fafc", borderRadius: 4, color: "#64748b" }}>{alert.category}</span>
        </div>
        {alert.gap_details && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#94a3b8", marginBottom: 4, textTransform: "uppercase" }}>Gap</div>
            <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>{alert.gap_details}</div>
          </div>
        )}
        {alert.remediation && (
          <div style={{ padding: "10px 12px", background: "#f0fdf4", borderRadius: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#166534", marginBottom: 4, textTransform: "uppercase" }}>Remediation</div>
            <div style={{ fontSize: 12, color: "#166534", lineHeight: 1.5 }}>{alert.remediation}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SVG-based graph (no external library required)
// ---------------------------------------------------------------------------

const NODE_W = 220;
const NODE_H = 90;

function NodeBox({ node, selected, onClick }: { node: GraphNode; selected: boolean; onClick: () => void }) {
  const d = node.data;
  const score = d.compliance_score ?? 100;
  const color = d.risk_color ?? "#3b82f6";
  const isBank = node.type === "bank";
  const isSub = node.type === "subcontractor";

  const px = node.position.x - NODE_W / 2;
  const py = node.position.y - NODE_H / 2;

  return (
    <g
      transform={`translate(${px}, ${py})`}
      onClick={onClick}
      style={{ cursor: "pointer" }}
    >
      {/* Shadow */}
      <rect x={2} y={3} width={NODE_W} height={NODE_H} rx={10} fill="rgba(0,0,0,.08)" />
      {/* Background */}
      <rect
        width={NODE_W} height={NODE_H} rx={10}
        fill="#fff"
        stroke={selected ? "#3b82f6" : color}
        strokeWidth={selected ? 2.5 : 1.5}
      />
      {/* Color strip on left */}
      <rect width={5} height={NODE_H} rx={2} fill={color} />
      {/* Score circle */}
      {!isBank && (
        <>
          <circle cx={NODE_W - 32} cy={NODE_H / 2} r={22} fill={color} opacity={0.12} />
          <text x={NODE_W - 32} y={NODE_H / 2 + 5} textAnchor="middle" fontSize={13} fontWeight={700} fill={color}>{score}</text>
        </>
      )}

      {/* Label */}
      <text x={16} y={28} fontSize={13} fontWeight={700} fill="#1e293b">
        {d.label.length > 22 ? d.label.slice(0, 22) + "…" : d.label}
      </text>

      {isBank && (
        <text x={16} y={48} fontSize={10} fill="#64748b">{d.role ?? "Financial Institution"}</text>
      )}
      {!isBank && (
        <>
          <text x={16} y={48} fontSize={10} fill="#64748b">
            {node.type === "vendor" ? `${(d.alerts ?? []).length} alert${(d.alerts ?? []).length !== 1 ? "s" : ""}` : (d.service ?? "").slice(0, 30)}
          </text>
          {isSub && d.risk_flag && (
            <rect x={16} y={62} width={60} height={16} rx={4} fill="#fef2f2" />
          )}
          {isSub && d.risk_flag && (
            <text x={46} y={74} textAnchor="middle" fontSize={10} fontWeight={600} fill="#991b1b">RISK FLAG</text>
          )}
          {!isSub && d.risk_label && (
            <text x={16} y={74} fontSize={10} fontWeight={600} fill={color} style={{ textTransform: "uppercase" }}>{d.risk_label}</text>
          )}
        </>
      )}
    </g>
  );
}

function EdgeLine({ edge, nodes }: { edge: GraphEdge; nodes: GraphNode[] }) {
  const src = nodes.find((n) => n.id === edge.source);
  const tgt = nodes.find((n) => n.id === edge.target);
  if (!src || !tgt) return null;

  const x1 = src.position.x;
  const y1 = src.position.y + NODE_H / 2;
  const x2 = tgt.position.x;
  const y2 = tgt.position.y - NODE_H / 2;
  const mx = (x1 + x2) / 2;

  const stroke = edge.style?.stroke ?? "#94a3b8";
  const sw = edge.style?.strokeWidth ?? 1;

  return (
    <g>
      <path
        d={`M ${x1} ${y1} C ${x1} ${mx}, ${x2} ${mx}, ${x2} ${y2}`}
        stroke={stroke} strokeWidth={sw} fill="none"
        strokeDasharray={edge.animated ? "6 4" : undefined}
      />
      {edge.label && (
        <text x={(x1 + x2) / 2} y={(y1 + y2) / 2} textAnchor="middle" fontSize={10} fill="#64748b"
          style={{ background: "#fff" }}>
          {edge.label}
        </text>
      )}
    </g>
  );
}

// ---------------------------------------------------------------------------
// Category scores bar
// ---------------------------------------------------------------------------

const CAT_LABELS: Record<string, string> = {
  rto_rpo: "RTO/RPO",
  audit_rights: "Audit Rights",
  data_residency: "Data Residency",
  subcontracting: "Subcontracting",
  incident_reporting: "Incident Reporting",
  exit_strategy: "Exit Strategy",
};

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color = score >= 80 ? "#22c55e" : score >= 50 ? "#f97316" : "#ef4444";
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
        <span style={{ color: "#475569" }}>{label}</span>
        <span style={{ fontWeight: 700, color }}>{score}/100</span>
      </div>
      <div style={{ height: 6, background: "#f1f5f9", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${score}%`, background: color, borderRadius: 3, transition: "width 0.4s" }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main VendorGraph component
// ---------------------------------------------------------------------------

export function VendorGraph({ nodes, edges, meta }: Props) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const vendorNode = nodes.find((n) => n.type === "vendor");

  // SVG canvas size
  const allX = nodes.map((n) => n.position.x);
  const allY = nodes.map((n) => n.position.y);
  const minX = Math.min(...allX) - NODE_W;
  const minY = Math.min(...allY) - NODE_H;
  const maxX = Math.max(...allX) + NODE_W;
  const maxY = Math.max(...allY) + NODE_H;
  const svgW = maxX - minX;
  const svgH = Math.max(maxY - minY, 300);

  const scoreColor = meta.compliance_score >= 80 ? "#22c55e" : meta.compliance_score >= 50 ? "#f97316" : "#ef4444";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20 }}>
      {/* Graph canvas */}
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden", position: "relative" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: 15 }}>{meta.vendor_name}</span>
            <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: 8 }}>{meta.filename}</span>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#64748b" }}>{meta.alert_count} alerts</span>
            <span style={{ fontWeight: 800, fontSize: 20, color: scoreColor }}>{meta.compliance_score}</span>
            <span style={{ fontSize: 12, color: "#94a3b8" }}>/100</span>
          </div>
        </div>

        <div style={{ overflowX: "auto", padding: 16 }}>
          <svg width={svgW} height={svgH} viewBox={`${minX} ${minY} ${svgW} ${svgH}`}>
            {/* Edges first (behind nodes) */}
            {edges.map((e) => <EdgeLine key={e.id} edge={e} nodes={nodes} />)}
            {/* Nodes */}
            {nodes.map((n) => (
              <NodeBox
                key={n.id}
                node={n}
                selected={selectedNode?.id === n.id}
                onClick={() => setSelectedNode(selectedNode?.id === n.id ? null : n)}
              />
            ))}
          </svg>
        </div>

        {/* Alert detail overlay */}
        {selectedAlert && (
          <AlertPanel alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
        )}
      </div>

      {/* Right sidebar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Global score */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 16 }}>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4, fontWeight: 600, textTransform: "uppercase" }}>Global Score</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: scoreColor, lineHeight: 1 }}>{meta.compliance_score}</div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>/ 100 &nbsp; {meta.risk_label.replace("_", " ").toUpperCase()}</div>
        </div>

        {/* Category scores */}
        {meta.category_scores && (
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>DORA Categories</div>
            {Object.entries(meta.category_scores).map(([k, v]) => (
              <ScoreBar key={k} label={CAT_LABELS[k] ?? k} score={v as number} />
            ))}
          </div>
        )}

        {/* Node detail when selected */}
        {selectedNode && selectedNode.type === "vendor" && (
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #f1f5f9", fontSize: 13, fontWeight: 600 }}>
              Alerts — {selectedNode.data.label}
            </div>
            {(selectedNode.data.alerts ?? []).length === 0 ? (
              <div style={{ padding: 16, fontSize: 13, color: "#94a3b8" }}>No alerts</div>
            ) : (
              (selectedNode.data.alerts ?? []).map((a, i) => {
                const dot: Record<string, string> = { critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#22c55e" };
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedAlert(a)}
                    style={{ padding: "10px 16px", borderBottom: "1px solid #f8fafc", cursor: "pointer", display: "flex", gap: 8, alignItems: "flex-start" }}
                  >
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: dot[a.severity] ?? "#94a3b8", marginTop: 4, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{a.title}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8" }}>{a.dora_reference}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {selectedNode && selectedNode.type === "subcontractor" && (
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{selectedNode.data.label}</div>
            <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.8 }}>
              <div><span style={{ color: "#94a3b8" }}>Service:</span> {selectedNode.data.service}</div>
              <div><span style={{ color: "#94a3b8" }}>Data location:</span> {selectedNode.data.data_location}</div>
              {selectedNode.data.risk_flag && (
                <div style={{ marginTop: 8, padding: "6px 10px", background: "#fef2f2", borderRadius: 6, fontSize: 11, color: "#991b1b", fontWeight: 600 }}>
                  Risk flag: requires amendment
                </div>
              )}
            </div>
          </div>
        )}

        {/* Amendment hints */}
        {vendorNode && (vendorNode.data.amendment_hints ?? []).length > 0 && (
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #fca5a5", padding: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#991b1b", marginBottom: 8, textTransform: "uppercase" }}>Amendment Required</div>
            {(vendorNode.data.amendment_hints ?? []).map((hint: string) => (
              <div key={hint} style={{ fontSize: 12, color: "#475569", padding: "4px 0", display: "flex", gap: 6, alignItems: "center" }}>
                <span style={{ color: "#ef4444" }}>&#9888;</span>
                <span>{CAT_LABELS[hint] ?? hint}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
