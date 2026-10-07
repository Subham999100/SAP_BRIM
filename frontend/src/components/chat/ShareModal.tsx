import React, { useState } from 'react';
import { X, Copy, Check, Share2, Globe, Shield } from 'lucide-react';
import type { Chat } from '../../types';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

interface ShareModalProps {
  chat: Chat | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({ chat, isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !chat) return null;

  const shareUrl = `${window.location.origin}/#share=${chat.id}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-modal-title"
        className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl p-5 text-slate-100 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3.5 right-3.5 p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2.5 mb-3.5">
          <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700/80 text-sap-400 flex items-center justify-center">
            <Share2 className="w-4 h-4" />
          </div>
          <div>
            <h2 id="share-modal-title" className="text-sm font-semibold text-slate-100">
              Share Conversation
            </h2>
            <p className="text-[11px] text-slate-400">Read-only link to this SAP session</p>
          </div>
        </div>

        {/* Chat Title Preview */}
        <div className="mb-3.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center gap-2">
          <Globe className="w-3.5 h-3.5 text-sap-400 shrink-0" />
          <span className="text-xs font-medium text-slate-200 truncate">{chat.title}</span>
        </div>

        {/* Copy Link Input & Button */}
        <div className="mb-3.5">
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Public Link
          </label>
          <div className="flex items-center gap-2">
            <Input
              type="text"
              readOnly
              value={shareUrl}
              className="flex-1 bg-slate-950 border-slate-800 text-xs font-mono text-slate-300"
            />
            <Button
              type="button"
              variant={copied ? 'secondary' : 'sap'}
              size="sm"
              onClick={handleCopy}
              className="gap-1.5 shrink-0"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Footer Note */}
        <div className="pt-2.5 border-t border-slate-800 flex items-center gap-2 text-[11px] text-slate-500">
          <Shield className="w-3.5 h-3.5 text-sap-400 shrink-0" />
          <span>Anyone with this link will have view-only access.</span>
        </div>
      </div>
    </div>
  );
};
