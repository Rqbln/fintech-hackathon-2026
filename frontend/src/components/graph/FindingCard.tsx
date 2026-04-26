import { ExternalLink } from "lucide-react";
import type { ObligationFinding } from "@/lib/types";
import { verdictIcon, verdictColor, riskBadgeClass, cn } from "@/lib/utils";

interface Props {
  finding: ObligationFinding;
  onCitationClick?: (contractId: string, page: number, quote: string) => void;
}

export default function FindingCard({ finding, onCitationClick }: Props) {
  const borderColor =
    finding.verdict === "met"
      ? "border-emerald-300"
      : finding.verdict === "partially_met"
      ? "border-amber-300"
      : finding.verdict === "unmet"
      ? "border-red-300"
      : "border-slate-300";

  return (
    <div className={cn("border-l-2 pl-3 py-2 space-y-1.5", borderColor)}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none">{verdictIcon(finding.verdict)}</span>
          <span className="text-xs font-semibold text-slate-700 tracking-tight">
            Art.{finding.article} §{finding.paragraph}
          </span>
          <span className={cn("text-[11px] px-1.5 py-0.5 rounded border font-medium", riskBadgeClass(finding.risk_level))}>
            {finding.risk_level}
          </span>
        </div>
        <span className={cn("text-xs font-medium", verdictColor(finding.verdict))}>
          {finding.verdict.replace("_", " ")}
        </span>
      </div>

      {/* Rationale — primary body text, minimum 13px */}
      <p className="text-[13px] text-slate-600 leading-relaxed">{finding.rationale}</p>

      {/* Gap */}
      {finding.gap_description && (
        <p className="text-xs text-red-600/80 italic leading-relaxed">{finding.gap_description}</p>
      )}

      {/* Evidence spans */}
      {finding.evidence_spans.length > 0 && (
        <div className="space-y-1.5 pt-0.5">
          {finding.evidence_spans.slice(0, 2).map((span, i) => (
            <div key={i} className="group">
              <blockquote className="border-l border-slate-300 pl-2 text-xs text-slate-500 italic leading-relaxed">
                "{span.text}"
                {span.page > 0 && (
                  <span className="not-italic text-slate-400 ml-1 tabular">p.{span.page}</span>
                )}
              </blockquote>
              {onCitationClick && span.document_id && (
                <button
                  onClick={() => onCitationClick(span.document_id, span.page, span.text)}
                  className="flex items-center gap-1 mt-0.5 ml-2 text-[11px] font-medium text-indigo-600 hover:text-indigo-700 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <ExternalLink size={10} />
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
