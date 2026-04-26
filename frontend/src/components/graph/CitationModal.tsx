"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Loader2, FileText } from "lucide-react";

interface Props {
  contractId: string | null;
  page: number;
  quote: string;
  onClose: () => void;
}

export default function CitationModal({ contractId, page, quote, onClose }: Props) {
  const isOpen = !!contractId;
  const [currentPage, setCurrentPage] = useState(page > 0 ? page : 1);
  const [loading, setLoading] = useState(true);
  const embedRef = useRef<HTMLObjectElement>(null);

  // Resolve the exact page containing the quote, then open the PDF there
  useEffect(() => {
    if (!contractId) return;
    setLoading(true);

    if (quote) {
      fetch(`/api/documents/${contractId}/find-text?q=${encodeURIComponent(quote)}`)
        .then((r) => r.json())
        .then((data: { page: number }) => setCurrentPage(data.page))
        .catch(() => setCurrentPage(page > 0 ? page : 1));
    } else {
      setCurrentPage(page > 0 ? page : 1);
    }
  }, [contractId, page, quote]);

  const pdfSrc = contractId
    ? `/api/documents/${contractId}/pdf?highlight=${encodeURIComponent(quote)}#page=${currentPage}`
    : "";

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
            className="fixed inset-x-4 top-8 bottom-8 md:inset-x-16 lg:inset-x-32 xl:inset-x-52 z-50 flex flex-col rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <FileText size={16} className="text-indigo-600 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">
                    {contractId}
                  </p>
                  {quote && (
                    <p className="text-xs text-slate-500 truncate mt-0.5 italic">
                      "{quote.slice(0, 80)}{quote.length > 80 ? "…" : ""}"
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0 ml-4">
                {/* Page navigation */}
                <div className="flex items-center gap-1 bg-slate-100 rounded-lg px-1 py-1">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <span className="text-xs text-slate-700 px-1 min-w-[60px] text-center">
                    p. {currentPage}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => p + 1)}
                    className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors"
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>

                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Cited quote banner */}
            {quote && (
              <div className="px-5 py-2.5 bg-indigo-50 border-b border-indigo-200 shrink-0">
                <p className="text-xs text-indigo-700 italic leading-relaxed">
                  <span className="text-indigo-600 font-semibold not-italic mr-1">Citation:</span>
                  "{quote}"
                </p>
              </div>
            )}

            {/* PDF embed */}
            <div className="flex-1 relative bg-white overflow-hidden">
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center z-10 bg-white">
                  <div className="flex flex-col items-center gap-3 text-slate-500">
                    <Loader2 size={24} className="animate-spin text-indigo-600" />
                    <p className="text-sm">Loading document…</p>
                  </div>
                </div>
              )}
              <object
                ref={embedRef}
                key={`${contractId}-${currentPage}`}
                data={pdfSrc}
                type="application/pdf"
                className="w-full h-full"
                onLoad={() => setLoading(false)}
              >
                {/* Fallback for browsers without inline PDF support */}
                <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
                  <FileText size={40} className="text-slate-300" />
                  <p className="text-sm text-center">
                    Your browser cannot display PDFs inline.
                  </p>
                  <a
                    href={`/api/documents/${contractId}/pdf`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 text-sm hover:underline"
                  >
                    Open in new tab →
                  </a>
                </div>
              </object>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
