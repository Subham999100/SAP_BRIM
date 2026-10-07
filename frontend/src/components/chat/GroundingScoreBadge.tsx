import React, { useState } from 'react';
import { ShieldCheck, Info } from 'lucide-react';
import { Badge } from '../ui/badge';

interface GroundingScoreBadgeProps {
  score?: number;
}

export const GroundingScoreBadge: React.FC<GroundingScoreBadgeProps> = ({ score }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  if (score === undefined || score === null) return null;

  const pct = Math.round(score * 100);

  let variant: 'success' | 'warning' | 'destructive' = 'success';
  let label = 'High Evidence';
  if (pct < 65) {
    variant = 'destructive';
    label = 'Low Evidence';
  } else if (pct < 85) {
    variant = 'warning';
    label = 'Moderate Evidence';
  }

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={() => setShowTooltip((v) => !v)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="focus:outline-none"
        aria-label={`Grounding score: ${pct}%, ${label}`}
      >
        <Badge variant={variant} className="cursor-pointer gap-1 px-1.5 py-0.5 text-[10px]">
          <ShieldCheck className="w-3 h-3 shrink-0" />
          <span>Grounding: {pct}%</span>
          <Info className="w-2.5 h-2.5 opacity-60" />
        </Badge>
      </button>

      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-1.5 w-64 p-2.5 bg-slate-900 border border-slate-700/80 rounded-lg shadow-lg z-30 text-xs text-slate-300 pointer-events-none animate-in fade-in duration-100">
          <div className="font-semibold text-slate-100 mb-1 flex items-center justify-between text-[11px]">
            <span>Grounding Score ({pct}%)</span>
            <span className="text-[10px] font-normal px-1 py-0.2 bg-slate-800 rounded text-slate-300">
              {label}
            </span>
          </div>
          <p className="text-[10px] leading-relaxed text-slate-400">
            Calculated from multi-signal evidence evaluation: vector semantic similarity, reranker cross-scoring, query term coverage, and chunk support.
          </p>
        </div>
      )}
    </div>
  );
};
