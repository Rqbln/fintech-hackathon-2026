"use client";

import { memo, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Building2, Cloud, Database, FileText, ShieldAlert, TriangleAlert, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import SaasShell from "@/components/shell/SaasShell";
import { getGraph } from "@/lib/api";
import type { GraphEdge, GraphNode } from "@/lib/types";

type Risk = "core" | "critical" | "warning" | "compliant";
type NodeType = "bank" | "cloud" | "service" | "contract";

interface SupplyNodeData {
  label: string;
  risk: Risk;
  nodeType: NodeType;
  subtitle: string;
}

const riskBadgeClass: Record<Risk, string> = {
  core: "bg-blue-100 text-blue-800 border-blue-300",
  critical: "bg-rose-100 text-rose-800 border-rose-300",
  warning: "bg-amber-100 text-amber-800 border-amber-300",
  compliant: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

const riskLabel: Record<Risk, string> = {
  core: "Central Entity",
  critical: "Critical",
  warning: "Warning",
  compliant: "Compliant",
};

const iconByNodeType = {
  bank: Building2,
  cloud: Cloud,
  contract: FileText,
  service: Database,
};

const cardStyle: CSSProperties = {
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
};

const SupplyChainNode = memo(({ data }: NodeProps<Node<SupplyNodeData>>) => {
  const Icon = iconByNodeType[data.nodeType];
  const RiskIcon = data.risk === "critical" ? ShieldAlert : data.risk === "warning" ? TriangleAlert : ShieldCheck;

  return (
    <div
      style={cardStyle}
      className="min-w-[220px] rounded-xl border border-white/60 bg-white/80 p-3 shadow-lg shadow-slate-900/10"
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-slate-400" />
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
          <Icon size={18} />
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
            riskBadgeClass[data.risk]
          )}
        >
          <RiskIcon size={12} />
          {riskLabel[data.risk]}
        </span>
      </div>
      <p className="text-sm font-bold text-slate-900">{data.label}</p>
      <p className="mt-0.5 text-[11px] text-slate-500">{data.subtitle}</p>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-slate-400" />
    </div>
  );
});
SupplyChainNode.displayName = "SupplyChainNode";

const nodeTypes = {
  supplyChainNode: SupplyChainNode,
};

function inferNodeType(label: string): NodeType {
  const lower = label.toLowerCase();
  if (lower.includes("cloud") || lower.includes("aws") || lower.includes("azure") || lower.includes("gcp")) return "cloud";
  if (lower.includes("bank") || lower.includes("banque")) return "bank";
  return "service";
}

function inferRisk(node: GraphNode, rootId: string | null): Risk {
  if (rootId && node.key === rootId) return "core";
  if (node.attributes.is_critical_provider || node.attributes.criticality_score >= 0.75) return "critical";
  if (node.attributes.criticality_score >= 0.4) return "warning";
  return "compliant";
}

