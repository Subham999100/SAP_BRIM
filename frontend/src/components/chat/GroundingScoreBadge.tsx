import React, { useState } from 'react';
import { ShieldCheck, Info } from 'lucide-react';

interface GroundingScoreBadgeProps {
  score?: number;
}

export const GroundingScoreBadge: React.FC<GroundingScoreBadgeProps> = ({ score }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  if (score === undefined || score === null) return null;

  const pct = Math.round(score * 100);

  // Confidence tiers
  let colorStyles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  let label = 'High Evidence';
  if (pct < 65) {
    colorStyles = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    label = 'Low Evidence';
  } else if (pct < 85) {
    colorStyles = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    label = 'Moderate Evidence';
  }

  return (
    <div className="relative inline-flex items-center">
      <button
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${colorStyles} transition hover:opacity-90`}
      >
        <ShieldCheck className="w-3.5 h-3.5" />
        <span>Grounding: {pct}%</span>
        <Info className="w-3 h-3 opacity-60 ml-0.5" />
      </button>

      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-slate-950 border border-slate-700 rounded-xl shadow-xl z-30 text-xs text-slate-300 pointer-events-none animate-in fade-in zoom-in-95">
          <div className="font-semibold text-slate-100 mb-1 flex items-center justify-between">
            <span>Grounding Score ({pct}%)</span>
            <span className="text-[10px] font-normal px-1.5 py-0.5 bg-slate-800 rounded">{label}</span>
          </div>
          <p className="text-[11px] leading-relaxed text-slate-400">
            Calculated from multi-signal evidence evaluation: vector semantic similarity, reranker cross-scoring, query term coverage, and multi-chunk support.
          </p>
        </div>
      )}
    </div>
  );
};
