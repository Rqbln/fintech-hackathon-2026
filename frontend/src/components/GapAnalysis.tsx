import { useState, useEffect } from "react";
import type { Alert, CategoryScores } from "../api";

interface Props {
  /** Pass the live analysis result from ContractUpload → App. Optional: falls back to static demo data. */
  alerts?: Alert[];
  categoryScores?: CategoryScores;
  vendorName?: string;
  complianceScore?: number;
}

const sevColors: Record<string, { bg: string; text: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b" },
  high:     { bg: "#fff7ed", text: "#9a3412" },
  medium:   { bg: "#fefce8", text: "#854d0e" },
  low:      { bg: "#f0fdf4", text: "#166534" },
};

const CAT_LABELS: Record<string, string> = {
  rto_rpo: "RTO/RPO",
  audit_rights: "Audit Rights",
  data_residency: "Data Residency",
  subcontracting: "Subcontracting",
  incident_reporting: "Incident Reporting",
  exit_strategy: "Exit Strategy",
};

const DORA_ARTICLE: Record<string, string> = {
  rto_rpo: "Art. 30(2)(f)",
  audit_rights: "Art. 30(3)(c)",
  data_residency: "Art. 30(2)(b)",
  subcontracting: "Art. 30(2)(a)",
  incident_reporting: "Art. 30(2)(e)",
  exit_strategy: "Art. 30(3)(e)",
};

// Static demo data shown when no live data available
const DEMO_ALERTS: Alert[] = [
  { alert_id: "demo_1", severity: "critical", title: "RTO gap: bank requires 4h, contract stipulates 8h", dora_reference: "Art. 30(2)(f)", page: 5, gap_details: "Bank rule: RTO ≤ 4h for portfolio management. Contract: RTO = 8h.", remediation: "Negotiate SLA amendment to bring RTO to 4h or below.", category: "rto_rpo" },
  { alert_id: "demo_2", severity: "critical", title: "Data residency: primary processing outside EEA", dora_reference: "Art. 30(2)(b)", page: 6, gap_details: "Contract allows data processing in US East. Bank policy BR-003 requires EEA-only.", remediation: "Add data residency clause restricting processing to EEA.", category: "data_residency" },
  { alert_id: "demo_3", severity: "high", title: "Missing annual audit frequency guarantee", dora_reference: "Art. 30(3)(c)", page: 8, gap_details: "Contract limits audit to SOC 2 reports only. Bank requires minimum 1 on-site audit per year.", remediation: "Add explicit on-site audit rights clause with annual minimum.", category: "audit_rights" },
  { alert_id: "demo_4", severity: "high", title: "Subcontractor approval scope mismatch", dora_reference: "Art. 30(2)(a)", page: 10, gap_details: "Vendor can change sub-processors without prior bank approval for non-critical services.", remediation: "Require prior written approval for all sub-processor changes.", category: "subcontracting" },
];

