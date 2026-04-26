import type { FindTextResult, GraphResponse, Job, ReportArtifact, SessionSummary, VendorConcentrationItem } from "./types";

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
): Promise<{ job_id: string; contract_id: string; status: string; gcs_uri?: string }> {
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

export async function getVendorConcentration(): Promise<VendorConcentrationItem[]> {
  return get<VendorConcentrationItem[]>("/api/graph/concentration");
}

export async function runGapAnalysis(params: {
  contract_ids: string[];
  vendor_name: string;
  contract_text_preview?: string;
  obligation_ids?: string[];
}): Promise<ReportArtifact> {
  return post<ReportArtifact>("/api/gap-analysis", params);
}

export type GapStreamEvent =
  | { type: "finding"; data: import("./types").ObligationFinding }
  | { type: "progress"; stage: "analysis" | "remediation" | "done"; completed: number; total: number; message?: string }
  | { type: "done"; report: import("./types").ReportArtifact }
  | { type: "error"; message: string };

export async function streamGapAnalysis(
  params: {
    contract_ids: string[];
    vendor_name: string;
    contract_text_preview?: string;
    obligation_ids?: string[];
    primary_contract_id?: string;
    use_cache?: boolean;
  },
  onEvent: (event: GapStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch("/api/gap-analysis-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`gap-analysis-stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // SSE lines are separated by \n\n; each line starts with "data: "
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";

    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6)) as GapStreamEvent;
          onEvent(event);
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function getReportMarkdown(sessionId: string): Promise<string> {
  const res = await fetch(`/api/report/${sessionId}/markdown`);
  if (!res.ok) throw new Error(`Report fetch failed: ${res.status}`);
  return res.text();
}

export async function getCompliantDraftMarkdown(sessionId: string, vendorName?: string): Promise<string> {
  const payload = vendorName?.trim() ? { vendor_name: vendorName.trim() } : {};
  const res = await fetch(`/api/report/${sessionId}/compliant-draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Compliant draft generation failed: ${res.status}`);
  return res.text();
}

export async function getCompliantDraftPdf(sessionId: string, vendorName?: string): Promise<Blob> {
  const payload = vendorName?.trim() ? { vendor_name: vendorName.trim() } : {};
  const res = await fetch(`/api/report/${sessionId}/compliant-draft.pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Compliant PDF generation failed: ${res.status}`);
  return res.blob();
}

export async function getReport(sessionId: string): Promise<ReportArtifact> {
  return get<ReportArtifact>(`/api/report/${sessionId}`);
}

export async function listSessions(): Promise<SessionSummary[]> {
  return get<SessionSummary[]>("/api/sessions");
}

export async function getSessionTrace(sessionId: string): Promise<ReportArtifact> {
  return get<ReportArtifact>(`/api/sessions/${sessionId}/trace`);
}

export async function findTextPage(contractId: string, quote: string): Promise<FindTextResult> {
  const params = new URLSearchParams({ q: quote });
  return get<FindTextResult>(`/api/documents/${encodeURIComponent(contractId)}/find-text?${params.toString()}`);
}

export function buildHighlightedPdfUrl(contractId: string, quote: string, page?: number): string {
  const params = new URLSearchParams();
  params.append("highlights", quote);
  if (page && page > 0) params.set("page", String(page));
  return `/api/documents/${encodeURIComponent(contractId)}/pdf?${params.toString()}#page=${page && page > 0 ? page : 1}`;
}

export function buildMultiHighlightedPdfUrl(contractId: string, quotes: string[], page?: number): string {
  const params = new URLSearchParams();
  const deduped = Array.from(new Set(quotes.map((q) => q.trim()).filter(Boolean))).slice(0, 8);
  for (const q of deduped) params.append("highlights", q);
  if (page && page > 0) params.set("page", String(page));
  return `/api/documents/${encodeURIComponent(contractId)}/pdf?${params.toString()}#page=${page && page > 0 ? page : 1}`;
}
