import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  side?: 'left' | 'right';
  className?: string;
  title?: string;
}

export function Sheet({
  open,
  onOpenChange,
  children,
  side = 'left',
  className,
}: SheetProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 transition-opacity"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Content panel */}
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative z-50 flex h-full w-72 flex-col bg-slate-950 text-slate-100 shadow-xl transition-transform duration-200 border-r border-slate-800',
          side === 'left' ? 'animate-in slide-in-from-left duration-200' : 'animate-in slide-in-from-right duration-200 ml-auto border-l border-slate-800',
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}

export function SheetClose({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-md p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors',
        className
      )}
      aria-label="Close"
    >
      <X className="h-4 w-4" />
    </button>
  );
}
