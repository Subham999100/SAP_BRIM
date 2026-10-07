import * as React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'sap' | 'success' | 'warning' | 'destructive';
}

export function Badge({
  className,
  variant = 'default',
  ...props
}: BadgeProps) {
  const variants = {
    default: 'bg-slate-800 text-slate-200 border-slate-700/60',
    secondary: 'bg-slate-900 text-slate-300 border-slate-800',
    outline: 'bg-transparent text-slate-300 border-slate-700/80',
    sap: 'bg-sap-950/70 text-sap-300 border-sap-700/50',
    success: 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50',
    warning: 'bg-amber-950/60 text-amber-300 border-amber-700/50',
    destructive: 'bg-rose-950/60 text-rose-300 border-rose-700/50',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-semibold tracking-wide transition-colors',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
