const vendors = [
  { id: "VND-001", name: "AWS", type: "Cloud IaaS", country: "LU", cost: 1850000, functions: ["FN-002", "FN-003", "FN-005", "FN-006"], riskScore: 12, substituability: "LOW", certifications: 6 },
  { id: "VND-002", name: "Bloomberg", type: "Market Data", country: "US", cost: 2400000, functions: ["FN-001", "FN-002", "FN-005"], riskScore: 15, substituability: "VERY LOW", certifications: 2 },
  { id: "VND-003", name: "SWIFT", type: "Messaging", country: "BE", cost: 420000, functions: ["FN-001", "FN-004"], riskScore: 6, substituability: "VERY LOW", certifications: 3 },
  { id: "VND-004", name: "BlackRock Aladdin", type: "Platform", country: "US", cost: 3200000, functions: ["FN-001", "FN-002", "FN-004"], riskScore: 18, substituability: "VERY LOW", certifications: 3 },
  { id: "VND-005", name: "CyberArk", type: "Security", country: "IL", cost: 380000, functions: ["FN-003", "FN-006"], riskScore: 9, substituability: "MEDIUM", certifications: 3 },
];

const concentrationRisks = [
  { type: "Infrastructure", provider: "AWS", risk: "CRITICAL", detail: "AWS eu-central-1 failure impacts direct cloud (VND-001) AND CyberArk PAM (VND-005). 2 of 5 vendors share AWS dependency.", affected: ["AWS (direct)", "CyberArk (hosted on AWS)"], color: "#ef4444" },
  { type: "Geographic", provider: "US Processing", risk: "CRITICAL", detail: "Bloomberg and Aladdin process data primarily in the US, outside EEA. Conflicts with DORA Art. 30(2)(b) and bank data residency policy.", affected: ["Bloomberg", "BlackRock Aladdin"], color: "#ef4444" },
  { type: "Platform", provider: "Azure (via Aladdin)", risk: "HIGH", detail: "Aladdin runs on Azure + Snowflake. Three layers of dependency for risk calculations. No alternative platform.", affected: ["BlackRock Aladdin"], color: "#f97316" },
  { type: "Network", provider: "Equinix", risk: "MEDIUM", detail: "Bloomberg network appliances hosted in Equinix colocation. Single data center dependency for market data feeds.", affected: ["Bloomberg"], color: "#eab308" },
];

const functions = [
  { id: "FN-001", name: "Portfolio Mgmt", rto: "4h", rpo: "1h" },
  { id: "FN-002", name: "Risk Monitoring", rto: "8h", rpo: "4h" },
  { id: "FN-003", name: "KYC/AML", rto: "24h", rpo: "8h" },
  { id: "FN-004", name: "Fund Accounting", rto: "4h", rpo: "0" },
  { id: "FN-005", name: "ESG Reporting", rto: "48h", rpo: "24h" },
  { id: "FN-006", name: "Cybersecurity", rto: "1h", rpo: "0" },
];

function riskColor(score: number) {
  if (score >= 16) return { bg: "#fef2f2", text: "#991b1b" };
  if (score >= 10) return { bg: "#fff7ed", text: "#9a3412" };
  if (score >= 5) return { bg: "#fefce8", text: "#854d0e" };
  return { bg: "#f0fdf4", text: "#166534" };
}

export function RiskMap() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Concentration Risk Map</h2>
        <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>Vendor dependencies, shared infrastructure, and concentration risk analysis per DORA Art. 29</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9" }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Vendor &harr; Function Matrix</h3>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#f8fafc" }}>
                  <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 600, color: "#64748b", fontSize: 10, textTransform: "uppercase" as const }}>Vendor</th>
                  {functions.map((f) => (
                    <th key={f.id} style={{ padding: "8px 6px", fontWeight: 600, color: "#64748b", fontSize: 10, textAlign: "center", textTransform: "uppercase" as const }}>
                      {f.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {vendors.map((v) => (
                  <tr key={v.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 500 }}>{v.name}</td>
                    {functions.map((f) => (
                      <td key={f.id} style={{ textAlign: "center", padding: "10px 6px" }}>
                        {v.functions.includes(f.id) ? (
                          <span style={{ display: "inline-block", width: 20, height: 20, borderRadius: 4, background: "#3b82f6", color: "#fff", lineHeight: "20px", fontSize: 10, fontWeight: 700 }}>&#10003;</span>
                        ) : (
                          <span style={{ color: "#e2e8f0" }}>&mdash;</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9" }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Concentration Alerts</h3>
          </div>
          <div>
            {concentrationRisks.map((r, i) => (
              <div key={i} style={{ padding: "14px 20px", borderBottom: i < concentrationRisks.length - 1 ? "1px solid #f1f5f9" : "none" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: r.color }} />
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{r.provider}</span>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: r.risk === "CRITICAL" ? "#fef2f2" : r.risk === "HIGH" ? "#fff7ed" : "#fefce8", color: r.risk === "CRITICAL" ? "#991b1b" : r.risk === "HIGH" ? "#9a3412" : "#854d0e" }}>
                    {r.risk}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.5, marginBottom: 6 }}>{r.detail}</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" as const }}>
                  {r.affected.map((a) => (
                    <span key={a} style={{ fontSize: 10, padding: "2px 6px", background: "#f1f5f9", borderRadius: 4, color: "#475569" }}>{a}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9" }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Vendor Risk Profiles</h3>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f8fafc" }}>
              {["ID", "Vendor", "Type", "Country", "Annual Cost", "Functions", "Certifications", "Substituability", "Risk Score"].map((h) => (
                <th key={h} style={{ textAlign: h === "Annual Cost" ? "right" : "left", padding: "10px 14px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const, borderBottom: "1px solid #e2e8f0" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vendors.map((v) => {
              const rc = riskColor(v.riskScore);
              return (
                <tr key={v.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "12px 14px", fontFamily: "monospace", fontSize: 11, color: "#94a3b8" }}>{v.id}</td>
                  <td style={{ padding: "12px 14px", fontWeight: 600 }}>{v.name}</td>
                  <td style={{ padding: "12px 14px", color: "#64748b" }}>{v.type}</td>
                  <td style={{ padding: "12px 14px" }}>
                    <span style={{ padding: "2px 6px", background: "#f1f5f9", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>{v.country}</span>
                  </td>
                  <td style={{ padding: "12px 14px", textAlign: "right", fontFamily: "monospace" }}>€{(v.cost / 1000).toFixed(0)}K</td>
                  <td style={{ padding: "12px 14px", textAlign: "center" }}>{v.functions.length}</td>
                  <td style={{ padding: "12px 14px", textAlign: "center" }}>{v.certifications}</td>
                  <td style={{ padding: "12px 14px" }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: v.substituability === "VERY LOW" ? "#991b1b" : v.substituability === "LOW" ? "#9a3412" : "#854d0e" }}>
                      {v.substituability}
                    </span>
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <span style={{ padding: "3px 10px", borderRadius: 20, background: rc.bg, color: rc.text, fontWeight: 700, fontSize: 12 }}>{v.riskScore}/25</span>
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
