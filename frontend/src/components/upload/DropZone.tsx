"use client";

import { useCallback, useState } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export default function DropZone({ onFiles, disabled }: Props) {
  const [dragging, setDragging] = useState(false);

  const handle = useCallback(
    (files: FileList | null) => {
      if (!files || disabled) return;
      const pdfs = Array.from(files).filter(
        (f) => f.type === "application/pdf" || f.name.endsWith(".pdf")
      );
      if (pdfs.length) onFiles(pdfs);
    },
    [onFiles, disabled]
  );

  return (
    <label
      className={cn(
        "flex flex-col items-center justify-center gap-4 w-full rounded-2xl border-2 border-dashed",
        "cursor-pointer transition-all duration-200 select-none",
        "min-h-[220px] px-8 py-10",
        dragging
          ? "border-indigo-500 bg-indigo-50 scale-[1.01]"
          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
        disabled && "opacity-50 cursor-not-allowed"
      )}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files); }}
    >
      <input
        type="file"
        multiple
        accept=".pdf,application/pdf"
        className="sr-only"
        disabled={disabled}
        onChange={(e) => handle(e.target.files)}
      />
      <div className={cn(
        "p-4 rounded-2xl transition-colors",
        dragging ? "bg-indigo-100" : "bg-slate-100"
      )}>
        <Upload size={28} className={dragging ? "text-indigo-600" : "text-slate-500"} />
      </div>
      <div className="text-center">
        <p className="text-slate-900 font-medium">
          {dragging ? "Release to upload" : "Drop vendor contracts here"}
        </p>
        <p className="text-slate-500 text-sm mt-1">
          PDF files · multiple allowed
        </p>
      </div>
    </label>
  );
}
