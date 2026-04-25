import { useState, useRef } from "react";

export function ContractUpload() {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF files are accepted");
      return;
    }
    setFile(f);
    setStatus("uploading");
    setTimeout(() => setStatus("done"), 1500);
  };

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Upload Vendor Document</h2>
      <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 24px" }}>Upload a vendor contract, SLA, or SOC 2 report for automated DORA compliance extraction</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "#3b82f6" : "#cbd5e1"}`,
          borderRadius: 16,
          padding: "48px 24px",
          textAlign: "center",
          background: dragOver ? "#eff6ff" : "#fff",
          cursor: "pointer",
          transition: "all 0.15s",
          maxWidth: 600,
        }}
      >
        <input ref={inputRef} type="file" accept=".pdf" hidden onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
        <div style={{ fontSize: 40, marginBottom: 12 }}>&#128196;</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#334155", marginBottom: 4 }}>
          {dragOver ? "Drop your file here" : "Drag & drop a PDF here"}
        </div>
        <div style={{ fontSize: 13, color: "#94a3b8" }}>or click to browse &middot; PDF only &middot; max 50MB</div>
      </div>

      {file && (
        <div style={{ marginTop: 20, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, maxWidth: 600 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{file.name}</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{(file.size / 1024).toFixed(0)} KB</div>
            </div>
            <span style={{
              padding: "4px 12px",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 600,
              background: status === "done" ? "#f0fdf4" : status === "error" ? "#fef2f2" : "#eff6ff",
              color: status === "done" ? "#166534" : status === "error" ? "#991b1b" : "#1d4ed8",
            }}>
              {status === "uploading" ? "Processing..." : status === "done" ? "Extracted" : status === "error" ? "Error" : "Ready"}
            </span>
          </div>

          {status === "done" && (
            <div style={{ marginTop: 16, padding: 16, background: "#f8fafc", borderRadius: 8, fontSize: 13 }}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: "#334155" }}>Extraction Preview</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, color: "#475569" }}>
                <div><span style={{ color: "#94a3b8" }}>Clauses found:</span> 24</div>
                <div><span style={{ color: "#94a3b8" }}>SLA entries:</span> 8</div>
                <div><span style={{ color: "#94a3b8" }}>Entities:</span> 12</div>
                <div><span style={{ color: "#94a3b8" }}>Confidence:</span> 94.2%</div>
              </div>
              <button style={{
                marginTop: 12, padding: "8px 20px", background: "#3b82f6", color: "#fff",
                border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}>
                Run Compliance Analysis
              </button>
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Recent Documents</h3>
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          {[
            { name: "aws_cloud_contract_2023.pdf", vendor: "AWS", date: "2026-04-25", clauses: 31, status: "Analyzed" },
            { name: "bloomberg_data_services_sla.pdf", vendor: "Bloomberg", date: "2026-04-25", clauses: 24, status: "Analyzed" },
            { name: "swift_messaging_agreement.pdf", vendor: "SWIFT", date: "2026-04-25", clauses: 18, status: "Analyzed" },
            { name: "aladdin_platform_license.pdf", vendor: "BlackRock", date: "2026-04-25", clauses: 27, status: "Analyzed" },
            { name: "cyberark_pam_contract.pdf", vendor: "CyberArk", date: "2026-04-25", clauses: 22, status: "Analyzed" },
          ].map((doc, i) => (
            <div key={i} style={{ padding: "12px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
              <div>
                <span style={{ fontWeight: 500 }}>{doc.name}</span>
                <span style={{ color: "#94a3b8", marginLeft: 8 }}>{doc.vendor}</span>
              </div>
              <div style={{ display: "flex", gap: 16, alignItems: "center", color: "#64748b" }}>
                <span>{doc.clauses} clauses</span>
                <span>{doc.date}</span>
                <span style={{ padding: "2px 8px", background: "#f0fdf4", color: "#166534", borderRadius: 12, fontWeight: 600, fontSize: 11 }}>{doc.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
