"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Download,
  Filter,
  FileText,
  Loader2,
  Search,
  ShieldAlert,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ObligationFinding, RemediationProposal } from "@/lib/types";
import { buildHighlightedPdfUrl, findTextPage, getReportMarkdown, streamGapAnalysis } from "@/lib/api";
import { cn, riskBadgeClass, scoreToLabel } from "@/lib/utils";
import FindingCard from "@/components/graph/FindingCard";
import SaasShell from "@/components/shell/SaasShell";

type ViewTab = "findings" | "remediation";

interface CitationTarget {
  contractId: string;
  page: number;
  quote: string;
}

function InvestigationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const vendorKey = searchParams.get("vendorKey") ?? "";
  const vendorName = searchParams.get("vendorName") ?? "Selected Vendor";
  const vendorCountry = searchParams.get("country") ?? "";
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
  const [execSummary, setExecSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationTarget | null>(null);
  const [activeContractId, setActiveContractId] = useState<string>(primaryContractId);
  const [activePage, setActivePage] = useState(1);
  const [highlightedPdfUrl, setHighlightedPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setActiveContractId(primaryContractId);
    setHighlightedPdfUrl(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [primaryContractId]);

  useEffect(() => {
    if (!vendorName || !primaryContractId) return;
    setLoading(true);
    setError(null);
    setFindings([]);
    setProposals([]);
    setExecSummary("");
    setSessionId(null);
    setActiveCitation(null);

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
        if (event.type === "finding") {
          setFindings((prev) => [...prev, event.data]);
          return;
        }
        if (event.type === "done") {
          setProposals(event.report.remediation_proposals);
          setExecSummary(event.report.executive_summary);
          setSessionId(event.report.session_id);
          setLoading(false);
          return;
        }
        if (event.type === "error") {
          setError(event.message);
          setLoading(false);
        }
      },
      ctrl.signal
    ).catch((e: Error) => {
      if (e.name !== "AbortError") {
        setError(e.message);
        setLoading(false);
      }
    });

    return () => ctrl.abort();
  }, [primaryContractId, vendorName]);

  const handleCitationClick = async (contractId: string, page: number, quote: string) => {
    const resolvedContractId = contractId || primaryContractId;
    setActiveContractId(resolvedContractId);
    setActiveCitation({ contractId: resolvedContractId, page, quote });
    setPdfLoading(true);

    const fallbackPage = page > 0 ? page : 1;
    try {
      const resolved = await findTextPage(resolvedContractId, quote);
      const resolvedPage = resolved.page > 0 ? resolved.page : fallbackPage;
      setActivePage(resolvedPage);
      setHighlightedPdfUrl(buildHighlightedPdfUrl(resolvedContractId, quote, resolvedPage));
    } catch {
      setActivePage(fallbackPage);
      setHighlightedPdfUrl(buildHighlightedPdfUrl(resolvedContractId, quote, fallbackPage));
    }
  };

  const pdfSrc = highlightedPdfUrl
    ? highlightedPdfUrl
    : `/api/documents/${encodeURIComponent(activeContractId)}/pdf#page=${activePage}`;
  const totalDone = findings.length >= 12 || (!loading && findings.length > 0);
  const riskLabel = scoreToLabel(Number(searchParams.get("score") ?? "0"));

  const handleExportMarkdown = async () => {
    if (!sessionId) return;
    setExporting(true);
    try {
      const md = await getReportMarkdown(sessionId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `regagent_report_${sessionId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <SaasShell
      title={`Investigation - ${vendorName}`}
      subtitle="Split-screen legal evidence and compliance findings"
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
              onClick={handleExportMarkdown}
              disabled={exporting}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              {exporting ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
              Export report
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
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-xs uppercase tracking-wide text-slate-500">Non-conformity analysis</p>
                <p className="text-xs text-slate-500">{findings.length}/12 obligations</p>
              </div>
              <div className="mb-3 flex items-center gap-2">
                <div className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500">
                  <Search size={12} />
                  Search finding
                </div>
                <div className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500">
                  <Filter size={12} />
                  Severity
                </div>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-indigo-100">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${Math.min(100, (findings.length / 12) * 100)}%` }}
                />
              </div>
              {totalDone && (
                <div className="mt-3 flex gap-2">
                  {(["findings", "remediation"] as const).map((it) => (
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
              )}
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
                  <p className="text-sm text-slate-700">Evaluating contractual obligations...</p>
                  <p className="text-xs text-slate-500">Findings will stream live into this panel.</p>
                </div>
              )}

              {!error && (tab === "findings" || !totalDone) && (
                <div className="space-y-3">
                  {execSummary && (
                    <div className="rounded-lg border border-indigo-100 bg-indigo-50/70 p-3">
                      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-700">Executive summary</p>
                      <div className="prose prose-sm max-w-none text-slate-700">
                        <ReactMarkdown>{execSummary}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  {findings.map((finding) => (
                    <FindingCard key={finding.obligation_id} finding={finding} onCitationClick={handleCitationClick} />
                  ))}
                </div>
              )}

              {!error && tab === "remediation" && totalDone && (
                <div className="space-y-3">
                  {proposals.length === 0 && (
                    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                      <ShieldAlert size={16} />
                      No remediation required for the selected scope.
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
