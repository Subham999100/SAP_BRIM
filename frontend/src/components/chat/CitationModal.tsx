import React from 'react';
import { X, FileText, ShieldAlert, Award, Hash, BookOpen, Globe } from 'lucide-react';
import type { Citation, WebSource } from '../../types';

interface CitationModalProps {
  citations?: Citation[];
  webSources?: WebSource[];
  isOpen: boolean;
  onClose: () => void;
}

export const CitationModal: React.FC<CitationModalProps> = ({
  citations = [],
  webSources = [],
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const hasCitations = citations.length > 0;
  const hasWebSources = webSources.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/90 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/70 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sap-600/20 text-sap-400 border border-sap-500/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Sources & Citations</h3>
              <p className="text-xs text-slate-400">
                {hasCitations
                  ? `${citations.length} verified private SAP documentation ${citations.length === 1 ? 'source' : 'sources'}`
                  : `${webSources.length} verified authoritative web ${webSources.length === 1 ? 'reference' : 'references'}`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {/* Knowledge Base Citations */}
          {hasCitations && (
            <div className="space-y-4">
              {citations.map((c, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition space-y-3"
                >
                  {/* Citation Meta Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-850 pb-2.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded-md bg-sap-600/30 border border-sap-500/40 text-sap-300 text-xs font-bold flex items-center justify-center shrink-0">
                        {idx + 1}
                      </span>
                      <div className="flex items-center gap-1.5 min-w-0">
                        <BookOpen className="w-3.5 h-3.5 text-sap-400 shrink-0" />
                        <span className="text-xs font-semibold text-slate-200 truncate" title={c.document}>
                          {c.document}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded-md border border-emerald-800/40">
                        <Hash className="w-3 h-3" />
                        Page {c.page}
                      </span>
                      {c.score > 0 && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-sap-300 bg-sap-950/50 px-2 py-0.5 rounded-md border border-sap-800/40">
                          <Award className="w-3 h-3 text-sap-400" />
                          {Math.round(c.score * 100)}% match
                        </span>
                      )}
                    </div>
                  </div>

                  {c.section && (
                    <div className="text-[11px] text-slate-400 font-medium">
                      Section: <span className="text-slate-300">{c.section}</span>
                    </div>
                  )}

                  {/* Excerpt */}
                  <div>
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                      Verified Excerpt
                    </span>
                    <div className="p-3 bg-slate-900/90 border border-slate-800/80 rounded-lg text-xs leading-relaxed text-slate-300 font-mono">
                      "{c.snippet}"
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Web Sources */}
          {hasWebSources && (
            <div className="space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 block">
                Authoritative Web Sources
              </span>
              {webSources.map((w, idx) => (
                <a
                  key={idx}
                  href={w.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-cyan-500/40 transition group"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="text-xs font-semibold text-cyan-300 group-hover:text-cyan-200 truncate">
                        {w.title}
                      </span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50 shrink-0 ml-2">
                      {w.domain}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {w.snippet}
                  </p>
                </a>
              ))}
            </div>
          )}

          {/* Security & Document Privacy Note */}
          <div className="flex items-start gap-2.5 p-3.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300/90 leading-relaxed">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <span>
              <strong>Document Privacy:</strong> Original SAP enterprise PDF manuals are indexed securely in the developer-managed private knowledge base. Direct file downloads and storage paths are restricted.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
