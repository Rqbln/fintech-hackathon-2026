import { FileText } from "lucide-react";
import type { ObligationFinding } from "@/lib/types";
import { verdictIcon, verdictColor, riskBadgeClass, cn } from "@/lib/utils";

interface Props {
  finding: ObligationFinding;
  onCitationClick?: (contractId: string, page: number, quote: string) => void;
}

const borderColor: Record<string, string> = {
  met: "border-emerald-400",
  partially_met: "border-amber-400",
  unmet: "border-red-400",
};

export default function FindingCard({ finding, onCitationClick }: Props) {
  return (
    <div className={cn("border-l-[3px] pl-4 py-3 space-y-2.5", borderColor[finding.verdict] ?? "border-slate-300")}>
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-lg leading-none">{verdictIcon(finding.verdict)}</span>
          <span className="text-sm font-semibold text-slate-800">
            Art.{finding.article} §{finding.paragraph}
          </span>
          <span className={cn("text-[11px] px-1.5 py-0.5 rounded border font-medium", riskBadgeClass(finding.risk_level))}>
            {finding.risk_level}
          </span>
        </div>
        <span className={cn("text-xs font-semibold shrink-0", verdictColor(finding.verdict))}>
          {finding.verdict.replace(/_/g, " ")}
        </span>
      </div>

      {/* Rationale */}
      <p className="text-sm text-slate-600 leading-relaxed">{finding.rationale}</p>

      {/* Gap */}
      {finding.gap_description && (
        <p className="text-xs text-red-600 italic leading-relaxed border-l-2 border-red-200 pl-2.5">
          {finding.gap_description}
        </p>
      )}

      {/* Evidence spans + always-visible PDF button */}
      {finding.evidence_spans.length > 0 && (
        <div className="space-y-2 pt-0.5">
          {finding.evidence_spans.slice(0, 2).map((span, i) => (
            <div key={i} className="space-y-1.5">
              <blockquote className="border-l-2 border-slate-200 pl-3 text-xs text-slate-500 italic leading-relaxed">
                "{span.text}"
                {span.page > 0 && (
                  <span className="not-italic text-slate-400 ml-1 tabular"> p.{span.page}</span>
                )}
              </blockquote>
              {onCitationClick && span.document_id && (
                <button
                  onClick={() => onCitationClick(span.document_id, span.page, span.text)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-md transition-colors ml-3"
                >
                  <FileText size={11} />
                  See in PDF
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
