import type { ObligationFinding } from "@/lib/types";
import { verdictIcon, verdictColor, riskBadgeClass, cn } from "@/lib/utils";

interface Props {
  finding: ObligationFinding;
}

export default function FindingCard({ finding }: Props) {
  const borderColor =
    finding.verdict === "met"
      ? "border-emerald-500/40"
      : finding.verdict === "partially_met"
      ? "border-amber-500/40"
      : finding.verdict === "unmet"
      ? "border-red-500/40"
      : "border-slate-600";

  return (
    <div className={cn("border-l-2 pl-3 py-2 space-y-1.5", borderColor)}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none">{verdictIcon(finding.verdict)}</span>
          <span className="text-xs font-semibold text-slate-300">
            Art.{finding.article} §{finding.paragraph}
          </span>
          <span
            className={cn(
              "text-[10px] px-1.5 py-0.5 rounded border font-medium",
              riskBadgeClass(finding.risk_level)
            )}
          >
            {finding.risk_level}
          </span>
        </div>
        <span className={cn("text-[11px] font-medium", verdictColor(finding.verdict))}>
          {finding.verdict.replace("_", " ")}
        </span>
      </div>

      {/* Rationale */}
      <p className="text-[12px] text-slate-400 leading-relaxed">{finding.rationale}</p>

      {/* Gap */}
      {finding.gap_description && (
        <p className="text-[11px] text-red-400/80 italic">{finding.gap_description}</p>
      )}

      {/* Evidence quotes */}
      {finding.evidence_spans.length > 0 && (
        <div className="space-y-1 pt-0.5">
          {finding.evidence_spans.slice(0, 2).map((span, i) => (
            <blockquote
              key={i}
              className="border-l border-slate-600 pl-2 text-[11px] text-slate-500 italic"
            >
              "{span.text}"
              {span.page > 0 && (
                <span className="not-italic text-slate-600 ml-1">p.{span.page}</span>
              )}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  );
}
