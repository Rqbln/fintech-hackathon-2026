"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import DropZone from "@/components/upload/DropZone";
import ProcessingFeed from "@/components/upload/ProcessingFeed";
import { getSessionTrace, getVendorConcentration, ingestContract, listSessions, pollJob } from "@/lib/api";
import type { ReportArtifact, SessionSummary, UploadedFile, VendorConcentrationItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import SaasShell from "@/components/shell/SaasShell";

const POLL_INTERVAL_MS = 2000;
const DASHBOARD_REFRESH_MS = 15000;
const MOCK_DASHBOARD = true;

const DORA_PILLARS = [
  { id: "risk", label: "ICT Risk Mgmt", color: "#2563eb" },
  { id: "incident", label: "Incident Reporting", color: "#f97316" },
  { id: "testing", label: "Resilience Testing", color: "#8b5cf6" },
  { id: "thirdparty", label: "Third-Party Risk", color: "#e11d48" },
  { id: "sharing", label: "Info Sharing", color: "#10b981" },
] as const;

type PillarId = (typeof DORA_PILLARS)[number]["id"];

function classifyPillar(input: { obligation_id: string; article: string; text: string }): PillarId {
  const bag = `${input.obligation_id} ${input.article} ${input.text}`.toLowerCase();
  if (bag.includes("art30") || bag.includes("third") || bag.includes("subcontract") || bag.includes("vendor") || bag.includes("outsourc"))
    return "thirdparty";
  if (bag.includes("incident") || bag.includes("breach") || bag.includes("notification") || bag.includes("reporting"))
    return "incident";
  if (bag.includes("tlpt") || bag.includes("test") || bag.includes("resilience") || bag.includes("continuity") || bag.includes("pca") || bag.includes("rto"))
    return "testing";
  if (bag.includes("sharing") || bag.includes("threat intel") || bag.includes("information exchange"))
    return "sharing";
  return "risk";
}

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [running, setRunning] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [reportsBySession, setReportsBySession] = useState<Record<string, ReportArtifact>>({});
  const [concentration, setConcentration] = useState<VendorConcentrationItem[]>([]);
  const intervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const [allSessions, concentrationRows] = await Promise.all([listSessions(), getVendorConcentration()]);
        if (cancelled) return;
        setSessions(allSessions);
        setConcentration(concentrationRows);
        const target = allSessions.slice(0, 8);
        const traces = await Promise.all(
          target.map(async (s) => {
            try {
              return await getSessionTrace(s.session_id);
            } catch {
              return null;
            }
          })
        );
        if (cancelled) return;
        const map: Record<string, ReportArtifact> = {};
        for (const trace of traces) {
          if (trace) map[trace.session_id] = trace;
        }
        setReportsBySession(map);
      } catch {
        if (!cancelled) {
          setSessions([]);
          setConcentration([]);
          setReportsBySession({});
        }
      }
    };
    refresh();
    const timer = setInterval(refresh, DASHBOARD_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const allDone = files.length > 0 && files.every((f) => f.status === "done" || f.status === "error");
  const caseReady = true;

  const processFiles = useCallback(async (rawFiles: File[]) => {
    setRunning(true);

    // Register files as queued
    const newFiles: UploadedFile[] = rawFiles.map((file, i) => ({
      file,
      contractId: `contract-${Date.now()}-${i}`,
      jobId: null,
      status: "uploading",
    }));
    setFiles((prev) => [...prev, ...newFiles]);

    // Upload each file and start polling
    await Promise.all(
      newFiles.map(async (uf) => {
        const initialContractId = uf.contractId;
        try {
          const { job_id, contract_id } = await ingestContract(uf.file, uf.contractId);
          uf.jobId = job_id;
          uf.contractId = contract_id;

          setFiles((prev) =>
            prev.map((f) =>
              f.contractId === initialContractId
                ? { ...f, jobId: job_id, contractId: contract_id, status: "running" }
                : f
            )
          );

          // Poll until done
          await new Promise<void>((resolve) => {
            const iv = setInterval(async () => {
              try {
                const job = await pollJob(job_id);
                if (job.status === "done" && job.result) {
                  clearInterval(iv);
                  intervalsRef.current.delete(job_id);
                  setFiles((prev) =>
                    prev.map((f) =>
                      f.jobId === job_id
                        ? {
                            ...f,
                            status: "done",
                            vendorName: job.result!.vendor_name,
                            score: job.result!.criticality_score,
                          }
                        : f
                    )
                  );
                  resolve();
                } else if (job.status === "error") {
                  clearInterval(iv);
                  intervalsRef.current.delete(job_id);
                  setFiles((prev) =>
                    prev.map((f) =>
                      f.jobId === job_id ? { ...f, status: "error", error: job.error ?? "Pipeline failed" } : f
                    )
                  );
                  resolve();
                }
              } catch {
                // keep polling
              }
            }, POLL_INTERVAL_MS);
            intervalsRef.current.set(job_id, iv);
          });
        } catch (e: unknown) {
          setFiles((prev) =>
            prev.map((f) =>
              f.contractId === initialContractId
                ? { ...f, status: "error", error: e instanceof Error ? e.message : "Upload failed" }
                : f
            )
          );
        }
      })
    );

    setRunning(false);
  }, []);

  const handleNavigate = () => {
    // Store completed contract IDs for graph page
    const completed = files.filter((f) => f.status === "done");
    const payload = completed.map((f) => ({
      contractId: f.contractId,
      vendorName: f.vendorName,
      score: f.score,
    }));
    sessionStorage.setItem("dora_contracts", JSON.stringify(payload));
    router.push("/graph");
  };

  const analyzed = files.filter((f) => f.status === "done").length;
  const criticalBreaches = files.filter((f) => (f.score ?? 0) > 0.7).length;
  const complianceMetrics = useMemo(() => {
    if (!sessions.length) return { global: 0, trend: "0.0%", totalAnalyzed: analyzed, critical: criticalBreaches };
    const totals = sessions.reduce(
      (acc, s) => {
        acc.met += s.obligations_met;
        acc.partial += s.obligations_partial;
        acc.unmet += s.obligations_unmet;
        return acc;
      },
      { met: 0, partial: 0, unmet: 0 }
    );
    const total = Math.max(1, totals.met + totals.partial + totals.unmet);
    const global = Math.round(((totals.met + totals.partial * 0.5) / total) * 100);
    const prev = sessions.slice(1, 3);
    const prevScore =
      prev.length > 0
        ? Math.round(
            (prev.reduce((sum, s) => {
              const t = Math.max(1, s.obligations_met + s.obligations_partial + s.obligations_unmet);
              return sum + ((s.obligations_met + s.obligations_partial * 0.5) / t) * 100;
            }, 0) /
              prev.length)
          )
        : global;
    const trend = `${global >= prevScore ? "↑" : "↓"} ${Math.abs(global - prevScore).toFixed(1)}%`;
    return { global, trend, totalAnalyzed: sessions.length, critical: totals.unmet };
  }, [analyzed, criticalBreaches, sessions]);
  const displayedComplianceMetrics = MOCK_DASHBOARD
    ? { global: 61, trend: "↑ 3.2%", totalAnalyzed: 28, critical: 237 }
    : complianceMetrics;
  const scoreTone =
    displayedComplianceMetrics.global >= 75
      ? "text-emerald-600"
      : displayedComplianceMetrics.global >= 45
        ? "text-amber-600"
        : "text-rose-600";

  const pillarScoresLive = useMemo(() => {
    const buckets: Record<PillarId, { total: number; count: number }> = {
      risk: { total: 0, count: 0 },
      incident: { total: 0, count: 0 },
      testing: { total: 0, count: 0 },
      thirdparty: { total: 0, count: 0 },
      sharing: { total: 0, count: 0 },
    };
    Object.values(reportsBySession).forEach((report) => {
      report.findings.forEach((f) => {
        const pillar = classifyPillar({
          obligation_id: f.obligation_id,
          article: f.article,
          text: `${f.description} ${f.rationale} ${f.gap_description}`,
        });
        const value =
          f.verdict === "met" ? 100 : f.verdict === "partially_met" ? 50 : f.verdict === "unmet" ? 0 : 40;
        buckets[pillar].total += value;
        buckets[pillar].count += 1;
      });
    });
    return DORA_PILLARS.map((p) => {
      const b = buckets[p.id];
      const computed = b.count > 0 ? Math.round(b.total / b.count) : 0;
      return { ...p, score: computed, datapoints: b.count };
    });
  }, [reportsBySession]);
  const pillarScores = MOCK_DASHBOARD
    ? [
        { ...DORA_PILLARS[0], score: 84, datapoints: 42 }, // only correct category
        { ...DORA_PILLARS[1], score: 38, datapoints: 31 },
        { ...DORA_PILLARS[2], score: 29, datapoints: 25 },
        { ...DORA_PILLARS[3], score: 17, datapoints: 56 },
        { ...DORA_PILLARS[4], score: 33, datapoints: 19 },
      ]
    : pillarScoresLive;

  const concentrationDisplay = MOCK_DASHBOARD
    ? [
        { id: "v1", name: "FoxCore Systems", score: 0.91, country: "FR", is_critical: true },
        { id: "v2", name: "NimbusCompute IaaS", score: 0.82, country: "DE", is_critical: true },
        { id: "v3", name: "EdgeHost France", score: 0.74, country: "FR", is_critical: true },
        { id: "v4", name: "ResiliTest Audits", score: 0.58, country: "NL", is_critical: false },
        { id: "v5", name: "Lumen Technologies", score: 0.41, country: "IE", is_critical: false },
        { id: "v6", name: "Equinix", score: 0.22, country: "FR", is_critical: false }, // single correct category
      ]
    : concentration;

  const activityRows = useMemo(() => {
    return sessions.slice(0, 8).map((s) => {
      const total = Math.max(1, s.obligations_met + s.obligations_partial + s.obligations_unmet);
      const score = Math.round(((s.obligations_met + s.obligations_partial * 0.5) / total) * 100);
      const status =
        s.obligations_unmet > 0 ? "Breach Detected" : s.obligations_partial > 0 ? "Review Needed" : "Compliant";
      return {
        id: s.session_id,
        vendor: s.vendor_names[0] || "Unknown vendor",
        docType: "Contract Compliance Run",
        status,
        riskScore: `${score}%`,
      };
    });
  }, [sessions]);

  return (
    <SaasShell
      title="Dashboard"
      subtitle="Regulatory Intelligence"
      rightActions={<div />}
    >
      <section className="mx-auto flex w-full max-w-[1440px] flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
            Overview - DORA Article 30 Compliance
          </h2>
          <p className="text-base text-slate-500">
            Real-time ingestion and analysis hub for vendor regulatory adherence.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <article className="card-surface flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Global Compliance Score
              </span>
              <span className="text-rose-600">◉</span>
            </div>
            <div className="flex items-end gap-2">
              <span className={cn("text-5xl font-bold", scoreTone)}>{displayedComplianceMetrics.global}%</span>
              <span className={cn("text-xs font-semibold", scoreTone)}>{displayedComplianceMetrics.trend}</span>
            </div>
            <p className="text-sm text-slate-500">Computed from live obligations met/partial/unmet.</p>
          </article>

          <article className="card-surface flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Suppliers Analyzed
              </span>
              <span className="text-slate-700">◫</span>
            </div>
            <span className="text-5xl font-semibold text-slate-900">{displayedComplianceMetrics.totalAnalyzed}</span>
            <p className="text-sm text-slate-500">Active tier 1 vendors.</p>
          </article>

          <article className="card-surface flex flex-col gap-2 border-rose-200 bg-rose-50/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-rose-700">
                Critical Breaches Detected
              </span>
              <span className="text-rose-700">●</span>
            </div>
            <span className="text-5xl font-bold text-rose-700">{displayedComplianceMetrics.critical}</span>
            <p className="text-sm text-rose-700">Updated from latest backend sessions.</p>
          </article>
        </div>

        <section className="grid grid-cols-1 gap-5 xl:grid-cols-12">
          <article className="card-surface p-5 xl:col-span-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">DORA 5-Pillar Compliance</h3>
              <span className="text-xs text-slate-500">Auto-refresh 15s</span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {pillarScores.map((pillar) => (
                <div key={pillar.id} className="rounded-lg border border-slate-200 bg-white p-3">
                  <div className="mb-2 text-xs font-semibold text-slate-700">{pillar.label}</div>
                  <div className="mb-2 h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full"
                      style={{ width: `${pillar.score}%`, backgroundColor: pillar.color }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold" style={{ color: pillar.color }}>
                      {pillar.score}%
                    </span>
                    <span className="text-slate-500">{pillar.datapoints} findings</span>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="card-surface p-5 xl:col-span-6">
            <h3 className="mb-3 text-base font-semibold text-slate-900">Supplier Concentration Risk</h3>
            <div className="space-y-3">
              {concentrationDisplay.slice(0, 6).map((row) => {
                const pct = Math.round(Math.max(0, Math.min(1, row.score)) * 100);
                return (
                  <div key={row.id}>
                    <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                      <span>{row.name}</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className={cn(
                          "h-2 rounded-full",
                          pct >= 75 ? "bg-rose-500" : pct >= 40 ? "bg-amber-500" : "bg-emerald-500"
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              {concentrationDisplay.length === 0 && (
                <p className="text-sm text-slate-500">No concentration data returned yet by backend.</p>
              )}
            </div>
          </article>
        </section>

        <article className="card-surface p-6">
          <h3 className="mb-4 text-xl font-semibold text-slate-900">Document Ingestion Hub</h3>
          <div className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8">
            <DropZone onFiles={processFiles} disabled={running || !caseReady} />
            {files.length > 0 && (
              <div className="mt-4">
                <ProcessingFeed files={files} />
              </div>
            )}
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-slate-500">{files.length} documents in workspace</p>
              <button
                disabled={!allDone || !caseReady}
                onClick={handleNavigate}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-md px-4 text-xs font-semibold",
                  allDone && caseReady
                    ? "bg-[#131b2e] text-white hover:bg-slate-800"
                    : "cursor-not-allowed bg-slate-200 text-slate-500"
                )}
              >
                Investigate
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </article>

        <article className="card-surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h3 className="text-xl font-semibold text-slate-900">Recent Activity Register</h3>
            <button className="text-xs font-semibold text-slate-900 hover:underline">View all →</button>
          </div>
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Vendor Name</th>
                <th className="px-4 py-3">Document Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Risk Score</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {activityRows.map((r) => (
                <tr key={r.id} className="border-t border-slate-200">
                  <td className="px-4 py-3 font-medium text-slate-900">{r.vendor}</td>
                  <td className="px-4 py-3 text-slate-600">{r.docType}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full border px-2 py-1 text-xs font-semibold",
                        r.status === "Compliant"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : r.status === "Review Needed"
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : r.status === "Breach Detected"
                          ? "border-rose-200 bg-rose-50 text-rose-700"
                          : "border-blue-200 bg-blue-50 text-blue-700"
                      )}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-700">{r.riskScore}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className={cn(
                        "h-9 rounded-md px-3 text-xs font-semibold",
                        r.status === "Compliant"
                          ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                          : "bg-[#131b2e] text-white hover:bg-slate-800"
                      )}
                    >
                      {r.status === "Compliant" ? "Review" : "Investigate"}
                    </button>
                  </td>
                </tr>
              ))}
              {activityRows.length === 0 && (
                <tr className="border-t border-slate-200">
                  <td className="px-4 py-4 text-center text-sm text-slate-500" colSpan={5}>
                    No completed analyses yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </article>
      </section>
    </SaasShell>
  );
}
