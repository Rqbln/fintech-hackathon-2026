import type { GraphResponse, Job, ReportArtifact } from "./types";

const BASE = "";  // rewrites proxy /api/* to FastAPI

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export async function ingestContract(
  file: File,
  contractId?: string
): Promise<{ job_id: string; contract_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const url = contractId
    ? `/api/ingest?contract_id=${encodeURIComponent(contractId)}`
    : "/api/ingest";
  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
  return res.json();
}

export async function pollJob(jobId: string): Promise<Job> {
  return get<Job>(`/api/jobs/${jobId}`);
}

export async function getGraph(rootVendor?: string, depth = 2): Promise<GraphResponse> {
  const params = new URLSearchParams({ depth: String(depth) });
  if (rootVendor) params.set("root_vendor", rootVendor);
  return get<GraphResponse>(`/api/graph?${params}`);
}

export async function runGapAnalysis(params: {
  contract_ids: string[];
  vendor_name: string;
  contract_text_preview?: string;
  obligation_ids?: string[];
}): Promise<ReportArtifact> {
  return post<ReportArtifact>("/api/gap-analysis", params);
}

export async function getReportMarkdown(sessionId: string): Promise<string> {
  const res = await fetch(`/api/report/${sessionId}/markdown`);
  if (!res.ok) throw new Error(`Report fetch failed: ${res.status}`);
  return res.text();
}
