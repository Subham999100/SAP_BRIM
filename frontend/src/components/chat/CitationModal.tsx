import React from 'react';
import { X, FileText, Award, Hash, BookOpen, Globe, Shield } from 'lucide-react';
import type { Citation, WebSource } from '../../types';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="citations-modal-title"
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-800 bg-slate-950/70 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-md bg-slate-850 text-sap-400 border border-slate-800">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 id="citations-modal-title" className="text-sm font-semibold text-slate-100">
                Sources & Citations
              </h3>
              <p className="text-[11px] text-slate-400">
                {hasCitations
                  ? `${citations.length} verified SAP documentation ${citations.length === 1 ? 'source' : 'sources'}`
                  : `${webSources.length} verified web ${webSources.length === 1 ? 'reference' : 'references'}`}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1 text-slate-200">
          {/* Knowledge Base Citations */}
          {hasCitations && (
            <div className="space-y-3">
              {citations.map((c, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2.5"
                >
                  {/* Citation Meta Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-850 pb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded bg-slate-900 border border-slate-700/80 text-sap-300 text-[11px] font-bold flex items-center justify-center shrink-0">
                        {idx + 1}
                      </span>
                      <div className="flex items-center gap-1.5 min-w-0">
                        <BookOpen className="w-3.5 h-3.5 text-sap-400 shrink-0" />
                        <span className="text-xs font-medium text-slate-200 truncate" title={c.document}>
                          {c.document}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant="outline" className="text-[10px] gap-0.5 text-emerald-400 border-emerald-800/40 bg-emerald-950/20">
                        <Hash className="w-2.5 h-2.5" />
                        Page {c.page}
                      </Badge>
                      {c.score > 0 && (
                        <Badge variant="sap" className="text-[10px] gap-0.5">
                          <Award className="w-2.5 h-2.5" />
                          {Math.round(c.score * 100)}% match
                        </Badge>
                      )}
                    </div>
                  </div>

                  {c.section && (
                    <div className="text-[11px] text-slate-400">
                      Section: <span className="text-slate-300 font-medium">{c.section}</span>
                    </div>
                  )}

                  {/* Excerpt */}
                  <div>
                    <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                      Verified Excerpt
                    </span>
                    <div className="p-2.5 bg-slate-900/90 border border-slate-800/90 rounded-md text-xs leading-relaxed text-slate-300 font-mono">
                      "{c.snippet}"
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Web Sources */}
          {hasWebSources && (
            <div className="space-y-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Authoritative Web References
              </span>
              {webSources.map((w, idx) => (
                <a
                  key={idx}
                  href={w.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="text-xs font-medium text-cyan-300 group-hover:underline truncate">
                        {w.title}
                      </span>
                    </div>
                    <Badge variant="outline" className="text-[10px] shrink-0 ml-2">
                      {w.domain}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {w.snippet}
                  </p>
                </a>
              ))}
            </div>
          )}

          {/* Security & Document Privacy Note */}
          <div className="flex items-start gap-2 p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-xs text-slate-400 leading-relaxed">
            <Shield className="w-3.5 h-3.5 shrink-0 text-sap-400 mt-0.5" />
            <span>
              <strong>Document Privacy:</strong> Original SAP enterprise PDF documentation is indexed securely in the developer-managed private knowledge base. Direct file downloads and storage paths are restricted.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end shrink-0">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
