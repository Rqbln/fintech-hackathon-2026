"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { UploadedFile } from "@/lib/types";

interface Props {
  files: UploadedFile[];
}

const STEPS = [
  "Parsing PDF",
  "Embedding into Vector Store",
  "Extracting vendor data",
  "Building dependency graph",
  "Scoring risks",
];

function FileRow({ uf }: { uf: UploadedFile }) {
  const isDone = uf.status === "done";
  const isError = uf.status === "error";
  const isRunning = uf.status === "running" || uf.status === "uploading";

  return (
    <div className="border border-slate-700/60 rounded-lg p-4 bg-slate-900/60">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-200 truncate max-w-[220px]">
          {uf.file.name}
        </span>
        <span className="text-xs text-slate-500">
          {(uf.file.size / 1024).toFixed(0)} KB
        </span>
      </div>

      {isError && (
        <div className="flex items-center gap-2 text-red-400 text-xs mt-1">
          <XCircle size={13} />
          <span>{uf.error ?? "Pipeline failed"}</span>
        </div>
      )}

      {isDone && uf.vendorName && (
        <div className="mt-1">
          <div className="flex items-center gap-2 text-emerald-400 text-xs">
            <CheckCircle2 size={13} />
            <span>{uf.vendorName}</span>
          </div>
          {uf.score !== undefined && (
            <div className="mt-1.5 flex items-center gap-2">
              <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${uf.score * 100}%`,
                    background: uf.score > 0.7 ? "#ef4444" : uf.score > 0.4 ? "#f59e0b" : "#6366f1",
                  }}
                />
              </div>
              <span className="text-xs text-slate-400 w-10 text-right">
                {(uf.score * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}

      {isRunning && (
        <div className="mt-2 space-y-1.5">
          {STEPS.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <Loader2 size={11} className="animate-spin text-indigo-400 shrink-0" />
              <span className="text-xs text-slate-400">{step}</span>
            </div>
          ))}
        </div>
      )}

      {uf.status === "queued" && (
        <div className="flex items-center gap-2 mt-1 text-slate-500 text-xs">
          <Circle size={11} />
          <span>Queued</span>
        </div>
      )}
    </div>
  );
}

export default function ProcessingFeed({ files }: Props) {
  const done = files.filter((f) => f.status === "done").length;

  return (
    <div className="w-full space-y-3">
      {files.length > 0 && (
        <p className="text-xs text-slate-500 text-right">
          {done}/{files.length} complete
        </p>
      )}
      {files.map((uf) => (
        <FileRow key={uf.contractId} uf={uf} />
      ))}
    </div>
  );
}
