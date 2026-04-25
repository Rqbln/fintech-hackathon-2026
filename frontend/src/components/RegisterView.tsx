const registerEntries = [
  { model: "B_01.01", entity: "Eurobank Investment Solutions S.A.", lei: "549300EXAMPLE000EBIS", country: "FR", type: "UCITS Management Company", aum: "€18.7B", status: "complete" },
  { model: "B_01.02", entity: "Eurobank IS - Luxembourg Branch", lei: "549300EXAMPLE000EBIS", country: "LU", type: "Branch", aum: "—", status: "complete" },
  { model: "B_01.02", entity: "Eurobank IS - Amsterdam Branch", lei: "549300EXAMPLE000EBIS", country: "NL", type: "Branch", aum: "—", status: "complete" },
  { model: "B_01.03", entity: "Eurobank N.V. (Parent)", lei: "549300EXAMPLE000EBNV", country: "NL", type: "Group Parent", aum: "—", status: "complete" },
  { model: "B_03.01", entity: "Amazon Web Services EMEA SARL", lei: "549300EXAMPLE000AWSE", country: "LU", type: "Cloud IaaS", aum: "€1.85M/yr", status: "complete" },
  { model: "B_03.01", entity: "Bloomberg Finance L.P.", lei: "549300EXAMPLE000BFLP", country: "US", type: "Market Data", aum: "€2.4M/yr", status: "review" },
  { model: "B_03.01", entity: "S.W.I.F.T. SCRL", lei: "549300EXAMPLE000SWFT", country: "BE", type: "Messaging", aum: "€420K/yr", status: "complete" },
  { model: "B_03.01", entity: "BlackRock Financial Management, Inc.", lei: "549300EXAMPLE000BKFM", country: "US", type: "Platform", aum: "€3.2M/yr", status: "review" },
  { model: "B_03.01", entity: "CyberArk Software Ltd.", lei: "549300EXAMPLE000CYBK", country: "IL", type: "Security", aum: "€380K/yr", status: "review" },
  { model: "B_04.01", entity: "Equinix Inc. (sub of Bloomberg)", lei: "549300EXAMPLE000EQNX", country: "US", type: "Colocation", aum: "—", status: "complete" },
  { model: "B_04.01", entity: "Microsoft Azure (sub of BlackRock)", lei: "549300EXAMPLE000MSFT", country: "US", type: "Cloud hosting", aum: "—", status: "complete" },
  { model: "B_04.01", entity: "Snowflake Inc. (sub of BlackRock)", lei: "549300EXAMPLE000SNFL", country: "US", type: "Data warehouse", aum: "—", status: "complete" },
  { model: "B_04.01", entity: "AWS Inc. (sub of CyberArk)", lei: "549300EXAMPLE000AWSI", country: "US", type: "Cloud hosting", aum: "—", status: "complete" },
  { model: "B_05.01", entity: "Portfolio Management & Order Execution", lei: "—", country: "FR", type: "Critical Function", aum: "RTO: 4h", status: "complete" },
  { model: "B_05.01", entity: "Risk Measurement & Reporting", lei: "—", country: "FR", type: "Critical Function", aum: "RTO: 8h", status: "complete" },
];

const statusStyle: Record<string, { bg: string; text: string; label: string }> = {
  complete: { bg: "#f0fdf4", text: "#166534", label: "Complete" },
  review: { bg: "#fefce8", text: "#854d0e", label: "Under Review" },
  missing: { bg: "#fef2f2", text: "#991b1b", label: "Missing" },
};

export function RegisterView() {
  const complete = registerEntries.filter((e) => e.status === "complete").length;
  const review = registerEntries.filter((e) => e.status === "review").length;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>DORA Register of Information</h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            Regulatory RoI per ESA ITS templates &middot; {complete} complete, {review} under review
          </p>
        </div>
        <button
          onClick={() => {
            const csv = [
              ["Model", "Entity", "LEI", "Country", "Type", "Value", "Status"].join(","),
              ...registerEntries.map((e) =>
                [e.model, `"${e.entity}"`, e.lei, e.country, e.type, `"${e.aum}"`, e.status].join(",")
              ),
            ].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "regagent_roi_export.csv";
            a.click();
            URL.revokeObjectURL(url);
          }}
          style={{
            padding: "8px 20px",
            background: "#0f172a",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Export CSV
        </button>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {[
          { label: "B_01.xx Entity", count: registerEntries.filter((e) => e.model.startsWith("B_01")).length, color: "#3b82f6" },
          { label: "B_03.xx Vendors", count: registerEntries.filter((e) => e.model.startsWith("B_03")).length, color: "#8b5cf6" },
          { label: "B_04.xx Subcontractors", count: registerEntries.filter((e) => e.model.startsWith("B_04")).length, color: "#f59e0b" },
          { label: "B_05.xx Functions", count: registerEntries.filter((e) => e.model.startsWith("B_05")).length, color: "#22c55e" },
        ].map((g) => (
          <div key={g.label} style={{ padding: "8px 16px", background: "#fff", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: g.color }} />
            <span style={{ color: "#64748b" }}>{g.label}:</span>
            <span style={{ fontWeight: 700 }}>{g.count}</span>
          </div>
        ))}
      </div>

      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f8fafc" }}>
              {["RoI Model", "Entity / Function", "LEI Code", "Country", "Type", "Value", "Status"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "10px 14px", fontWeight: 600, color: "#64748b", fontSize: 11, textTransform: "uppercase" as const, borderBottom: "1px solid #e2e8f0" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {registerEntries.map((e, i) => {
              const st = statusStyle[e.status];
              return (
                <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{ fontFamily: "monospace", fontSize: 12, padding: "2px 6px", background: "#f1f5f9", borderRadius: 4, fontWeight: 600 }}>{e.model}</span>
                  </td>
                  <td style={{ padding: "10px 14px", fontWeight: 500, maxWidth: 260 }}>{e.entity}</td>
                  <td style={{ padding: "10px 14px", fontFamily: "monospace", fontSize: 11, color: "#94a3b8" }}>{e.lei}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{ padding: "2px 6px", background: "#f1f5f9", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>{e.country}</span>
                  </td>
                  <td style={{ padding: "10px 14px", color: "#64748b" }}>{e.type}</td>
                  <td style={{ padding: "10px 14px", color: "#475569" }}>{e.aum}</td>
                  <td style={{ padding: "10px 14px" }}>
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
