import * as React from 'react';
import { cn } from '../../lib/utils';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  fallback: string;
}

export function Avatar({ className, fallback, ...props }: AvatarProps) {
  return (
    <div
      className={cn(
        'relative flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-700/80 bg-slate-800 text-[11px] font-medium text-slate-200 select-none',
        className
      )}
      {...props}
    >
      <span>{fallback}</span>
    </div>
  );
}
