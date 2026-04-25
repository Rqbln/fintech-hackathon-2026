"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Globe, AlertTriangle } from "lucide-react";
import type { NodeAttributes, ReportArtifact } from "@/lib/types";
import { runGapAnalysis } from "@/lib/api";
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
  const [report, setReport] = useState<ReportArtifact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"findings" | "remediation">("findings");
  const [citation, setCitation] = useState<{ contractId: string; page: number; quote: string } | null>(null);

  const isOpen = !!nodeKey && nodeAttrs?.node_type === "Vendor";

  useEffect(() => {
    if (!isOpen || !nodeAttrs) return;
    setReport(null);
    setError(null);
    setTab("findings");
    setLoading(true);

    runGapAnalysis({
      contract_ids: contractIds.length ? contractIds : [nodeKey!],
      vendor_name: nodeAttrs.label,
      contract_text_preview: "",
    })
      .then((r) => { setReport(r); onSessionReady(r.session_id); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [nodeKey, nodeAttrs, contractIds]);

  const score = nodeAttrs?.criticality_score ?? 0;
  const riskColor = scoreToColor(score);
  const riskLabel = scoreToLabel(score);

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
                  {/* Risk indicator dot */}
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{
                      background: riskColor,
                      boxShadow: `0 0 8px ${riskColor}88`,
                    }}
                  />
                  <h2 className="text-base font-semibold text-slate-100 truncate">
                    {nodeAttrs?.label}
                  </h2>
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

            {/* Tab bar */}
            {report && (
              <div className="flex gap-1 mt-4">
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
                    {t === "findings" && report && (
                      <span className="ml-1.5 opacity-60">{report.findings.length}</span>
                    )}
                    {t === "remediation" && report && (
                      <span className="ml-1.5 opacity-60">{report.remediation_proposals.length}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {loading && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                <Loader2 size={24} className="animate-spin text-indigo-400" />
                <p className="text-sm">Running DORA gap analysis…</p>
                <p className="text-xs text-slate-600">Evaluating 12 obligations</p>
              </div>
            )}

            {error && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-red-400">
                <AlertTriangle size={22} />
                <p className="text-sm text-center">{error}</p>
              </div>
            )}

            {report && tab === "findings" && (
              <div className="space-y-4">
                {/* Summary pills */}
                <div className="flex gap-2 flex-wrap">
                  <span className="text-xs px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full">
                    ✅ {report.obligations_met} met
                  </span>
                  <span className="text-xs px-2 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-full">
                    ⚠️ {report.obligations_partial} partial
                  </span>
                  <span className="text-xs px-2 py-1 bg-red-500/10 border border-red-500/20 text-red-400 rounded-full">
                    ❌ {report.obligations_unmet} unmet
                  </span>
                </div>

                {/* Executive summary */}
                {report.executive_summary && (
                  <div className="bg-slate-800/60 rounded-lg p-3 border border-slate-700/60">
                    <p className="text-[11px] text-slate-400 uppercase tracking-wider mb-1.5 font-semibold">AI Summary</p>
                    <p className="text-xs text-slate-300 leading-relaxed">{report.executive_summary}</p>
                  </div>
                )}

                {/* Findings */}
                <div className="space-y-3">
                  {report.findings.map((f) => (
                    <FindingCard
                      key={f.obligation_id}
                      finding={f}
                      onCitationClick={(cId, pg, quote) => setCitation({ contractId: cId, page: pg, quote })}
                    />
                  ))}
                </div>
              </div>
            )}

            {report && tab === "remediation" && (
              <div className="space-y-4">
                {report.remediation_proposals.length === 0 ? (
                  <div className="text-center text-slate-500 text-sm pt-8">
                    No remediation needed — all obligations met.
                  </div>
                ) : (
                  report.remediation_proposals.map((p) => (
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
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 font-semibold">
                            EU-Sovereign alternatives
                          </p>
                          <div className="space-y-1.5">
                            {p.sovereign_alternatives.slice(0, 3).map((alt) => (
                              <div
                                key={alt.name}
                                className="flex items-center justify-between px-3 py-2 bg-slate-800/60 rounded-lg border border-slate-700/40"
                              >
                                <div>
                                  <span className="text-xs font-medium text-slate-200">{alt.name}</span>
                                  <span className="text-[10px] text-slate-500 ml-1.5">{alt.hq_country}</span>
                                  {alt.eu_sovereign && (
                                    <span className="ml-1.5 text-[10px] text-emerald-400 font-medium">EU ✓</span>
                                  )}
                                  {alt.certification && (
                                    <span className="ml-1 text-[10px] text-indigo-400">{alt.certification}</span>
                                  )}
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

    {/* CitationModal lives outside AnimatePresence — it owns its own AnimatePresence
        internally, and nesting them causes Framer Motion duplicate-key warnings. */}
    <CitationModal
      contractId={citation?.contractId ?? null}
      page={citation?.page ?? 1}
      quote={citation?.quote ?? ""}
      onClose={() => setCitation(null)}
    />
    </>
  );
}