function buildContractGraph(params: {
  contractId: string;
  bankName: string;
  vendorNodes: GraphNode[];
  vendorEdges: GraphEdge[];
  rootVendorId: string | null;
}): { nodes: Node<SupplyNodeData>[]; edges: Edge[] } {
  const { contractId, bankName, vendorNodes, vendorEdges, rootVendorId } = params;
  const bankId = "bank::central";
  const contractNodeId = `contract::${contractId || "latest"}`;

  const outgoing = new Map<string, string[]>();
  const incoming = new Map<string, number>();
  for (const v of vendorNodes) outgoing.set(v.key, []);
  for (const v of vendorNodes) incoming.set(v.key, 0);
  for (const e of vendorEdges) {
    outgoing.get(e.source)?.push(e.target);
    incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1);
  }

  const depth = new Map<string, number>();
  if (rootVendorId) {
    const queue = [rootVendorId];
    depth.set(rootVendorId, 0);
    while (queue.length > 0) {
      const current = queue.shift()!;
      const currentDepth = depth.get(current) ?? 0;
      for (const next of outgoing.get(current) ?? []) {
        if (!depth.has(next)) {
          depth.set(next, currentDepth + 1);
          queue.push(next);
        }
      }
    }
  }
  for (const v of vendorNodes) {
    if (!depth.has(v.key)) depth.set(v.key, rootVendorId ? 1 : 0);
  }

  const byDepth = new Map<number, string[]>();
  for (const [id, d] of depth.entries()) {
    const arr = byDepth.get(d) ?? [];
    arr.push(id);
    byDepth.set(d, arr);
  }

  const nodes: Node<SupplyNodeData>[] = [
    {
      id: bankId,
      type: "supplyChainNode",
      position: { x: 130, y: 320 },
      data: {
        label: bankName,
        risk: "core",
        nodeType: "bank",
        subtitle: "Institution",
      },
    },
    {
      id: contractNodeId,
      type: "supplyChainNode",
      position: { x: 470, y: 320 },
      data: {
        label: contractId || "Latest contract",
        risk: "core",
        nodeType: "contract",
        subtitle: "Contrat ingere",
      },
    },
  ];

  const xStart = 820;
  const xStep = 300;
  const yCenter = 320;
  const yStep = 150;

  for (const n of vendorNodes) {
    const d = depth.get(n.key) ?? 0;
    const siblings = byDepth.get(d) ?? [n.key];
    const siblingIndex = Math.max(0, siblings.indexOf(n.key));
    const blockHeight = (siblings.length - 1) * yStep;
    const y = yCenter - blockHeight / 2 + siblingIndex * yStep;
    nodes.push({
      id: n.key,
      type: "supplyChainNode",
      position: { x: xStart + d * xStep, y },
      data: {
        label: n.attributes.label,
        risk: inferRisk(n, rootVendorId),
        nodeType: inferNodeType(n.attributes.label),
        subtitle:
          rootVendorId && n.key === rootVendorId
            ? "Fournisseur principal du contrat"
            : (incoming.get(n.key) ?? 0) > 0
              ? `Sous-traitant (niveau ${Math.max(1, d)})`
              : "Fournisseur mentionne dans le contrat",
      },
    });
  }

  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const edges: Edge[] = [
    {
      id: `e-${bankId}-${contractNodeId}`,
      source: bankId,
      target: contractNodeId,
      type: "default",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#2563eb" },
      style: { stroke: "#2563eb", strokeWidth: 2.3 },
    },
  ];

  for (const vendor of vendorNodes) {
    const targetRisk = nodeById.get(vendor.key)?.data.risk;
    const stroke = targetRisk === "critical" ? "#e11d48" : targetRisk === "warning" ? "#f59e0b" : "#10b981";
    edges.push({
      id: `e-${bankId}-${vendor.key}`,
      source: bankId,
      target: vendor.key,
      type: "default",
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
      style: { stroke, strokeWidth: targetRisk === "critical" ? 2.2 : 2 },
    });
  }
  return { nodes, edges };
}

function minimapColor(node: Node<SupplyNodeData>) {
  if (node.data.risk === "critical") return "#e11d48";
  if (node.data.risk === "warning") return "#f59e0b";
  if (node.data.risk === "compliant") return "#10b981";
  return "#2563eb";
}

