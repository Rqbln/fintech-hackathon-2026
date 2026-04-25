import { useState, useRef } from "react";
import { uploadPDF, analyzeDocument, listDocuments } from "../api";
import type { UploadResult, DocumentInfo, AnalysisResult } from "../api";

interface Props {
  onAnalysisDone: (result: AnalysisResult) => void;
}

type Phase = "idle" | "uploading" | "uploaded" | "analyzing" | "done" | "error";

export function ContractUpload({ onAnalysisDone }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [vendorName, setVendorName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const loadDocs = async () => {
    try {
      const list = await listDocuments();
      setDocs(list);
    } catch {
      // non-critical
    }
  };

  const handleFile = async (f: File) => {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF files are accepted");
      return;
    }
    setFile(f);
    setPhase("uploading");
    setError(null);
    try {
      const result = await uploadPDF(f);
      setUploadResult(result);
      setVendorName(result.vendor_name || f.name.replace(".pdf", ""));
      setPhase("uploaded");
      loadDocs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setPhase("error");
    }
  };

  const runAnalysis = async () => {
    if (!uploadResult) return;
    setPhase("analyzing");
    setError(null);
    try {
      const result = await analyzeDocument(
        uploadResult.document_id,
        vendorName || uploadResult.vendor_name,
        uploadResult.filename,
      );
      setPhase("done");
      onAnalysisDone(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setPhase("error");
    }
  };

  const reset = () => {
    setFile(null);
    setPhase("idle");
    setUploadResult(null);
    setError(null);
    setVendorName("");
  };

  const phaseLabel: Record<Phase, string> = {
    idle: "Ready",
    uploading: "Uploading...",
    uploaded: "Uploaded",
    analyzing: "Analyzing (6 DORA categories via Gemini)...",
    done: "Analysis complete",
    error: "Error",
  };

  const phaseBadge: Record<Phase, { bg: string; text: string }> = {
    idle:      { bg: "#f1f5f9", text: "#475569" },
    uploading: { bg: "#eff6ff", text: "#1d4ed8" },
    uploaded:  { bg: "#eff6ff", text: "#1d4ed8" },
    analyzing: { bg: "#fef9c3", text: "#854d0e" },
    done:      { bg: "#f0fdf4", text: "#166534" },
    error:     { bg: "#fef2f2", text: "#991b1b" },
  };

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Upload Vendor Contract</h2>
      <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 24px" }}>
        Upload a PDF contract — OCR extraction, DORA compliance scoring and graph generation run automatically
      </p>

      {/* Drop zone */}
      {phase === "idle" && (
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
            {dragOver ? "Drop your PDF here" : "Drag & drop a PDF here"}
          </div>
          <div style={{ fontSize: 13, color: "#94a3b8" }}>or click to browse &middot; PDF only &middot; max 50 MB</div>
        </div>
      )}

      {/* File card */}
      {file && phase !== "idle" && (
        <div style={{ marginTop: 20, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, maxWidth: 600 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{file.name}</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{(file.size / 1024).toFixed(0)} KB</div>
            </div>
            <span style={{ padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600, ...phaseBadge[phase] }}>
              {phaseLabel[phase]}
            </span>
          </div>

          {/* Spinner for long ops */}
          {(phase === "uploading" || phase === "analyzing") && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#64748b", padding: "8px 0" }}>
              <span style={{ display: "inline-block", width: 14, height: 14, border: "2px solid #3b82f6", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
              {phase === "uploading" ? "OCR extraction in progress..." : "Running RAG + Gemini on 6 DORA categories..."}
            </div>
          )}

          {/* Vendor name input + run button after upload */}
          {phase === "uploaded" && uploadResult && (
            <div style={{ marginTop: 8 }}>
              <div style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, fontSize: 13, marginBottom: 12 }}>
                <div style={{ fontWeight: 600, color: "#166534", marginBottom: 6 }}>Extraction complete</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, color: "#475569" }}>
                  <div><span style={{ color: "#94a3b8" }}>doc_id:</span> <code style={{ fontSize: 11 }}>{uploadResult.document_id}</code></div>
                  <div><span style={{ color: "#94a3b8" }}>Clauses:</span> {uploadResult.clause_count}</div>
                  <div><span style={{ color: "#94a3b8" }}>SLA entries:</span> {uploadResult.sla_entry_count}</div>
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Vendor name (for graph labels)</label>
                <input
                  value={vendorName}
                  onChange={(e) => setVendorName(e.target.value)}
                  placeholder="e.g. Cloud Provider Inc."
                  style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #cbd5e1", fontSize: 13, boxSizing: "border-box" }}
                />
              </div>
              <button
                onClick={runAnalysis}
                style={{ padding: "10px 24px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              >
                Run DORA Compliance Analysis
              </button>
            </div>
          )}

          {phase === "done" && (
            <div style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, fontSize: 13, color: "#166534", fontWeight: 600, marginBottom: 12 }}>
              Analysis complete — graph updated, navigate to "Vendor Graph" tab
            </div>
          )}

          {error && (
            <div style={{ padding: 12, background: "#fef2f2", borderRadius: 8, fontSize: 13, color: "#991b1b", marginBottom: 12 }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {(phase === "done" || phase === "error") && (
            <button onClick={reset} style={{ padding: "8px 16px", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13, cursor: "pointer", color: "#475569" }}>
              Upload another
            </button>
          )}
        </div>
      )}

      {/* Indexed documents list */}
      <div style={{ marginTop: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Indexed Documents</h3>
          <button onClick={loadDocs} style={{ fontSize: 12, color: "#3b82f6", background: "none", border: "none", cursor: "pointer" }}>Refresh</button>
        </div>
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
          {docs === null ? (
            <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8", fontSize: 13 }}>
              <button onClick={loadDocs} style={{ color: "#3b82f6", background: "none", border: "none", cursor: "pointer", fontSize: 13 }}>Load indexed documents</button>
            </div>
          ) : docs.length === 0 ? (
            <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8", fontSize: 13 }}>No documents indexed yet</div>
          ) : (
            docs.map((doc, i) => (
              <div key={i} style={{ padding: "12px 20px", borderBottom: i < docs.length - 1 ? "1px solid #f1f5f9" : "none", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
                <div>
                  <span style={{ fontWeight: 500 }}>{doc.filename}</span>
                  <span style={{ color: "#94a3b8", marginLeft: 8 }}>{doc.vendor_name}</span>
                </div>
                <div style={{ display: "flex", gap: 16, alignItems: "center", color: "#64748b" }}>
                  <span>{doc.clause_count} clauses</span>
                  <code style={{ fontSize: 11, color: "#94a3b8" }}>{doc.document_id}</code>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
