"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Globe, AlertTriangle, Zap } from "lucide-react";
import type { NodeAttributes, ObligationFinding, RemediationProposal, ReportArtifact } from "@/lib/types";
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
}

export default function VendorPanel({ nodeKey, nodeAttrs, contractIds, onClose, onSessionReady }: Props) {
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

    // Reset state
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

    streamGapAnalysis(
      {
        contract_ids: contractIds.length ? contractIds : [nodeKey!],
        vendor_name: nodeAttrs.label,
        contract_text_preview: "",
      },
      (event) => {
        if (event.type === "finding") {
          setFindings((prev) => [...prev, event.data]);
        } else if (event.type === "done") {
          setProposals(event.report.remediation_proposals);
          setExecSummary(event.report.executive_summary);
          onSessionReady(event.report.session_id);
          setDone(true);
          setStreaming(false);
        } else if (event.type === "error") {
          setError(event.message);
          setStreaming(false);
        }
      },
      ctrl.signal
    )
      .catch((e: Error) => {
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
          transition={{ type: "spring", stiffness: 340, damping: 32 }}
          className="absolute top-0 right-0 h-full w-[420px] flex flex-col bg-[#0d1424]/95 backdrop-blur-sm border-l border-slate-700/60 z-20 overflow-hidden"
        >
          {/* Header */}
          <div className="px-5 pt-5 pb-4 border-b border-slate-700/60 shrink-0">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ background: riskColor, boxShadow: `0 0 8px ${riskColor}88` }}
                  />
                  <h2 className="text-base font-semibold text-slate-100 truncate">
                    {nodeAttrs?.label}
                  </h2>
                  {cached && (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-full">
                      <Zap size={8} /> cached
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {nodeAttrs?.country && (
                    <span className="flex items-center gap-1">
                      <Globe size={11} />
                      {nodeAttrs.country}
                    </span>
                  )}
                  <span className={cn("px-1.5 py-0.5 rounded border text-[10px] font-medium", riskBadgeClass(riskLabel.toLowerCase()))}>
                    {riskLabel} · {(score * 100).toFixed(0)}%
                  </span>
                  {contractIds.length > 0 && (
                    <span>{contractIds.length} contract{contractIds.length > 1 ? "s" : ""}</span>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors ml-2 shrink-0"
              >
                <X size={16} />
              </button>
            </div>

            {/* Progress bar while streaming */}
            {streaming && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                  <span className="flex items-center gap-1.5">
                    <Loader2 size={10} className="animate-spin" />
                    Evaluating obligations…
                  </span>
                  <span>{findings.length}/12</span>
                </div>
                <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-indigo-500 rounded-full"
                    animate={{ width: `${(findings.length / 12) * 100}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}

            {/* Summary pills — appear as findings stream in */}
            {findings.length > 0 && (
              <div className="flex gap-2 flex-wrap mt-3">
                <span className="text-xs px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full">
                  ✅ {met}
                </span>
                <span className="text-xs px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-full">
                  ⚠️ {partial}
                </span>
                <span className="text-xs px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-full">
                  ❌ {unmet}
                </span>
              </div>
            )}

            {/* Tab bar — show once we have findings */}
            {findings.length > 0 && done && (
              <div className="flex gap-1 mt-3">
                {(["findings", "remediation"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize",
                      tab === t
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
                    )}
                  >
                    {t}
                    <span className="ml-1.5 opacity-60">
                      {t === "findings" ? findings.length : proposals.length}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {error && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-red-400">
                <AlertTriangle size={22} />
                <p className="text-sm text-center">{error}</p>
              </div>
            )}

            {/* Findings — stream in one by one */}
            {(tab === "findings" || !done) && findings.length > 0 && (
              <div className="space-y-3">
                {execSummary && (
                  <div className="bg-slate-800/60 rounded-lg p-3 border border-slate-700/60 mb-4">
                    <p className="text-[11px] text-slate-400 uppercase tracking-wider mb-1.5 font-semibold">AI Summary</p>
                    <p className="text-xs text-slate-300 leading-relaxed">{execSummary}</p>
                  </div>
                )}
                {findings.map((f) => (
                  <motion.div
                    key={f.obligation_id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <FindingCard
                      finding={f}
                      onCitationClick={(cId, pg, quote) => setCitation({ contractId: cId, page: pg, quote })}
                    />
                  </motion.div>
                ))}
                {streaming && (
                  <div className="flex items-center gap-2 text-slate-600 text-xs py-2">
                    <Loader2 size={11} className="animate-spin" />
                    <span>More findings arriving…</span>
                  </div>
                )}
              </div>
            )}

            {/* Empty state while first finding loads */}
            {findings.length === 0 && streaming && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                <Loader2 size={24} className="animate-spin text-indigo-400" />
                <p className="text-sm">Running DORA gap analysis…</p>
                <p className="text-xs text-slate-600">Evaluating 12 obligations in parallel</p>
              </div>
            )}

            {/* Remediation tab */}
            {tab === "remediation" && done && (
              <div className="space-y-4">
                {proposals.length === 0 ? (
                  <div className="text-center text-slate-500 text-sm pt-8">
                    No remediation needed — all obligations met.
                  </div>
                ) : (
                  proposals.map((p) => (
                    <div
                      key={p.obligation_id}
                      className="border border-slate-700/60 rounded-xl p-4 bg-slate-900/40 space-y-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-semibold text-slate-200">{p.summary}</p>
                        <span className={cn("text-[10px] px-1.5 py-0.5 rounded border font-medium shrink-0", riskBadgeClass(p.priority))}>
                          {p.priority}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">{p.detail}</p>
                      {p.sovereign_alternatives.length > 0 && (
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 font-semibold">EU-Sovereign alternatives</p>
                          <div className="space-y-1.5">
                            {p.sovereign_alternatives.slice(0, 3).map((alt) => (
                              <div
                                key={alt.name}
                                className="flex items-center justify-between px-3 py-2 bg-slate-800/60 rounded-lg border border-slate-700/40"
                              >
                                <div>
                                  <span className="text-xs font-medium text-slate-200">{alt.name}</span>
                                  <span className="text-[10px] text-slate-500 ml-1.5">{alt.hq_country}</span>
                                  {alt.eu_sovereign && <span className="ml-1.5 text-[10px] text-emerald-400 font-medium">EU ✓</span>}
                                  {alt.certification && <span className="ml-1 text-[10px] text-indigo-400">{alt.certification}</span>}
                                </div>
                                <span className="text-[10px] text-slate-500">{alt.cost_delta}</span>
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
