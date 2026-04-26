import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Verdict } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreToColor(score: number): string {
  if (score > 0.7) return "#ef4444";   // red — critical
  if (score > 0.4) return "#f59e0b";   // amber — high
  if (score > 0.2) return "#6366f1";   // indigo — medium
  return "#94a3b8";                     // slate — low
}

export function scoreToLabel(score: number): string {
  if (score > 0.7) return "Critical";
  if (score > 0.4) return "High";
  if (score > 0.2) return "Medium";
  return "Low";
}

export function nodeColor(nodeType: string, score: number): string {
  if (nodeType === "Bank") return "#f8fafc";
  if (nodeType === "Service") return "#22d3ee";
  if (nodeType === "Contract") return "#4ade80";
  if (nodeType === "DORAObligation") return "#f87171";
  return scoreToColor(score);
}

export function nodeSize(nodeType: string, score: number): number {
  if (nodeType === "Bank") return 32;
  if (nodeType === "Service") return 8;
  if (nodeType === "Contract") return 7;
  if (nodeType === "DORAObligation") return 8;
  return 10 + score * 30;
}

export function verdictColor(verdict: Verdict): string {
  if (verdict === "met") return "text-emerald-400";
  if (verdict === "partially_met") return "text-amber-400";
  if (verdict === "unmet") return "text-red-400";
  return "text-slate-400";
}

export function verdictIcon(verdict: Verdict): string {
  if (verdict === "met") return "✅";
  if (verdict === "partially_met") return "⚠️";
  if (verdict === "unmet") return "❌";
  return "❓";
}

export function riskBadgeClass(level: string): string {
  if (level === "critical") return "bg-red-50 text-red-700 border-red-200";
  if (level === "high") return "bg-amber-50 text-amber-700 border-amber-200";
  if (level === "medium") return "bg-indigo-50 text-indigo-700 border-indigo-200";
  return "bg-slate-50 text-slate-700 border-slate-200";
}
