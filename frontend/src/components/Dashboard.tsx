const kpis = [
  { label: "ICT Vendors", value: "5", sub: "3 critical", color: "#3b82f6" },
  { label: "Compliance Rate", value: "68%", sub: "DORA Art. 30", color: "#f59e0b" },
  { label: "Critical Alerts", value: "4", sub: "2 unvalidated", color: "#ef4444" },
  { label: "AUM", value: "€18.7B", sub: "245 employees", color: "#8b5cf6" },
  { label: "Risk Score", value: "14.2", sub: "/ 25 (High)", color: "#ef4444" },
  { label: "RoI Coverage", value: "83%", sub: "12/15 models", color: "#22c55e" },
];

const alerts = [
  { severity: "critical", vendor: "BlackRock Aladdin", message: "RTO gap: bank requires 4h, contract stipulates 8h for platform recovery", article: "Art. 30(2)(f)", time: "2 min ago" },
  { severity: "critical", vendor: "Bloomberg", message: "Data residency: primary processing in US, violates bank rule BR-003 (EEA-only)", article: "Art. 30(2)(b)", time: "5 min ago" },
  { severity: "high", vendor: "AWS", message: "Subcontractor disclosure incomplete: 3 sub-processors not listed in contract annex", article: "Art. 30(2)(a)", time: "12 min ago" },
  { severity: "high", vendor: "CyberArk", message: "Exit strategy: no data portability clause found in contract CTR-CYB-2023-001", article: "Art. 30(3)(e)", time: "18 min ago" },
  { severity: "medium", vendor: "SWIFT", message: "Audit rights: limited to ISAE 3402 reports, no on-site audit provision", article: "Art. 30(3)(c)", time: "25 min ago" },
  { severity: "low", vendor: "AWS", message: "Contract renewal due in 60 days (CTR-AWS-2023-001 expires 2026-02-28)", article: "Art. 30(2)(g)", time: "1h ago" },
];

const sevColors: Record<string, { bg: string; text: string; dot: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b", dot: "#ef4444" },
  high: { bg: "#fff7ed", text: "#9a3412", dot: "#f97316" },
  medium: { bg: "#fefce8", text: "#854d0e", dot: "#eab308" },
  low: { bg: "#f0fdf4", text: "#166534", dot: "#22c55e" },
};

const vendors = [
  { name: "BlackRock Aladdin", cost: "€3.2M", functions: 3, score: 18, status: "critical" },
  { name: "Bloomberg", cost: "€2.4M", functions: 3, score: 15, status: "high" },
  { name: "AWS", cost: "€1.85M", functions: 4, score: 12, status: "high" },
  { name: "SWIFT", cost: "€420K", functions: 2, score: 6, status: "medium" },
  { name: "CyberArk", cost: "€380K", functions: 2, score: 9, status: "medium" },
];

export function Dashboard() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>CRO Dashboard</h2>
        <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>Eurobank Investment Solutions S.A. &middot; DORA Third-Party Risk Overview</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
        {kpis.map((k) => (
          <div key={k.label} style={{ background: "#fff", borderRadius: 12, padding: "20px 20px 16px", border: "1px solid #e2e8f0", boxShadow: "0 1px 2px rgba(0,0,0,.04)" }}>
            <div style={{ fontSize: 12, color: "#64748b", fontWeight: 500, marginBottom: 8 }}>{k.label}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Recent Alerts</h3>
            <span style={{ fontSize: 12, color: "#ef4444", fontWeight: 600 }}>{alerts.filter((a) => a.severity === "critical").length} critical</span>
          </div>
          <div>
            {alerts.map((a, i) => {
              const c = sevColors[a.severity];
              return (
                <div key={i} style={{ padding: "12px 20px", borderBottom: i < alerts.length - 1 ? "1px solid #f8fafc" : "none", display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: c.dot, marginTop: 6, flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{a.vendor}</span>
                      <span style={{ fontSize: 11, color: "#94a3b8" }}>{a.time}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.4 }}>{a.message}</div>
                    <span style={{ display: "inline-block", marginTop: 4, fontSize: 10, padding: "2px 6px", borderRadius: 4, background: c.bg, color: c.text, fontWeight: 600 }}>{a.article}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9" }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Vendor Risk Ranking</h3>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f8fafc" }}>
                <th style={{ textAlign: "left", padding: "10px 20px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const }}>Vendor</th>
                <th style={{ textAlign: "right", padding: "10px 12px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const }}>Cost/yr</th>
                <th style={{ textAlign: "center", padding: "10px 12px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const }}>Functions</th>
                <th style={{ textAlign: "center", padding: "10px 20px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const }}>Risk</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((v) => {
                const c = sevColors[v.status];
                return (
                  <tr key={v.name} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "12px 20px", fontWeight: 500 }}>{v.name}</td>
                    <td style={{ padding: "12px", textAlign: "right", color: "#64748b" }}>{v.cost}</td>
                    <td style={{ padding: "12px", textAlign: "center" }}>{v.functions}</td>
                    <td style={{ padding: "12px 20px", textAlign: "center" }}>
                      <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 20, background: c.bg, color: c.text, fontWeight: 700, fontSize: 12 }}>{v.score}/25</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div style={{ padding: "16px 20px", borderTop: "1px solid #f1f5f9" }}>
            <h4 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#475569" }}>Concentration Risks</h4>
            <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#ef4444" }} />
                <span><b>US data processing</b>: Bloomberg + Aladdin process data outside EEA</span>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f97316" }} />
                <span><b>AWS cascade</b>: CyberArk hosted on AWS &mdash; single cloud failure hits 2 vendors</span>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f97316" }} />
                <span><b>Aladdin SPOF</b>: supports 3 critical functions with no alternative platform</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
