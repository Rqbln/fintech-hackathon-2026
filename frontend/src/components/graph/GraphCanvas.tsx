"use client";

import { useEffect, useRef } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import { circular } from "graphology-layout";
import type { GraphResponse, NodeAttributes } from "@/lib/types";
import { nodeColor, nodeSize } from "@/lib/utils";

interface Props {
  data: GraphResponse;
  selectedNode: string | null;
  onNodeClick: (key: string, attrs: NodeAttributes) => void;
}

const BANK_KEY = "client:bank";

export default function GraphCanvas({ data, selectedNode, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const rafRef = useRef<number>(0);

  // Build and render the graph once when data changes
  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new Graph();
    graphRef.current = graph;

    // Bank (client) node — always at center
    graph.addNode(BANK_KEY, {
      label: "Your Bank",
      node_type: "Bank",
      criticality_score: 0,
      color: "#ffffff",
      size: 28,
      baseSize: 28,
      x: 0,
      y: 0,
    });

    // Vendor / Service / Contract nodes from API
    for (const { key, attributes } of data.nodes) {
      if (!graph.hasNode(key)) {
        const score = attributes.criticality_score ?? 0;
        const sz = nodeSize(attributes.node_type, score);
        graph.addNode(key, {
          ...attributes,
          color: nodeColor(attributes.node_type, score),
          size: sz,
          baseSize: sz,
          x: Math.random() * 4 - 2,
          y: Math.random() * 4 - 2,
        });
      }
    }

    // Edges from API
    for (const { key, source, target, attributes } of data.edges) {
      if (graph.hasNode(source) && graph.hasNode(target) && !graph.hasEdge(key)) {
        graph.addEdgeWithKey(key, source, target, {
          label: attributes.label,
          color: attributes.label === "DEPENDS_ON" ? "#f59e0b44" : "#33415566",
          size: attributes.label === "DEPENDS_ON" ? 2 : 1.2,
        });
      }
    }

    // Connect bank to every vendor
    for (const { key, attributes } of data.nodes) {
      if (attributes.node_type === "Vendor") {
        const edgeKey = `bank->${key}`;
        if (!graph.hasEdge(edgeKey)) {
          graph.addEdgeWithKey(edgeKey, BANK_KEY, key, {
            color: "#33415544",
            size: 1,
            label: "",
          });
        }
      }
    }

    // Initial circular layout, then force atlas, then pin bank at center
    circular.assign(graph, { scale: 5 });
    graph.setNodeAttribute(BANK_KEY, "x", 0);
    graph.setNodeAttribute(BANK_KEY, "y", 0);

    forceAtlas2.assign(graph, {
      iterations: 120,
      settings: { gravity: 2.5, scalingRatio: 6, barnesHutOptimize: true },
    });

    graph.setNodeAttribute(BANK_KEY, "x", 0);
    graph.setNodeAttribute(BANK_KEY, "y", 0);

    // Sigma renderer
    const renderer = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,   // suppress "no width" on hidden/transitioning mount
      renderEdgeLabels: false,
      labelFont: "Inter, system-ui, sans-serif",
      labelSize: 12,
      labelColor: { color: "#94a3b8" },
      labelDensity: 0.07,
      labelGridCellSize: 80,
      minEdgeThickness: 0.5,
    });
    sigmaRef.current = renderer;

    renderer.on("clickNode", ({ node }) => {
      const attrs = graph.getNodeAttributes(node) as NodeAttributes;
      onNodeClick(node, attrs);
    });

    renderer.on("clickStage", () => {
      // Clicking empty space deselects — handled by parent
    });

    // Pulse animation for high-risk vendor nodes
    const animate = () => {
      // Guard: stop if renderer was killed or container is gone
      if (!sigmaRef.current || !containerRef.current?.isConnected) return;
      const t = Date.now() / 700;
      for (const node of graph.nodes()) {
        const attrs = graph.getNodeAttributes(node);
        if ((attrs.criticality_score ?? 0) > 0.6 && attrs.node_type === "Vendor") {
          const pulse = 1 + 0.15 * Math.sin(t + node.charCodeAt(0));
          graph.setNodeAttribute(node, "size", (attrs.baseSize ?? 20) * pulse);
        }
      }
      renderer.refresh({ skipIndexation: true });
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
      renderer.kill();
      sigmaRef.current = null;
      graphRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Update node/edge appearance when selection changes
  useEffect(() => {
    const renderer = sigmaRef.current;
    const graph = graphRef.current;
    if (!renderer || !graph) return;

    renderer.setSetting("nodeReducer", (node, data) => {
      if (node === BANK_KEY) return { ...data, color: "#ffffff", size: 28, zIndex: 10 };
      if (!selectedNode) return data;
      if (node === selectedNode) return { ...data, zIndex: 5, size: (data.baseSize ?? 15) * 1.35 };
      if (graph.areNeighbors(selectedNode, node)) return data;
      return { ...data, color: "#1e293b", label: undefined, size: (data.baseSize ?? 10) * 0.7 };
    });

    renderer.setSetting("edgeReducer", (edge, data) => {
      if (!selectedNode) return data;
      if (graph.hasExtremity(edge, selectedNode)) return { ...data, size: (data.size ?? 1) * 2.5, color: "#6366f188" };
      return { ...data, color: "#0f172a", size: 0.4 };
    });

    renderer.refresh();
  }, [selectedNode]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ background: "transparent" }}
    />
  );
}
