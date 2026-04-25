/**
 * API client — all calls to the FastAPI backend go through here.
 * The Vite proxy rewrites /api/* → http://localhost:8000/*
 */

// ---------------------------------------------------------------------------
// Types mirroring backend Pydantic models
// ---------------------------------------------------------------------------

export interface UploadResult {
  document_id: string;
  vendor_name: string;
  filename: string;
  clause_count: number;
  sla_entry_count: number;
  gcs_uri: string;
}

export interface BatchStatus {
  batch_id: string;
  status: "pending" | "processing" | "done";
  total: number;
  completed: number;
  results: UploadResult[];
  errors: { filename: string; error: string }[];
}

export interface Alert {
  alert_id: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  dora_reference: string;
  page: number;
  gap_details: string;
  remediation: string;
  category: string;
}

export interface CategoryScores {
  rto_rpo: number;
  audit_rights: number;
  data_residency: number;
  subcontracting: number;
  incident_reporting: number;
  exit_strategy: number;
}

export interface Evaluation {
  doc_id: string;
  vendor_name: string;
  compliance_score: number;
  status: "compliant" | "partial" | "non_compliant";
  alerts: Alert[];
  category_scores: CategoryScores;
}

export interface Subcontractor {
  name: string;
  service: string;
  data_location: string;
  risk_flag: boolean;
  page: number;
  evidence: string;
}

export interface GraphNode {
  id: string;
  type: "bank" | "vendor" | "subcontractor";
  position: { x: number; y: number };
  data: {
    label: string;
    compliance_score?: number;
    risk_color?: string;
    risk_label?: string;
    alerts?: Alert[];
    category_scores?: CategoryScores;
    on_click?: { action: string; doc_id: string; page: number; filename?: string };
    amendment_hints?: string[];
    service?: string;
    data_location?: string;
    risk_flag?: boolean;
    evidence?: { page: number; excerpt: string };
    lei_code?: string;
    country?: string;
    role?: string;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  animated: boolean;
  style: { stroke: string; strokeWidth: number };
  data: { critical: boolean };
}

export interface GraphMeta {
  doc_id: string;
  vendor_name: string;
  filename: string;
  compliance_score: number;
  risk_label: string;
  risk_color: string;
  alert_count: number;
  subcontractor_count: number;
  category_scores: CategoryScores;
}

export interface AnalysisResult {
  doc_id: string;
  vendor_name: string;
  filename: string;
  evaluation: Evaluation;
  subcontractors: Subcontractor[];
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    meta: GraphMeta;
  };
}

export interface DocumentInfo {
  document_id: string;
  vendor_name: string;
  filename: string;
  clause_count: number;
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function uploadPDF(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents/upload", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadBatch(files: File[]): Promise<{ batch_id: string }> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch("/api/documents/upload/batch", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchStatus> {
  return get<BatchStatus>(`/documents/upload/batch/${batchId}`);
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  return get<DocumentInfo[]>("/documents/");
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export async function analyzeDocument(
  docId: string,
  vendorName: string,
  filename: string,
): Promise<AnalysisResult> {
  const params = new URLSearchParams({ vendor_name: vendorName, filename });
  return get<AnalysisResult>(`/analysis/${docId}?${params}`);
}
