"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { ArrowLeft, Download, RefreshCw, Loader2 } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import type { GraphResponse, NodeAttributes, GraphEdge } from "@/lib/types";
import { getGraph, getReportMarkdown } from "@/lib/api";
import VendorPanel from "@/components/graph/VendorPanel";
import { scoreToColor, scoreToLabel, cn } from "@/lib/utils";

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
      ? "text-red-400 bg-red-500/10 border-red-500/30"
      : overallRisk === "High"
      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
      : "text-indigo-400 bg-indigo-500/10 border-indigo-500/30";

  return (
    <div className="h-screen flex flex-col bg-[#080d1a] overflow-hidden">
      {/* Navbar */}
      <nav className="shrink-0 flex items-center justify-between px-5 py-3 bg-[#0d1424]/80 backdrop-blur border-b border-slate-700/60 z-10">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 transition-colors text-sm"
          >
            <ArrowLeft size={15} />
            <span>Upload</span>
          </Link>
          <span className="text-slate-700">·</span>
          <span className="text-sm font-semibold text-slate-200">DORA Risk Graph</span>
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
          <button
            onClick={handleRefreshGraph}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          {lastSessionId && (
            <button
              onClick={handleExportMarkdown}
              disabled={exportLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-indigo-600/80 hover:bg-indigo-600 text-white transition-colors disabled:opacity-40"
            >
              {exportLoading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
              ECB Report
            </button>
          )}
        </div>
      </nav>

      {/* Main area */}
      <div className="flex-1 relative overflow-hidden">
        {/* Ambient gradients */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/3 w-[600px] h-[400px] bg-indigo-900/15 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[300px] bg-violet-900/10 rounded-full blur-3xl" />
        </div>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="flex flex-col items-center gap-3 text-slate-500">
              <Loader2 size={28} className="animate-spin text-indigo-400" />
              <p className="text-sm">Loading dependency graph…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center text-red-400 text-sm">
              <p className="font-medium mb-1">Failed to load graph</p>
              <p className="text-slate-500 text-xs">{error}</p>
              <button
                onClick={handleRefreshGraph}
                className="mt-3 text-xs text-indigo-400 hover:underline"
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
            />
          </motion.div>
        )}

        {/* Legend */}
        {graphData && !selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-5 left-5 flex flex-col gap-1.5 bg-[#0d1424]/80 backdrop-blur border border-slate-700/60 rounded-xl px-4 py-3"
          >
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
              Nodes
            </p>
            {[
              { color: "#ef4444", label: "Critical vendor" },
              { color: "#f59e0b", label: "High risk vendor" },
              { color: "#6366f1", label: "Vendor" },
              { color: "#22d3ee", label: "Service" },
              { color: "#ffffff", label: "Your bank" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: color }}
                />
                <span className="text-xs text-slate-400">{label}</span>
              </div>
            ))}
            <p className="text-[10px] text-slate-600 mt-1.5">Click a vendor to analyse</p>
          </motion.div>
        )}

        {/* Vendor panel */}
        {graphData && (
          <VendorPanel
            nodeKey={selectedNode}
            nodeAttrs={selectedAttrs}
            contractIds={vendorContracts}
            onClose={handleClosePanel}
            onSessionReady={setLastSessionId}
          />
        )}
      </div>
    </div>
  );
}
