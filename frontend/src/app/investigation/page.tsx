"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Loader2,
} from "lucide-react";
import type { ObligationFinding, RemediationProposal } from "@/lib/types";
import {
  buildHighlightedPdfUrl,
  buildMultiHighlightedPdfUrl,
  getCompliantDraftPdf,
  findTextPage,
  getSessionTrace,
  listSessions,
  streamGapAnalysis,
} from "@/lib/api";
import { cn, riskBadgeClass } from "@/lib/utils";
import SaasShell from "@/components/shell/SaasShell";

type ViewTab = "findings" | "remediation" | "audit";

interface CitationTarget {
  contractId: string;
  page: number;
  quote: string;
}

const ANALYSIS_CACHE_KEY = "dora_analysis_cache_v1";
const ANALYSIS_SESSION_BY_CONTRACT = "dora_analysis_session_by_contract_v1";

function FindingItem({
  finding,
  onCitationClick,
}: {
  finding: ObligationFinding;
  onCitationClick: (finding: ObligationFinding, contractId: string, page: number, quote: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const complianceScore =
    finding.verdict === "met" ? 100 : finding.verdict === "partially_met" ? 65 : finding.verdict === "unmet" ? 25 : 50;
  const severityTone =
    finding.risk_level === "critical"
      ? "border-rose-300 bg-rose-100"
      : finding.risk_level === "high"
        ? "border-orange-300 bg-orange-100"
        : finding.risk_level === "medium"
          ? "border-violet-300 bg-violet-100"
          : "border-emerald-300 bg-emerald-100";

  const shortTitle = `${finding.obligation_id} - Art.${finding.article} §${finding.paragraph}`;

  return (
    <article className={cn("rounded-xl border p-3 shadow-sm", severityTone)}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Non-conformity</p>
          <p className="text-xs font-semibold text-slate-800">{shortTitle}</p>
          <p className="mt-1 text-[11px] text-slate-600">{finding.description.slice(0, 120)}{finding.description.length > 120 ? "..." : ""}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="rounded-full border border-indigo-300 bg-indigo-200 px-2 py-0.5 text-[10px] font-semibold text-indigo-900">
            Compliance {complianceScore}%
          </span>
          <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize", riskBadgeClass(finding.risk_level))}>
            {finding.verdict.replace("_", " ")}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-end">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
        >
          {expanded ? "Masquer les détails" : "Plus de détails"}
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
      </div>
      {expanded && (
        <>
          <div className="mt-2 rounded-lg border border-white/70 bg-white/80 p-2">
            <p className="text-[11px] font-semibold text-slate-700">AI Rationale</p>
            <p className="mt-1 text-xs text-slate-700">{finding.rationale}</p>
          </div>
          {finding.gap_description && (
            <div className="mt-2 rounded-lg border border-rose-200 bg-white p-2">
              <p className="text-[11px] font-semibold text-rose-700">Gap Description</p>
              <p className="mt-1 text-xs text-rose-700">{finding.gap_description}</p>
            </div>
          )}
          {finding.evidence_spans.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="mb-1 text-[11px] font-semibold text-slate-700">Sources</p>
              {finding.evidence_spans.slice(0, 5).map((span, i) => (
                <button
                  key={`${finding.obligation_id}-${i}`}
                  onClick={() => onCitationClick(finding, span.document_id, span.page, span.text)}
                  className="block w-full rounded-lg border border-amber-300 bg-amber-100 px-2 py-1.5 text-left text-[11px] text-amber-900 hover:bg-amber-200"
                >
                  p.{span.page > 0 ? span.page : "?"} - {span.text.slice(0, 140)}
                  {span.text.length > 140 ? "..." : ""}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </article>
  );
}

function InvestigationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const vendorKey = searchParams.get("vendorKey") ?? "";
  const vendorName = searchParams.get("vendorName") ?? "Selected Vendor";
  const requestedPrimaryContractId = searchParams.get("primaryContractId") ?? "";
  const contractIds = useMemo(
    () =>
      (searchParams.get("contractIds") ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    [searchParams]
  );
  const primaryContractId = requestedPrimaryContractId || contractIds[0] || vendorKey;

  const [tab, setTab] = useState<ViewTab>("findings");
  const [findings, setFindings] = useState<ObligationFinding[]>([]);
  const [proposals, setProposals] = useState<RemediationProposal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [generatingCompliantPdf, setGeneratingCompliantPdf] = useState(false);
  const [runStartedAt, setRunStartedAt] = useState<string>("");
  const [streamCount, setStreamCount] = useState(0);
  const [progressStage, setProgressStage] = useState<"analysis" | "remediation" | "done">("analysis");
  const [progressCompleted, setProgressCompleted] = useState(0);
  const [progressTotal, setProgressTotal] = useState(12);
  const [progressMessage, setProgressMessage] = useState("Starting live compliance analysis...");
  const [activeCitation, setActiveCitation] = useState<CitationTarget | null>(null);
  const [activeContractId, setActiveContractId] = useState<string>(primaryContractId);
  const [activePage, setActivePage] = useState(1);
  const [highlightedPdfUrl, setHighlightedPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const activeRunKeyRef = useRef<string | null>(null);

  const cacheKey = useMemo(() => `${vendorName}::${primaryContractId}`, [vendorName, primaryContractId]);

  useEffect(() => {
    setActiveContractId(primaryContractId);
    setHighlightedPdfUrl(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [primaryContractId]);

  useEffect(() => {
    if (!vendorName || !primaryContractId) return;
    const runKey = `${vendorName}::${primaryContractId}`;
    if (activeRunKeyRef.current === runKey) return;
    activeRunKeyRef.current = runKey;

    let cancelled = false;
    try {
      const raw = sessionStorage.getItem(ANALYSIS_CACHE_KEY);
      const cache = raw ? (JSON.parse(raw) as Record<string, { findings: ObligationFinding[]; proposals: RemediationProposal[]; sessionId: string | null; runStartedAt: string; streamCount: number }>) : {};
      const hit = cache[cacheKey];
      if (hit) {
        setFindings(hit.findings);
        setProposals(hit.proposals);
        setSessionId(hit.sessionId);
        setRunStartedAt(hit.runStartedAt);
        setStreamCount(hit.streamCount);
        setLoading(false);
        setProgressStage("done");
        setProgressCompleted(hit.findings.length);
        setProgressTotal(Math.max(hit.findings.length, 1));
        setProgressMessage("Loaded cached analysis.");
        return;
      }
    } catch {
      // ignore cache parsing errors
    }

    const startStreaming = () => {
      abortRef.current?.abort();
      setLoading(true);
      setError(null);
      setFindings([]);
      setProposals([]);
      setSessionId(null);
      setActiveCitation(null);
      const startedAt = new Date().toISOString();
      setRunStartedAt(startedAt);
      setStreamCount(0);
      setProgressStage("analysis");
      setProgressCompleted(0);
      setProgressTotal(12);
      setProgressMessage("Starting live compliance analysis...");

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      streamGapAnalysis(
        {
          contract_ids: [primaryContractId],
          vendor_name: vendorName,
          primary_contract_id: primaryContractId,
          use_cache: false,
        },
        (event) => {
          if (cancelled) return;
          if (event.type === "finding") {
            setStreamCount((n) => n + 1);
            setFindings((prev) => {
              const idx = prev.findIndex((f) => f.obligation_id === event.data.obligation_id);
              const next = [...prev];
              if (idx >= 0) next[idx] = event.data;
              else next.push(event.data);
              try {
                const raw = sessionStorage.getItem(ANALYSIS_CACHE_KEY);
                const cache = raw ? JSON.parse(raw) : {};
                cache[cacheKey] = {
                  findings: next,
                  proposals,
                  sessionId,
                  runStartedAt: startedAt,
                  streamCount: next.length,
                };
                sessionStorage.setItem(ANALYSIS_CACHE_KEY, JSON.stringify(cache));
              } catch {
                // ignore cache write failures
              }
              return next;
            });
            return;
          }
          if (event.type === "progress") {
            setProgressStage(event.stage);
            setProgressCompleted(event.completed);
            setProgressTotal(event.total > 0 ? event.total : 12);
            setProgressMessage(event.message ?? "");
            return;
          }
          if (event.type === "done") {
            setFindings(event.report.findings);
            setProposals(event.report.remediation_proposals);
            setSessionId(event.report.session_id);
            setProgressStage("done");
            setProgressCompleted(event.report.findings.length);
            setProgressTotal(Math.max(event.report.findings.length, 1));
            setProgressMessage("Analysis completed.");
            setLoading(false);
            try {
              const raw = sessionStorage.getItem(ANALYSIS_CACHE_KEY);
              const cache = raw ? JSON.parse(raw) : {};
              cache[cacheKey] = {
                findings: event.report.findings,
                proposals: event.report.remediation_proposals,
                sessionId: event.report.session_id,
                runStartedAt: startedAt,
                streamCount: event.report.findings.length,
              };
              sessionStorage.setItem(ANALYSIS_CACHE_KEY, JSON.stringify(cache));
              const rawByContract = sessionStorage.getItem(ANALYSIS_SESSION_BY_CONTRACT);
              const byContract = rawByContract ? JSON.parse(rawByContract) : {};
              byContract[primaryContractId] = event.report.session_id;
              sessionStorage.setItem(ANALYSIS_SESSION_BY_CONTRACT, JSON.stringify(byContract));
            } catch {
              // ignore cache write failures
            }
            return;
          }
          if (event.type === "error") {
            setError(event.message);
            setLoading(false);
          }
        },
        ctrl.signal
      ).catch((e: Error) => {
        if (!cancelled && e.name !== "AbortError") {
          setError(e.message);
          setLoading(false);
        }
      });
    };

    (async () => {
      try {
        const rawByContract = sessionStorage.getItem(ANALYSIS_SESSION_BY_CONTRACT);
        const byContract = rawByContract ? JSON.parse(rawByContract) : {};
        const existingSessionId: string | undefined = byContract[primaryContractId];
        if (existingSessionId) {
          const report = await getSessionTrace(existingSessionId);
          if (cancelled) return;
          setFindings(report.findings);
          setProposals(report.remediation_proposals);
          setSessionId(report.session_id);
          setLoading(false);
          setProgressStage("done");
          setProgressCompleted(report.findings.length);
          setProgressTotal(Math.max(report.findings.length, 1));
          setProgressMessage("Loaded persisted analysis.");
          return;
        }
        const sessions = await listSessions();
        const match = sessions.find((s) => s.contract_ids.includes(primaryContractId));
        if (match) {
          const report = await getSessionTrace(match.session_id);
          if (cancelled) return;
          setFindings(report.findings);
          setProposals(report.remediation_proposals);
          setSessionId(report.session_id);
          setLoading(false);
          setProgressStage("done");
          setProgressCompleted(report.findings.length);
          setProgressTotal(Math.max(report.findings.length, 1));
          setProgressMessage("Loaded persisted analysis.");
          try {
            const raw = sessionStorage.getItem(ANALYSIS_CACHE_KEY);
            const cache = raw ? JSON.parse(raw) : {};
            cache[cacheKey] = {
              findings: report.findings,
              proposals: report.remediation_proposals,
              sessionId: report.session_id,
              runStartedAt: new Date(report.generated_at).toISOString(),
              streamCount: report.findings.length,
            };
            sessionStorage.setItem(ANALYSIS_CACHE_KEY, JSON.stringify(cache));
            const rawByContract2 = sessionStorage.getItem(ANALYSIS_SESSION_BY_CONTRACT);
            const byContract2 = rawByContract2 ? JSON.parse(rawByContract2) : {};
            byContract2[primaryContractId] = report.session_id;
            sessionStorage.setItem(ANALYSIS_SESSION_BY_CONTRACT, JSON.stringify(byContract2));
          } catch {
            // ignore cache write failures
          }
          return;
        }
      } catch {
        // fallback to live stream
      }
      if (!cancelled) startStreaming();
    })();

    return () => {
      cancelled = true;
      abortRef.current?.abort();
      if (activeRunKeyRef.current === runKey) {
        activeRunKeyRef.current = null;
      }
    };
  }, [cacheKey, primaryContractId, vendorName]);

  const handleCitationClick = async (finding: ObligationFinding, contractId: string, page: number, quote: string) => {
    const resolvedContractId = contractId || primaryContractId;
    setActiveContractId(resolvedContractId);
    setActiveCitation({ contractId: resolvedContractId, page, quote });
    setPdfLoading(true);

    const fallbackPage = page > 0 ? page : 1;
    try {
      const resolved = await findTextPage(resolvedContractId, quote);
      const resolvedPage = resolved.page > 0 ? resolved.page : fallbackPage;
      setActivePage(resolvedPage);
      const allQuotes = finding.evidence_spans.map((s) => s.text);
      setHighlightedPdfUrl(buildMultiHighlightedPdfUrl(resolvedContractId, [quote, ...allQuotes], resolvedPage));
    } catch {
      setActivePage(fallbackPage);
      const allQuotes = finding.evidence_spans.map((s) => s.text);
      setHighlightedPdfUrl(buildMultiHighlightedPdfUrl(resolvedContractId, [quote, ...allQuotes], fallbackPage));
    }
  };

  const pdfSrc = highlightedPdfUrl
    ? highlightedPdfUrl
    : `/api/documents/${encodeURIComponent(activeContractId)}/pdf#page=${activePage}`;
  const totalDone = !loading;
  const progressPercent = progressTotal > 0 ? Math.min(100, Math.round((progressCompleted / progressTotal) * 100)) : 0;

  const handleGenerateCompliantPdf = async () => {
    if (!sessionId) return;
    setGeneratingCompliantPdf(true);
    try {
      const blob = await getCompliantDraftPdf(sessionId, vendorName);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dora_compliant_draft_${sessionId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setGeneratingCompliantPdf(false);
    }
  };

  return (
    <SaasShell
      title={`Investigation - ${vendorName}`}
      subtitle={`Live run on ${primaryContractId || "N/A"} (pipeline + RAG + LLM)`}
      topTabs={[
        { id: "findings", label: "Findings" },
        { id: "remediation", label: "Remediation" },
        { id: "audit", label: "Audit trail" },
      ]}
      activeTabId={tab}
      rightActions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/graph")}
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-700"
          >
            <ArrowRight size={12} />
            Graph
          </button>
          {sessionId && (
            <button
              onClick={handleGenerateCompliantPdf}
              disabled={generatingCompliantPdf}
              className="inline-flex items-center gap-2 rounded-md bg-blue-700 px-3 py-2 text-xs font-semibold text-white shadow-md shadow-blue-900/30 hover:bg-blue-600 disabled:opacity-60"
            >
              {generatingCompliantPdf ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Generate DORA-compliant PDF
            </button>
          )}
        </div>
      }
    >
      <div className="card-surface h-[calc(100vh-165px)] min-h-[620px] overflow-x-auto overflow-y-hidden">
        <section className="grid h-full min-w-[1100px] grid-cols-[1.2fr_1fr]">
          <div className="relative min-h-0 overflow-hidden border-r border-indigo-100 bg-slate-100/60">
            <div className="flex items-center justify-between border-b border-indigo-100 bg-white px-4 py-2">
              <div className="text-xs text-slate-600">
                Contract: <span className="font-medium text-slate-800">{activeContractId || "N/A"}</span>
              </div>
              <div className="text-xs text-slate-500">Page {activePage}</div>
            </div>
            {pdfLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-100">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Loader2 size={16} className="animate-spin text-indigo-600" />
                  Loading PDF evidence...
                </div>
              </div>
            )}
            {activeContractId ? (
              <object
                key={`${activeContractId}-${activePage}-${highlightedPdfUrl ?? "raw"}`}
                data={pdfSrc}
                type="application/pdf"
                className="h-full w-full"
                onLoad={() => setPdfLoading(false)}
              >
                <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-slate-600">
                  <FileText size={20} />
                  PDF preview not available in this browser.
                  <a className="text-indigo-600 underline" href={`/api/documents/${activeContractId}/pdf`} target="_blank" rel="noreferrer">
                    Open in new tab
                  </a>
                </div>
              </object>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">No contract selected.</div>
            )}
          </div>

          <aside className="flex min-h-0 h-full flex-col overflow-hidden bg-white">
            <div className="border-b border-indigo-100 px-4 py-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-xs uppercase tracking-wide text-slate-500">Non-conformity analysis (live)</p>
                <p className="text-xs text-slate-500">{findings.length} findings streamed</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-2">
                <div className="mb-1 flex items-center justify-between text-[11px] text-slate-600">
                  <span>
                    {progressStage === "analysis"
                      ? `Analysis (${progressCompleted}/${progressTotal})`
                      : progressStage === "remediation"
                        ? "Remediation + summary"
                        : "Completed"}
                  </span>
                  <span className="font-medium text-slate-700">{progressPercent}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-300",
                      progressStage === "done" ? "bg-emerald-500" : "bg-indigo-500"
                    )}
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-500">{progressMessage}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600">
                contract_id={primaryContractId || "N/A"} | run_started={runStartedAt || "N/A"} | events={streamCount}
              </div>
              <div className="mt-2 flex gap-2">
                {(["findings", "remediation", "audit"] as const).map((it) => (
                  <button
                    key={it}
                    onClick={() => setTab(it)}
                    className={cn(
                      "rounded-lg px-3 py-1.5 text-xs font-medium capitalize",
                      tab === it ? "bg-indigo-600 text-white" : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                    )}
                  >
                    {it}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
              {error && (
                <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-red-600">
                  <AlertTriangle size={20} />
                  <p className="text-sm">{error}</p>
                </div>
              )}

              {!error && loading && findings.length === 0 && (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
                  <Loader2 size={20} className="animate-spin text-indigo-600" />
                  <p className="text-sm text-slate-700">Running live compliance pipeline...</p>
                  <p className="text-xs text-slate-500">Stream source: /api/gap-analysis-stream (use_cache=false)</p>
                </div>
              )}

              {!error && (tab === "findings" || !totalDone) && (
                <div className="space-y-3">
                  {findings.map((finding) => (
                    <FindingItem
                      key={`${finding.obligation_id}-${finding.rationale.slice(0, 20)}`}
                      finding={finding}
                      onCitationClick={handleCitationClick}
                    />
                  ))}
                  {!loading && findings.length === 0 && (
                    <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
                      No findings were returned by the pipeline for this contract.
                    </div>
                  )}
                </div>
              )}

              {!error && tab === "remediation" && totalDone && (
                <div className="space-y-3">
                  {proposals.length === 0 && (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                      No remediation proposals generated for this run.
                    </div>
                  )}
                  {proposals.map((proposal) => (
                    <div key={proposal.obligation_id} className="rounded-lg border border-indigo-100 bg-slate-50 p-3">
                      <div className="mb-1 flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900">{proposal.summary}</p>
                        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium", riskBadgeClass(proposal.priority))}>
                          {proposal.priority}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed text-slate-600">{proposal.detail}</p>
                    </div>
                  ))}
                </div>
              )}

              {!error && tab === "audit" && (
                <div className="space-y-3">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                    <p>session_id: {sessionId ?? "(pending)"}</p>
                    <p>contract_id: {primaryContractId || "(none)"}</p>
                    <p>vendor: {vendorName}</p>
                    <p>stream_events_received: {streamCount}</p>
                    <p>status: {loading ? "running" : "completed"}</p>
                  </div>
                  <div className="space-y-2">
                    {findings.map((f) => (
                      <div key={`audit-${f.obligation_id}`} className="rounded-lg border border-slate-200 bg-white p-3 text-xs">
                        <p className="font-semibold text-slate-800">{f.obligation_id} - {f.verdict}</p>
                        <p className="mt-1 text-slate-600">{f.rationale}</p>
                        {f.gap_description ? <p className="mt-1 text-rose-700">{f.gap_description}</p> : null}
                      </div>
                    ))}
                    {!findings.length && <p className="text-xs text-slate-500">No AI statements yet.</p>}
                  </div>
                </div>
              )}
            </div>

            {activeCitation && (
              <div className="border-t border-indigo-100 bg-indigo-50 px-4 py-2 text-[11px] text-indigo-800">
                Citation on p.{activeCitation.page}: "{activeCitation.quote.slice(0, 170)}
                {activeCitation.quote.length > 170 ? "..." : ""}"
              </div>
            )}
          </aside>
        </section>
      </div>
    </SaasShell>
  );
}

export default function InvestigationPage() {
  return (
    <Suspense
      fallback={
        <main className="h-screen p-6">
          <div className="card-surface flex h-full items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 size={16} className="animate-spin text-indigo-600" />
              Loading investigation...
            </div>
          </div>
        </main>
      }
    >
      <InvestigationContent />
    </Suspense>
  );
}