export default function GraphPage() {
  const router = useRouter();
  const defaultViewport = useMemo(() => ({ x: -20, y: -30, zoom: 0.9 }), []);
  const [nodes, setNodes] = useState<Node<SupplyNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [rootVendorName, setRootVendorName] = useState<string | null>(null);
  const [contractByVendorId, setContractByVendorId] = useState<Record<string, string>>({});
  const [defaultContractId, setDefaultContractId] = useState<string>("");
  const [bankName, setBankName] = useState("Institution");

  useEffect(() => {
    let cancelled = false;

    const load = async (initial = false) => {
      if (initial) setLoading(true);
      try {
        const graph = await getGraph(undefined, 3);
        const vendorNodes = graph.nodes.filter((n) => n.attributes.node_type === "Vendor");
        const contractNodes = graph.nodes.filter((n) => n.attributes.node_type === "Contract");
        const vendorIds = new Set(vendorNodes.map((n) => n.key));
        const contractIds = new Set(contractNodes.map((n) => n.key));
        const coversEdges = graph.edges.filter(
          (e) => contractIds.has(e.source) && vendorIds.has(e.target) && e.attributes.label === "COVERS"
        );
        const contractForVendor = new Map<string, string>();
        for (const edge of coversEdges) {
          if (!contractForVendor.has(edge.target)) contractForVendor.set(edge.target, edge.source);
        }
        const vendorEdges = graph.edges.filter(
          (e) =>
            vendorIds.has(e.source) &&
            vendorIds.has(e.target) &&
            e.attributes.label === "DEPENDS_ON"
        );

        const coveredVendorIds = new Set(coversEdges.map((e) => e.target));
        const rootVendorId =
          vendorNodes.find((n) => coveredVendorIds.has(n.key))?.key ??
          vendorNodes.find((n) => !vendorEdges.some((e) => e.target === n.key))?.key ??
          vendorNodes[0]?.key ??
          null;
        const inferredRoot = rootVendorId ? vendorNodes.find((n) => n.key === rootVendorId)?.attributes.label ?? null : null;
        const activeContractId =
          (rootVendorId ? contractForVendor.get(rootVendorId) : undefined) ??
          coversEdges[0]?.source ??
          contractNodes[0]?.key ??
          "";
        const contractGraph = buildContractGraph({
          contractId: activeContractId,
          bankName,
          vendorNodes,
          vendorEdges,
          rootVendorId,
        });

        if (!cancelled) {
          setGraphError(null);
          setRootVendorName(inferredRoot);
          setDefaultContractId(activeContractId);
          setContractByVendorId(Object.fromEntries(contractForVendor.entries()));
          setNodes(contractGraph.nodes);
          setEdges(contractGraph.edges);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setGraphError(err instanceof Error ? err.message : "Graph loading failed");
          setNodes([]);
          setEdges([]);
          setLoading(false);
        }
      }
    };

    try {
      const rawProfile = sessionStorage.getItem("caseProfile");
      if (rawProfile) {
        const parsed = JSON.parse(rawProfile) as { institution_name?: string };
        if (parsed.institution_name?.trim()) setBankName(parsed.institution_name.trim());
      }
    } catch {
      // ignore malformed profile cache
    }

    load(true);
    const timer = window.setInterval(() => {
      load(false);
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [bankName]);

  return (
    <SaasShell
      title="Supply Chain Risk Map"
      subtitle="Vendors and subcontractors extracted from ingested contracts"
      topTabs={[
        { id: "riskMap", label: "Risk map" },
        { id: "contracts", label: "Dependencies" },
        { id: "suppliers", label: "Suppliers" },
      ]}
      activeTabId="riskMap"
      rightActions={
        <div className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
          {loading ? "Loading graph..." : "Live Contract Graph"}
        </div>
      }
    >
      <div className="card-surface h-[calc(100vh-165px)] min-h-[640px] overflow-hidden p-0">
        <div className="relative h-full w-full overflow-hidden rounded-xl">
          <div className="pointer-events-none absolute inset-0 z-0">
            <div className="absolute -left-20 -top-24 h-80 w-80 rounded-full bg-indigo-200/40 blur-3xl" />
            <div className="absolute right-10 top-20 h-72 w-72 rounded-full bg-cyan-200/40 blur-3xl" />
            <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-violet-200/30 blur-3xl" />
          </div>
          {graphError ? (
            <div className="flex h-full items-center justify-center p-6">
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                Failed to load graph: {graphError}
              </div>
            </div>
          ) : nodes.length === 0 && !loading ? (
            <div className="flex h-full items-center justify-center p-6">
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                No vendor dependency graph found yet. Ingest a contract that explicitly mentions subcontractors.
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              defaultViewport={defaultViewport}
              className="h-full w-full bg-transparent"
              proOptions={{ hideAttribution: true }}
              onNodeClick={(_, node) => {
                if (loading) return;
                if (node.id.startsWith("bank::") || node.id.startsWith("contract::")) return;
                const contractId = contractByVendorId[node.id] || defaultContractId;
                if (!contractId) return;
                const params = new URLSearchParams({
                  vendorKey: node.id,
                  vendorName: node.data.label,
                  primaryContractId: contractId,
                  contractIds: contractId,
                });
                router.push(`/investigation?${params.toString()}`);
              }}
            >
              <Background variant={BackgroundVariant.Dots} gap={18} size={1.2} color="#cbd5e1" />
              <MiniMap
                position="bottom-right"
                nodeColor={minimapColor}
                pannable
                zoomable
                className="!h-28 !w-44 !rounded-lg !border !border-slate-200 !bg-white/90"
              />
              <Controls position="bottom-left" className="!rounded-lg !border !border-slate-200 !bg-white/90" />
            </ReactFlow>
          )}
        </div>
        {!loading && rootVendorName && (
          <div className="absolute left-6 top-6 z-20 rounded-full border border-white/70 bg-white/85 px-3 py-1 text-xs font-medium text-slate-700 shadow-sm">
            Root vendor: {rootVendorName}
          </div>
        )}
      </div>
    </SaasShell>
  );
}
