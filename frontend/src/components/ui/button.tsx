import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'sap';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', disabled, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-400 disabled:pointer-events-none disabled:opacity-50 select-none';

    const variants = {
      default: 'bg-slate-800 text-slate-100 hover:bg-slate-700 active:bg-slate-800/90 border border-slate-700/60 shadow-xs',
      secondary: 'bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-slate-100 border border-slate-800',
      outline: 'border border-slate-700/80 bg-transparent text-slate-300 hover:bg-slate-800/80 hover:text-slate-100',
      ghost: 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60',
      destructive: 'bg-rose-950/50 text-rose-300 border border-rose-800/50 hover:bg-rose-900/50 hover:text-rose-200',
      sap: 'bg-sap-600 text-white hover:bg-sap-500 active:bg-sap-700 border border-sap-500/50 shadow-xs',
    };

    const sizes = {
      default: 'h-8 px-3 py-1.5',
      sm: 'h-7 px-2.5 text-[11px]',
      lg: 'h-9 px-4 text-sm',
      icon: 'h-8 w-8 p-0',
    };

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
