"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Globe, Zap, AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { NodeAttributes, ObligationFinding, RemediationProposal } from "@/lib/types";
import { streamGapAnalysis } from "@/lib/api";
import { scoreToColor, scoreToLabel, riskBadgeClass, cn } from "@/lib/utils";
import FindingCard from "./FindingCard";
import CitationModal from "./CitationModal";

interface Props {
  nodeKey: string | null;
  nodeAttrs: NodeAttributes | null;
  contractIds: string[];
  onClose: () => void;
  onSessionReady: (sessionId: string) => void;
  onComplianceReady?: (vendorKey: string, color: string) => void;
}

export default function VendorPanel({ nodeKey, nodeAttrs, contractIds, onClose, onSessionReady, onComplianceReady }: Props) {
  const [findings, setFindings] = useState<ObligationFinding[]>([]);
  const [proposals, setProposals] = useState<RemediationProposal[]>([]);
  const [execSummary, setExecSummary] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);
  const [cached, setCached] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"findings" | "remediation">("findings");
  const [citation, setCitation] = useState<{ contractId: string; page: number; quote: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const isOpen = !!nodeKey && nodeAttrs?.node_type === "Vendor";

  useEffect(() => {
    if (!isOpen || !nodeAttrs) return;

    setFindings([]);
    setProposals([]);
    setExecSummary("");
    setError(null);
    setDone(false);
    setCached(false);
    setTab("findings");
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const ids = contractIds.length ? contractIds : [nodeKey!];

    const run = async () => {
      let contractText = "";
      try {
        const r = await fetch(`/api/contracts/${ids[0]}/preview`, { signal: ctrl.signal });
        if (r.ok) {
          const d = await r.json() as { text: string };
          contractText = d.text ?? "";
        }
      } catch { /* proceed without text */ }

      await streamGapAnalysis(
        { contract_ids: ids, vendor_name: nodeAttrs.label, contract_text_preview: contractText },
        (event) => {
          if (event.type === "finding") {
            setFindings((prev) => [...prev, event.data]);
          } else if (event.type === "done") {
            setProposals(event.report.remediation_proposals);
            setExecSummary(event.report.executive_summary);
            onSessionReady(event.report.session_id);
            setDone(true);
            setStreaming(false);
            if (onComplianceReady && nodeKey) {
              const fs = event.report.findings;
              const metCount = fs.filter((f) => f.verdict === "met").length;
              const ratio = fs.length > 0 ? metCount / fs.length : 0;
              const color = ratio >= 0.6 ? "#059669" : ratio >= 0.3 ? "#d97706" : "#dc2626";
              onComplianceReady(nodeKey, color);
            }
          } else if (event.type === "error") {
            setError(event.message);
            setStreaming(false);
          }
        },
        ctrl.signal,
        () => setCached(true),
      );
    };

    run().catch((e: Error) => {
      if (e.name !== "AbortError") setError(e.message);
      setStreaming(false);
    });

    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeKey, nodeAttrs, contractIds]);

  const score = nodeAttrs?.criticality_score ?? 0;
  const riskColor = scoreToColor(score);
  const riskLabel = scoreToLabel(score);

  const met = findings.filter((f) => f.verdict === "met").length;
  const partial = findings.filter((f) => f.verdict === "partially_met").length;
  const unmet = findings.filter((f) => f.verdict === "unmet").length;

  return (
    <>
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="absolute top-0 right-0 h-full w-[480px] flex flex-col bg-white border-l border-slate-200 shadow-2xl z-20 overflow-hidden"
        >
          {/* ── Header ── */}
          <div className="px-6 pt-6 pb-5 border-b border-slate-100 shrink-0">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2.5 mb-1.5">
                  <div
                    className="w-3.5 h-3.5 rounded-full shrink-0"
                    style={{ background: riskColor, boxShadow: `0 0 8px ${riskColor}66` }}
                  />
                  <h2 className="text-lg font-semibold text-slate-900 truncate leading-tight">
                    {nodeAttrs?.label}
                  </h2>
                  {cached && (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-medium shrink-0">
                      <Zap size={9} /> cached
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  {nodeAttrs?.country && (
                    <span className="flex items-center gap-1 text-sm text-slate-500">
                      <Globe size={12} />
                      {nodeAttrs.country}
                    </span>
                  )}
                  <span className={cn("px-2 py-0.5 rounded-md border text-xs font-semibold tabular", riskBadgeClass(riskLabel.toLowerCase()))}>
                    {riskLabel} · {(score * 100).toFixed(0)}%
                  </span>
                  {contractIds.length > 0 && (
                    <span className="text-xs text-slate-400">
                      {contractIds.length} contract{contractIds.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors shrink-0"
              >
                <X size={18} />
              </button>
            </div>

            {/* Progress */}
            {streaming && (
              <div className="mt-1">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
                  <span className="flex items-center gap-1.5">
                    <Loader2 size={11} className="animate-spin" />
                    Evaluating DORA obligations…
                  </span>
                  <span className="tabular font-medium">{findings.length} / 12</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-indigo-500 rounded-full"
                    animate={{ width: `${(findings.length / 12) * 100}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}

            {/* Verdict summary pills */}
            {findings.length > 0 && (
              <div className="flex gap-2 mt-4">
                <span className="flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-full">
                  ✅ <span className="tabular">{met}</span> met
                </span>
                <span className="flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded-full">
                  ⚠️ <span className="tabular">{partial}</span> partial
                </span>
                <span className="flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-red-50 border border-red-200 text-red-700 rounded-full">
                  ❌ <span className="tabular">{unmet}</span> unmet
                </span>
              </div>
            )}

            {/* Tabs */}
            {findings.length > 0 && done && (
              <div className="flex border-b border-slate-100 -mx-6 px-6 mt-4 gap-0">
                {(["findings", "remediation"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={cn(
                      "pb-3 px-1 mr-6 text-sm font-medium border-b-2 transition-colors capitalize",
                      tab === t
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-slate-400 hover:text-slate-700"
                    )}
                  >
                    {t}
                    <span className="ml-1.5 text-xs tabular opacity-60">
                      {t === "findings" ? findings.length : proposals.length}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ── Body ── */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {error && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-red-600">
                <AlertTriangle size={24} />
                <p className="text-sm text-center">{error}</p>
              </div>
            )}

            {/* Findings */}
            {(tab === "findings" || !done) && findings.length > 0 && (
              <div className="space-y-1">
                {execSummary && (
                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 mb-5">
                    <p className="text-[11px] text-slate-400 uppercase tracking-widest mb-2.5 font-semibold">AI Summary</p>
                    <div className="text-sm text-slate-700 leading-relaxed prose prose-slate prose-sm max-w-none
                      [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:space-y-1.5
                      [&_li]:text-slate-600
                      [&_strong]:text-slate-900 [&_strong]:font-semibold
                      [&_p]:mb-2 [&_p:last-child]:mb-0">
                      <ReactMarkdown>{execSummary}</ReactMarkdown>
                    </div>
                  </div>
                )}
                <div className="space-y-4">
                  {findings.map((f) => (
                    <motion.div
                      key={f.obligation_id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <FindingCard
                        finding={f}
                        onCitationClick={(cId, pg, quote) => setCitation({ contractId: cId, page: pg, quote })}
                      />
                    </motion.div>
                  ))}
                </div>
                {streaming && (
                  <div className="flex items-center gap-2 text-slate-400 text-xs py-3">
                    <Loader2 size={11} className="animate-spin" />
                    <span>More findings arriving…</span>
                  </div>
                )}
              </div>
            )}

            {/* Empty loading state */}
            {findings.length === 0 && streaming && (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
                <Loader2 size={28} className="animate-spin text-indigo-500" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-700">Running DORA gap analysis</p>
                  <p className="text-xs text-slate-400 mt-1">Evaluating 12 obligations in parallel</p>
                </div>
              </div>
            )}

            {/* Remediation */}
            {tab === "remediation" && done && (
              <div className="space-y-4">
                {proposals.length === 0 ? (
                  <div className="text-center text-slate-500 text-sm pt-12">
                    No remediation needed — all obligations met.
                  </div>
                ) : (
                  proposals.map((p) => (
                    <div key={p.obligation_id} className="border border-slate-200 rounded-xl p-5 bg-slate-50 space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900 leading-snug">{p.summary}</p>
                        <span className={cn("text-[11px] px-2 py-0.5 rounded border font-semibold shrink-0", riskBadgeClass(p.priority))}>
                          {p.priority}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed">{p.detail}</p>
                      {p.sovereign_alternatives.length > 0 && (
                        <div className="pt-1">
                          <p className="text-[11px] text-slate-400 uppercase tracking-widest mb-2.5 font-semibold">EU-Sovereign alternatives</p>
                          <div className="space-y-2">
                            {p.sovereign_alternatives.slice(0, 3).map((alt) => (
                              <div key={alt.name} className="flex items-center justify-between px-3.5 py-2.5 bg-white rounded-lg border border-slate-200">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-sm font-semibold text-slate-900">{alt.name}</span>
                                  <span className="text-xs text-slate-500">{alt.hq_country}</span>
                                  {alt.eu_sovereign && <span className="text-xs text-emerald-600 font-medium">EU ✓</span>}
                                  {alt.certification && <span className="text-xs text-indigo-600">{alt.certification}</span>}
                                </div>
                                <span className="text-xs text-slate-500 tabular shrink-0 ml-2">{alt.cost_delta}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>

    <CitationModal
      contractId={citation?.contractId ?? null}
      page={citation?.page ?? 1}
      quote={citation?.quote ?? ""}
      onClose={() => setCitation(null)}
    />
    </>
  );
}