export function GapAnalysis({ alerts, categoryScores, vendorName, complianceScore }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const isLive = (alerts ?? []).length > 0;
  const displayAlerts = isLive ? (alerts ?? []) : DEMO_ALERTS;

  const criticalCount = displayAlerts.filter((a) => a.severity === "critical").length;
  const highCount = displayAlerts.filter((a) => a.severity === "high").length;
  const scoreColor = (complianceScore ?? 0) >= 80 ? "#22c55e" : (complianceScore ?? 0) >= 50 ? "#f97316" : "#ef4444";

  return (
    <div>
      <div style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Gap Analysis</h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            {isLive
              ? `Live results for ${vendorName ?? "vendor"} — DORA Art. 30 vs. contract`
              : "Demo data — upload a contract to see live results"}
          </p>
        </div>
        {complianceScore !== undefined && (
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: scoreColor, lineHeight: 1 }}>{complianceScore}/100</div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>Global compliance score</div>
          </div>
        )}
      </div>

      {/* Summary badges */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ padding: "8px 16px", background: "#fef2f2", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#991b1b" }}>
          {criticalCount} Critical
        </div>
        <div style={{ padding: "8px 16px", background: "#fff7ed", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#9a3412" }}>
          {highCount} High
        </div>
        <div style={{ padding: "8px 16px", background: "#fefce8", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#854d0e" }}>
          {displayAlerts.filter((a) => a.severity === "medium").length} Medium
        </div>
        <div style={{ padding: "8px 16px", background: "#f0fdf4", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#166534" }}>
          {displayAlerts.filter((a) => a.severity === "low").length} Low
        </div>
      </div>

      {/* Category scores grid */}
      {categoryScores && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
          {Object.entries(categoryScores).map(([cat, score]) => {
            const s = score as number;
            const color = s >= 80 ? "#22c55e" : s >= 50 ? "#f97316" : "#ef4444";
            return (
              <div key={cat} style={{ background: "#fff", borderRadius: 10, border: "1px solid #e2e8f0", padding: "12px 14px" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>{DORA_ARTICLE[cat]}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#334155", marginBottom: 8 }}>{CAT_LABELS[cat] ?? cat}</div>
                <div style={{ height: 4, background: "#f1f5f9", borderRadius: 2, overflow: "hidden", marginBottom: 4 }}>
                  <div style={{ height: "100%", width: `${s}%`, background: color, borderRadius: 2 }} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color }}>{s}/100</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Alerts detail table */}
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #f1f5f9" }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Compliance Gaps</h3>
        </div>
        {displayAlerts.map((a, i) => {
          const sev = sevColors[a.severity] ?? sevColors.medium;
          const isOpen = expanded === a.alert_id;
          return (
            <div key={a.alert_id ?? i} style={{ borderBottom: i < displayAlerts.length - 1 ? "1px solid #f1f5f9" : "none" }}>
              <div
                onClick={() => setExpanded(isOpen ? null : (a.alert_id ?? String(i)))}
                style={{ padding: "14px 20px", display: "flex", gap: 12, alignItems: "flex-start", cursor: "pointer" }}
              >
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: sev.text, marginTop: 5, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{a.title}</span>
                    <div style={{ display: "flex", gap: 6 }}>
                      <span style={{ fontSize: 11, padding: "2px 8px", background: sev.bg, color: sev.text, borderRadius: 12, fontWeight: 700 }}>{a.severity}</span>
                      <span style={{ fontSize: 11, padding: "2px 8px", background: "#f1f5f9", borderRadius: 4, fontWeight: 600 }}>{a.dora_reference}</span>
                      {a.page > 0 && <span style={{ fontSize: 11, padding: "2px 8px", background: "#eff6ff", color: "#1d4ed8", borderRadius: 4 }}>p.{a.page}</span>}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{CAT_LABELS[a.category] ?? a.category}</div>
                </div>
                <span style={{ fontSize: 14, color: "#94a3b8", flexShrink: 0 }}>{isOpen ? "▲" : "▼"}</span>
              </div>

              {isOpen && (
                <div style={{ padding: "0 20px 16px 40px" }}>
                  {a.gap_details && (
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#94a3b8", marginBottom: 4, textTransform: "uppercase" }}>Gap detail</div>
                      <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>{a.gap_details}</div>
                    </div>
                  )}
                  {a.remediation && (
                    <div style={{ padding: "10px 14px", background: "#f0fdf4", borderRadius: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#166534", marginBottom: 4, textTransform: "uppercase" }}>Recommended action</div>
                      <div style={{ fontSize: 13, color: "#166534", lineHeight: 1.5 }}>{a.remediation}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!isLive && (
        <div style={{ marginTop: 16, padding: "12px 16px", background: "#eff6ff", borderRadius: 8, fontSize: 13, color: "#1d4ed8" }}>
          Demo data shown. Upload a vendor contract to run live DORA compliance analysis.
        </div>
      )}
    </div>
  );
}
