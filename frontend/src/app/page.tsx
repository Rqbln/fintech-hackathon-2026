"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ShieldCheck } from "lucide-react";
import DropZone from "@/components/upload/DropZone";
import ProcessingFeed from "@/components/upload/ProcessingFeed";
import { ingestContract, pollJob } from "@/lib/api";
import type { UploadedFile } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 2000;

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [running, setRunning] = useState(false);
  const intervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  const allDone = files.length > 0 && files.every((f) => f.status === "done" || f.status === "error");

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
        try {
          const { job_id, contract_id } = await ingestContract(uf.file, uf.contractId);
          uf.jobId = job_id;
          uf.contractId = contract_id;

          setFiles((prev) =>
            prev.map((f) =>
              f.contractId === uf.contractId
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
              f.contractId === uf.contractId
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

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-16 relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-indigo-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/4 w-[400px] h-[300px] bg-violet-600/6 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-xl relative z-10">
        {/* Logo / header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mb-4">
            <ShieldCheck size={26} className="text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            DORA AI Analyst
          </h1>
          <p className="text-slate-500 text-sm mt-1.5">
            Upload vendor contracts · AI extracts, maps, and audits DORA compliance
          </p>
        </div>

        {/* Drop zone */}
        <DropZone onFiles={processFiles} disabled={running} />

        {/* Processing feed */}
        {files.length > 0 && (
          <div className="mt-6">
            <ProcessingFeed files={files} />
          </div>
        )}

        {/* CTA */}
        <div className="mt-6 flex flex-col items-center gap-3">
          <button
            disabled={!allDone}
            onClick={handleNavigate}
            className={cn(
              "flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-200",
              allDone
                ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/40 scale-100 hover:scale-[1.02]"
                : "bg-slate-800 text-slate-600 cursor-not-allowed"
            )}
          >
            View Risk Graph
            <ArrowRight size={16} />
          </button>
          {files.length > 0 && !allDone && (
            <p className="text-xs text-slate-600">AI pipeline running — please wait…</p>
          )}
        </div>
      </div>
    </main>
  );
}
