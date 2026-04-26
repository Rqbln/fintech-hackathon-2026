"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Globe, AlertTriangle, ShieldCheck, Building2 } from "lucide-react";
import type { GraphNode, NodeAttributes } from "@/lib/types";
import { scoreToColor, scoreToLabel, riskBadgeClass, cn } from "@/lib/utils";

interface Props {
  nodes: GraphNode[];
  onVendorClick: (key: string, attrs: NodeAttributes) => void;
  onClose: () => void;
}

const EU_CODES = new Set([
  "AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR","HR","HU",
  "IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK",
  "IS","LI","NO","CH","GB",
]);

function isEU(country: string | null): boolean {
  if (!country) return false;
  return EU_CODES.has(country.trim().toUpperCase().slice(0, 2));
}

export default function PortfolioPanel({ nodes, onVendorClick, onClose }: Props) {
  const vendors = nodes
    .filter((n) => n.attributes.node_type === "Vendor")
    .sort((a, b) => (b.attributes.criticality_score ?? 0) - (a.attributes.criticality_score ?? 0));

  const critical = vendors.filter((v) => (v.attributes.criticality_score ?? 0) >= 0.7).length;
  const euBased = vendors.filter((v) => isEU(v.attributes.country)).length;
  const avgScore =
    vendors.length > 0
      ? vendors.reduce((s, v) => s + (v.attributes.criticality_score ?? 0), 0) / vendors.length
      : 0;

  return (
    <AnimatePresence>
      <motion.div
        key="portfolio-panel"
        initial={{ x: "-100%", opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: "-100%", opacity: 0 }}
        transition={{ type: "spring", stiffness: 340, damping: 32 }}
        className="absolute top-0 left-0 h-full w-[360px] flex flex-col bg-[#0d1424]/95 backdrop-blur-sm border-r border-slate-700/60 z-20 overflow-hidden"
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-4 border-b border-slate-700/60 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Building2 size={15} className="text-indigo-400" />
              <h2 className="text-sm font-semibold text-slate-100">ICT Risk Portfolio</h2>
              <span className="text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded-full">
                {vendors.length} vendor{vendors.length !== 1 ? "s" : ""}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X size={15} />
            </button>
          </div>

          {/* Aggregate stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-800/60 rounded-lg p-2.5 text-center border border-slate-700/40">
              <p className="text-lg font-bold text-red-400">{critical}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">Critical</p>
            </div>
            <div className="bg-slate-800/60 rounded-lg p-2.5 text-center border border-slate-700/40">
              <p className="text-lg font-bold text-emerald-400">{euBased}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">EU-based</p>
            </div>
            <div className="bg-slate-800/60 rounded-lg p-2.5 text-center border border-slate-700/40">
              <p className="text-lg font-bold" style={{ color: scoreToColor(avgScore) }}>
                {(avgScore * 100).toFixed(0)}%
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Avg risk</p>
            </div>
          </div>
        </div>

        {/* Vendor list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {vendors.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
              <Building2 size={28} />
              <p className="text-sm text-center">No vendors yet.<br />Upload a contract to start.</p>
            </div>
          )}
          {vendors.map((node) => {
            const score = node.attributes.criticality_score ?? 0;
            const riskColor = scoreToColor(score);
            const riskLabel = scoreToLabel(score);
            const eu = isEU(node.attributes.country);

            return (
              <button
                key={node.key}
                onClick={() => onVendorClick(node.key, node.attributes)}
                className="w-full text-left bg-slate-900/50 hover:bg-slate-800/60 border border-slate-700/40 hover:border-slate-600/60 rounded-xl px-3.5 py-3 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  {/* Risk dot */}
                  <div
                    className="w-2.5 h-2.5 rounded-full mt-1 shrink-0"
                    style={{ background: riskColor, boxShadow: `0 0 6px ${riskColor}66` }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-slate-200 truncate group-hover:text-white transition-colors">
                        {node.attributes.label}
                      </p>
                      <span className={cn("text-[10px] px-1.5 py-0.5 rounded border font-medium shrink-0", riskBadgeClass(riskLabel.toLowerCase()))}>
                        {riskLabel}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      {node.attributes.country && (
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <Globe size={9} />
                          {node.attributes.country}
                        </span>
                      )}
                      {eu ? (
                        <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                          <ShieldCheck size={9} />
                          EU
                        </span>
                      ) : node.attributes.country ? (
                        <span className="flex items-center gap-1 text-[10px] text-amber-400">
                          <AlertTriangle size={9} />
                          Non-EU
                        </span>
                      ) : null}
                    </div>

                    {/* Score bar */}
                    <div className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${score * 100}%`, background: riskColor }}
                      />
                    </div>
                    <p className="text-[10px] text-slate-600 mt-0.5">
                      {(score * 100).toFixed(0)}% criticality · click to analyse
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
