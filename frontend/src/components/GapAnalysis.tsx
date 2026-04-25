const gaps = [
  { vendor: "BlackRock Aladdin", article: "Art. 30(2)(f)", requirement: "RTO aligned with bank critical function needs", bank_rule: "RTO ≤ 4h for FN-001 (Portfolio Mgmt)", contract: "RTO = 8h (Aladdin platform recovery)", severity: "critical", status: "non_compliant" },
  { vendor: "BlackRock Aladdin", article: "Art. 30(2)(b)", requirement: "Data storage and processing location", bank_rule: "Primary data processing in EEA (BR-003)", contract: "Primary: US East, DR: UK South", severity: "critical", status: "non_compliant" },
  { vendor: "Bloomberg", article: "Art. 30(2)(b)", requirement: "Data storage and processing location", bank_rule: "Primary data processing in EEA (BR-003)", contract: "Primary: US, Backup: UK", severity: "critical", status: "non_compliant" },
  { vendor: "Bloomberg", article: "Art. 30(3)(c)", requirement: "Unrestricted audit and access rights", bank_rule: "On-site audit rights for critical vendors (BR-007)", contract: "Limited to SOC 2 Type II reports and annual questionnaire", severity: "high", status: "partial" },
  { vendor: "AWS", article: "Art. 30(2)(a)", requirement: "Complete subcontractor chain disclosure", bank_rule: "Full sub-processor registry (BR-005)", contract: "3 sub-processors not disclosed in Annex C", severity: "high", status: "partial" },
  { vendor: "CyberArk", article: "Art. 30(3)(e)", requirement: "Exit strategy and data portability", bank_rule: "Exit plan with 90-day transition (BR-008)", contract: "No data portability clause found", severity: "high", status: "non_compliant" },
  { vendor: "CyberArk", article: "Art. 30(2)(d)", requirement: "Guaranteed service levels", bank_rule: "99.95% uptime for security services (BR-002)", contract: "99.9% uptime SLA (0.05% gap)", severity: "medium", status: "partial" },
  { vendor: "SWIFT", article: "Art. 30(3)(c)", requirement: "Unrestricted audit and access rights", bank_rule: "On-site audit rights for critical vendors (BR-007)", contract: "ISAE 3402 Type II only, no on-site", severity: "medium", status: "partial" },
  { vendor: "AWS", article: "Art. 30(2)(g)", requirement: "Adequate notice period for contract changes", bank_rule: "180-day notice for material changes (BR-009)", contract: "90-day notice (90-day gap)", severity: "medium", status: "partial" },
  { vendor: "SWIFT", article: "Art. 30(2)(f)", requirement: "RTO/RPO targets", bank_rule: "RTO ≤ 4h for FN-001", contract: "RTO = 2h, RPO = 0 (compliant)", severity: "low", status: "compliant" },
];

const sevColors: Record<string, { bg: string; text: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b" },
  high: { bg: "#fff7ed", text: "#9a3412" },
  medium: { bg: "#fefce8", text: "#854d0e" },
  low: { bg: "#f0fdf4", text: "#166534" },
};

const statusColors: Record<string, { bg: string; text: string; label: string }> = {
  non_compliant: { bg: "#fef2f2", text: "#991b1b", label: "Non-Compliant" },
  partial: { bg: "#fff7ed", text: "#9a3412", label: "Partial" },
  compliant: { bg: "#f0fdf4", text: "#166534", label: "Compliant" },
};

export function GapAnalysis() {
  const criticalCount = gaps.filter((g) => g.severity === "critical").length;
  const highCount = gaps.filter((g) => g.severity === "high").length;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Gap Analysis</h2>
        <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
          Comparison: DORA Article 30 requirements vs. vendor contractual guarantees vs. bank internal rules
        </p>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <div style={{ padding: "8px 16px", background: "#fef2f2", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#991b1b" }}>
          {criticalCount} Critical Gaps
        </div>
        <div style={{ padding: "8px 16px", background: "#fff7ed", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#9a3412" }}>
          {highCount} High Gaps
        </div>
        <div style={{ padding: "8px 16px", background: "#f0fdf4", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#166534" }}>
          {gaps.filter((g) => g.status === "compliant").length} Compliant
        </div>
      </div>

      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f8fafc" }}>
              {["Vendor", "DORA Article", "Bank Requirement", "Contract Guarantee", "Severity", "Status"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "10px 16px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const, borderBottom: "1px solid #e2e8f0" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {gaps.map((g, i) => {
              const sev = sevColors[g.severity];
              const st = statusColors[g.status];
              return (
                <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "12px 16px", fontWeight: 500 }}>{g.vendor}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ padding: "2px 8px", background: "#f1f5f9", borderRadius: 4, fontWeight: 600, fontSize: 11 }}>{g.article}</span>
                  </td>
                  <td style={{ padding: "12px 16px", color: "#475569", maxWidth: 200 }}>{g.bank_rule}</td>
                  <td style={{ padding: "12px 16px", color: "#475569", maxWidth: 200 }}>{g.contract}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ padding: "3px 10px", borderRadius: 20, background: sev.bg, color: sev.text, fontWeight: 600, fontSize: 11 }}>{g.severity}</span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ padding: "3px 10px", borderRadius: 20, background: st.bg, color: st.text, fontWeight: 600, fontSize: 11 }}>{st.label}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
