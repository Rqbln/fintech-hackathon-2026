import { useState, useRef } from "react";

interface ExtractedFile {
  document_id: string;
  filename: string;
  vendor_name: string;
  status: string;
  total_clauses: number;
  total_sla_entries: number;
}

interface FileState {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export function ContractUpload() {
  const [dragOver, setDragOver] = useState(false);
  const [fileStates, setFileStates] = useState<FileState[]>([]);
  const [results, setResults] = useState<ExtractedFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (incoming: FileList | File[]) => {
    const pdfs = Array.from(incoming).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    const rejected = Array.from(incoming).length - pdfs.length;
    if (rejected > 0) alert(`${rejected} file(s) ignored — only PDFs are accepted`);
    if (pdfs.length === 0) return;
    setFileStates((prev) => [
      ...prev,
      ...pdfs.map((f) => ({ file: f, status: "pending" as const })),
    ]);
  };

  const uploadAll = async () => {
    const pending = fileStates.filter((s) => s.status === "pending");
    if (pending.length === 0) return;

    setFileStates((prev) =>
      prev.map((s) => (s.status === "pending" ? { ...s, status: "uploading" as const } : s))
    );

    const form = new FormData();
    for (const { file } of pending) form.append("files", file);

    try {
      const res = await fetch("/api/documents/upload", { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        const msg = body?.detail ?? "Upload failed";
        setFileStates((prev) =>
          prev.map((s) => (s.status === "uploading" ? { ...s, status: "error" as const, error: msg } : s))
        );
        return;
      }
      const data: { uploaded: ExtractedFile[]; count: number } = await res.json();
      const doneNames = new Set(data.uploaded.map((u) => u.filename));
      setFileStates((prev) =>
        prev.map((s) =>
          s.status === "uploading"
            ? doneNames.has(s.file.name)
              ? { ...s, status: "done" as const }
              : { ...s, status: "error" as const, error: "Not returned by server" }
            : s
        )
      );
      setResults((prev) => [...prev, ...data.uploaded]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Network error";
      setFileStates((prev) =>
        prev.map((s) => (s.status === "uploading" ? { ...s, status: "error" as const, error: msg } : s))
      );
    }
  };

  const hasPending = fileStates.some((s) => s.status === "pending");

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Upload Vendor Documents</h2>
      <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 24px" }}>
        Upload vendor contracts, SLAs, or SOC 2 reports for automated DORA compliance extraction
      </p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
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
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          hidden
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
        <div style={{ fontSize: 40, marginBottom: 12 }}>&#128196;</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#334155", marginBottom: 4 }}>
          {dragOver ? "Drop your PDFs here" : "Drag & drop PDFs here"}
        </div>
        <div style={{ fontSize: 13, color: "#94a3b8" }}>
          or click to browse &middot; PDF only &middot; multi-select supported &middot; max 50 MB each
        </div>
      </div>

      {fileStates.length > 0 && (
        <div style={{ marginTop: 20, maxWidth: 600 }}>
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
            {fileStates.map((s, i) => (
              <div key={i} style={{ padding: "12px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{s.file.name}</div>
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>{(s.file.size / 1024).toFixed(0)} KB</div>
                  {s.error && <div style={{ fontSize: 11, color: "#991b1b", marginTop: 2 }}>{s.error}</div>}
                </div>
                <span style={{
                  padding: "4px 12px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: 600,
                  background: s.status === "done" ? "#f0fdf4" : s.status === "error" ? "#fef2f2" : s.status === "uploading" ? "#eff6ff" : "#f8fafc",
                  color: s.status === "done" ? "#166534" : s.status === "error" ? "#991b1b" : s.status === "uploading" ? "#1d4ed8" : "#475569",
                }}>
                  {s.status === "pending" ? "Ready" : s.status === "uploading" ? "Uploading…" : s.status === "done" ? "Extracted" : "Error"}
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            {hasPending && (
              <button
                onClick={uploadAll}
                style={{ padding: "8px 20px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              >
                Upload {fileStates.filter((s) => s.status === "pending").length} file(s)
              </button>
            )}
            <button
              onClick={() => { setFileStates([]); setResults([]); }}
              style={{ padding: "8px 16px", background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 8, fontSize: 13, cursor: "pointer" }}
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: 24, maxWidth: 600 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Extraction Results</h3>
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", overflow: "hidden" }}>
            {results.map((r, i) => (
              <div key={i} style={{ padding: "12px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{r.filename}</div>
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>{r.vendor_name}</div>
                </div>
                <div style={{ display: "flex", gap: 16, alignItems: "center", color: "#64748b" }}>
                  <span>{r.total_clauses} clauses</span>
                  <span>{r.total_sla_entries} SLA</span>
                  <span style={{ padding: "2px 8px", background: "#f0fdf4", color: "#166534", borderRadius: 12, fontWeight: 600, fontSize: 11 }}>
                    {r.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
