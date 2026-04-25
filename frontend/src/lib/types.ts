// Mirrors the FastAPI Pydantic schemas

export interface EvidenceSpan {
  text: string;
  page: number;
  document_id: string;
  node_id: string;
}

export interface ServiceClause {
  service_name: string;
  sla_hours: number | null;
}

export type Verdict = "met" | "partially_met" | "unmet" | "unknown";

export interface ObligationFinding {
  obligation_id: string;
  article: string;
  paragraph: string;
  description: string;
  verdict: Verdict;
  rationale: string;
  evidence_spans: EvidenceSpan[];
  gap_description: string;
  risk_level: string;
}

export interface AlternativeVendor {
  name: string;
  hq_country: string;
  eu_sovereign: boolean;
  certification: string;
  services_covered: string[];
  cost_delta: string;
  feature_delta: string;
  website: string;
}

export interface RemediationProposal {
  obligation_id: string;
  vendor_name: string;
  priority: string;
  summary: string;
  detail: string;
  sovereign_alternatives: AlternativeVendor[];
  estimated_effort_days: number | null;
  references: string[];
}

export interface ReportArtifact {
  session_id: string;
  generated_at: string;
  contract_ids: string[];
  executive_summary: string;
  findings: ObligationFinding[];
  remediation_proposals: RemediationProposal[];
  obligations_met: number;
  obligations_partial: number;
  obligations_unmet: number;
  overall_risk_level: string;
}

// Graph types
export interface NodeAttributes {
  label: string;
  size: number;
  color: string;
  node_type: string;
  criticality_score: number;
  country: string | null;
  is_critical_provider: boolean;
  x: number | null;
  y: number | null;
  // runtime-only
  baseSize?: number;
}

export interface GraphNode {
  key: string;
  attributes: NodeAttributes;
}

export interface EdgeAttributes {
  label: string;
  size: number;
  color: string;
}

export interface GraphEdge {
  key: string;
  source: string;
  target: string;
  attributes: EdgeAttributes;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Job types
export interface JobResult {
  status: string;
  contract_id: string;
  vendor_name: string;
  vendor_id: string;
  criticality_score: number;
  node_ids_count: number;
}

export interface Job {
  job_id: string;
  status: "running" | "done" | "error";
  contract_id: string;
  result: JobResult | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

// Upload state
export interface UploadedFile {
  file: File;
  contractId: string;
  jobId: string | null;
  status: "queued" | "uploading" | "running" | "done" | "error";
  vendorName?: string;
  score?: number;
  error?: string;
}
