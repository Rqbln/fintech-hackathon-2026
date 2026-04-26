"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { ArrowLeft, Download, RefreshCw, Loader2, LayoutList } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import type { GraphResponse, NodeAttributes, GraphEdge } from "@/lib/types";
import { getGraph, getReportMarkdown } from "@/lib/api";
import VendorPanel from "@/components/graph/VendorPanel";
import PortfolioPanel from "@/components/graph/PortfolioPanel";
import { scoreToLabel, cn } from "@/lib/utils";

// Sigma must be client-only (WebGL)
const GraphCanvas = dynamic(() => import("@/components/graph/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-slate-500 gap-3">
      <Loader2 size={20} className="animate-spin" />
      <span className="text-sm">Initialising graph…</span>
    </div>
  ),
});

interface StoredContract {
  contractId: string;
  vendorName?: string;
  score?: number;
}

// Find contract IDs for a given vendor node by traversing edges
function getVendorContracts(vendorKey: string, edges: GraphEdge[]): string[] {
  return edges
    .filter((e) => e.attributes.label === "COVERS" && e.target === vendorKey)
    .map((e) => e.source);
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedAttrs, setSelectedAttrs] = useState<NodeAttributes | null>(null);
  const [vendorContracts, setVendorContracts] = useState<string[]>([]);
  const [exportLoading, setExportLoading] = useState(false);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [complianceColors, setComplianceColors] = useState<Record<string, string>>(() => {
    try {
      return JSON.parse(localStorage.getItem("dora_compliance_colors") ?? "{}");
    } catch { return {}; }
  });

  const handleComplianceReady = useCallback((vendorKey: string, color: string) => {
    setComplianceColors((prev) => {
      const next = { ...prev, [vendorKey]: color };
      localStorage.setItem("dora_compliance_colors", JSON.stringify(next));
      return next;
    });
  }, []);

  // Load graph on mount
  useEffect(() => {
    getGraph()
      .then(setGraphData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleNodeClick = useCallback(
    (key: string, attrs: NodeAttributes) => {
      if (attrs.node_type !== "Vendor") return;
      setSelectedNode(key);
      setSelectedAttrs(attrs);
      if (graphData) {
        const contracts = getVendorContracts(key, graphData.edges);
        // Also check sessionStorage for ingested contract IDs
        let stored: StoredContract[] = [];
        try {
          stored = JSON.parse(sessionStorage.getItem("dora_contracts") ?? "[]");
        } catch { /* ignore */ }
        const storedIds = stored.map((s) => s.contractId);
        const allIds = Array.from(new Set([...contracts, ...storedIds]));
        setVendorContracts(allIds);
      }
    },
    [graphData]
  );

  const handleClosePanel = useCallback(() => {
    setSelectedNode(null);
    setSelectedAttrs(null);
    setVendorContracts([]);
  }, []);

  const handlePortfolioVendorClick = useCallback(
    (key: string, attrs: NodeAttributes) => {
      setShowPortfolio(false);
      handleNodeClick(key, attrs);
    },
    [handleNodeClick]
  );

  const handleRefreshGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getGraph();
      setGraphData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to reload");
    } finally {
      setLoading(false);
    }
  };

  const handleExportMarkdown = async () => {
    if (!lastSessionId) return;
    setExportLoading(true);
    try {
      const md = await getReportMarkdown(lastSessionId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `DORA_report_${lastSessionId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // silently fail
    } finally {
      setExportLoading(false);
    }
  };

  // Compute overall risk level from graph
  const overallRisk = graphData
    ? (() => {
        const vendors = graphData.nodes.filter(
          (n) => n.attributes.node_type === "Vendor"
        );
        const maxScore = Math.max(
          0,
          ...vendors.map((n) => n.attributes.criticality_score ?? 0)
        );
        return scoreToLabel(maxScore);
      })()
    : null;

  const riskColorClass =
    overallRisk === "Critical"
      ? "text-red-600 bg-red-50 border-red-200"
      : overallRisk === "High"
      ? "text-amber-600 bg-amber-50 border-amber-200"
      : "text-indigo-600 bg-indigo-50 border-indigo-200";

  return (
    <div className="dot-bg h-screen flex flex-col overflow-hidden">
      {/* Navbar */}
      <nav className="shrink-0 flex items-center justify-between px-5 py-3 bg-white backdrop-blur border-b border-slate-200 z-10">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-900 transition-colors text-sm"
          >
            <ArrowLeft size={15} />
            <span>Upload</span>
          </Link>
          <span className="text-slate-300">·</span>
          <span className="text-sm font-semibold text-slate-900">DORA Risk Graph</span>
          {overallRisk && (
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full border font-medium",
                riskColorClass
              )}
            >
              {overallRisk} Risk
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {graphData && (
            <button
              onClick={() => setShowPortfolio((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors",
                showPortfolio
                  ? "bg-indigo-600 text-white"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
              )}
            >
              <LayoutList size={13} />
              Portfolio
            </button>
          )}
          <button
            onClick={handleRefreshGraph}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          {lastSessionId && (
            <button
              onClick={handleExportMarkdown}
              disabled={exportLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-40"
            >
              {exportLoading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
              ECB Report
            </button>
          )}
        </div>
      </nav>

      {/* Main area */}
      <div className="flex-1 relative overflow-hidden bg-white">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="flex flex-col items-center gap-3 text-slate-500">
              <Loader2 size={28} className="animate-spin text-indigo-600" />
              <p className="text-sm">Loading dependency graph…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center text-red-600 text-sm">
              <p className="font-medium mb-1">Failed to load graph</p>
              <p className="text-slate-500 text-xs">{error}</p>
              <button
                onClick={handleRefreshGraph}
                className="mt-3 text-xs text-indigo-600 hover:underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Graph canvas — dims when panel is open */}
        {graphData && (
          <motion.div
            className="absolute inset-0"
            animate={{ opacity: selectedNode ? 0.45 : 1 }}
            transition={{ duration: 0.25 }}
          >
            <GraphCanvas
              data={graphData}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
              complianceColors={complianceColors}
            />
          </motion.div>
        )}

        {/* Legend */}
        {graphData && !selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-5 left-5 flex flex-col gap-1.5 bg-white border border-slate-200 shadow-sm rounded-xl px-4 py-3"
          >
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
              Nodes
            </p>
            {[
              { color: "#0f172a", label: "Your bank" },
              { color: "#ef4444", label: "Critical risk" },
              { color: "#f59e0b", label: "High risk" },
              { color: "#2563eb", label: "Vendor (unanalysed)" },
              { color: "#dc2626", label: "Non-compliant" },
              { color: "#d97706", label: "Partially compliant" },
              { color: "#059669", label: "Compliant" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: color }}
                />
                <span className="text-xs text-slate-700">{label}</span>
              </div>
            ))}
            <p className="text-[10px] text-slate-500 mt-1.5">Click a vendor to analyse</p>
          </motion.div>
        )}

        {/* Portfolio panel */}
        {graphData && showPortfolio && (
          <PortfolioPanel
            nodes={graphData.nodes}
            onVendorClick={handlePortfolioVendorClick}
            onClose={() => setShowPortfolio(false)}
          />
        )}

        {/* Vendor panel */}
        {graphData && (
          <VendorPanel
            nodeKey={selectedNode}
            nodeAttrs={selectedAttrs}
            contractIds={vendorContracts}
            onClose={handleClosePanel}
            onSessionReady={setLastSessionId}
            onComplianceReady={handleComplianceReady}
          />
        )}
      </div>
    </div>
  );
}
