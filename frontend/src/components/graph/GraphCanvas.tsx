"use client";

import { useEffect, useRef } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { EdgeArrowProgram, drawDiscNodeHover, drawDiscNodeLabel } from "sigma/rendering";
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

// Custom hover: draw a soft glow ring behind the standard disc
function drawGlowHover(
  ctx: CanvasRenderingContext2D,
  data: Parameters<typeof drawDiscNodeHover>[1],
  settings: Parameters<typeof drawDiscNodeHover>[2]
) {
  const { x, y, size, color } = data;

  // Outer glow
  const grad = ctx.createRadialGradient(x, y, size * 0.8, x, y, size * 2.8);
  grad.addColorStop(0, (color ?? "#6366f1") + "44");
  grad.addColorStop(1, (color ?? "#6366f1") + "00");
  ctx.beginPath();
  ctx.arc(x, y, size * 2.8, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();

  // Inner ring
  ctx.beginPath();
  ctx.arc(x, y, size + 3, 0, Math.PI * 2);
  ctx.strokeStyle = (color ?? "#6366f1") + "99";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  drawDiscNodeHover(ctx, data, settings);
}

export default function GraphCanvas({ data, selectedNode, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new Graph();
    graphRef.current = graph;

    // Bank node — fixed at center, always visible
    graph.addNode(BANK_KEY, {
      label: "Your Bank",
      node_type: "Bank",
      criticality_score: 0,
      color: "#ffffff",
      size: 26,
      baseSize: 26,
      zIndex: 10,
      x: 0,
      y: 0,
    });

    for (const { key, attributes } of data.nodes) {
      if (!graph.hasNode(key)) {
        const score = attributes.criticality_score ?? 0;
        const sz = nodeSize(attributes.node_type, score);
        graph.addNode(key, {
          ...attributes,
          color: nodeColor(attributes.node_type, score),
          size: sz,
          baseSize: sz,
          zIndex: attributes.node_type === "Vendor" ? 2 : 1,
          x: Math.random() * 4 - 2,
          y: Math.random() * 4 - 2,
        });
      }
    }

    for (const { key, source, target, attributes } of data.edges) {
      if (graph.hasNode(source) && graph.hasNode(target) && !graph.hasEdge(key)) {
        const isDepends = attributes.label === "DEPENDS_ON";
        graph.addEdgeWithKey(key, source, target, {
          label: attributes.label,
          // "arrow" type uses EdgeArrowProgram — shows direction
          type: isDepends ? "arrow" : "line",
          color: isDepends ? "#f59e0b55" : "#33415566",
          size: isDepends ? 2.5 : 1.2,
        });
      }
    }

    // Bank → Vendor edges (thin, structural)
    for (const { key, attributes } of data.nodes) {
      if (attributes.node_type === "Vendor") {
        const edgeKey = `bank->${key}`;
        if (!graph.hasEdge(edgeKey)) {
          graph.addEdgeWithKey(edgeKey, BANK_KEY, key, {
            type: "line",
            color: "#3b4d6644",
            size: 0.8,
            label: "",
          });
        }
      }
    }

    circular.assign(graph, { scale: 5 });
    graph.setNodeAttribute(BANK_KEY, "x", 0);
    graph.setNodeAttribute(BANK_KEY, "y", 0);

    forceAtlas2.assign(graph, {
      iterations: 120,
      settings: { gravity: 2.5, scalingRatio: 6, barnesHutOptimize: true },
    });

    graph.setNodeAttribute(BANK_KEY, "x", 0);
    graph.setNodeAttribute(BANK_KEY, "y", 0);

    const renderer = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,
      renderEdgeLabels: false,
      zIndex: true,

      // Edge programs — "arrow" type gets directional arrowhead
      edgeProgramClasses: { arrow: EdgeArrowProgram },
      defaultEdgeType: "line",

      // Labels
      labelFont: "Inter, system-ui, sans-serif",
      labelSize: 11,
      labelWeight: "600",
      labelColor: { color: "#e2e8f0" },
      labelDensity: 0.05,  // lower = fewer labels, reduces clutter at full zoom
      labelGridCellSize: 100,

      minEdgeThickness: 0.5,

      // Hover: custom glow ring
      defaultDrawNodeHover: drawGlowHover,
      defaultDrawNodeLabel: drawDiscNodeLabel,
    });
    sigmaRef.current = renderer;

    renderer.on("clickNode", ({ node }) => {
      const attrs = graph.getNodeAttributes(node) as NodeAttributes;

      // Animate camera to center on clicked vendor
      if (attrs.node_type === "Vendor") {
        const display = renderer.getNodeDisplayData(node);
        if (display) {
          renderer.getCamera().animate(
            { x: display.x, y: display.y, ratio: 0.35 },
            { duration: 450, easing: "quadraticInOut" }
          );
        }
      }

      onNodeClick(node, attrs);
    });

    // Pulse: high-risk vendors oscillate in size
    const animate = () => {
      if (!sigmaRef.current || !containerRef.current?.isConnected) return;
      const t = Date.now() / 800;
      for (const node of graph.nodes()) {
        const attrs = graph.getNodeAttributes(node);
        if ((attrs.criticality_score ?? 0) > 0.6 && attrs.node_type === "Vendor") {
          const pulse = 1 + 0.18 * Math.sin(t + node.charCodeAt(0));
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

  // Selection highlight via reducers
  useEffect(() => {
    const renderer = sigmaRef.current;
    const graph = graphRef.current;
    if (!renderer || !graph) return;

    renderer.setSetting("nodeReducer", (node, nodeData) => {
      // Bank always white, always on top
      if (node === BANK_KEY) return { ...nodeData, color: "#ffffff", size: 26, zIndex: 10 };

      if (!selectedNode) return nodeData;

      if (node === selectedNode) {
        return { ...nodeData, zIndex: 8, size: (nodeData.baseSize ?? 15) * 1.4 };
      }
      if (graph.areNeighbors(selectedNode, node)) {
        return { ...nodeData, zIndex: 3 };
      }
      // Dim non-neighbors
      return { ...nodeData, color: "#1e2d45", label: undefined, size: (nodeData.baseSize ?? 10) * 0.65, zIndex: 0 };
    });

    renderer.setSetting("edgeReducer", (edge, edgeData) => {
      if (!selectedNode) return edgeData;
      if (graph.hasExtremity(edge, selectedNode)) {
        return { ...edgeData, size: (edgeData.size ?? 1) * 2.8, color: "#6366f1aa", zIndex: 5 };
      }
      return { ...edgeData, color: "#0f172a", size: 0.3, zIndex: 0 };
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
