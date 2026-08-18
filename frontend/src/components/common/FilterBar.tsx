import type { ReactNode } from 'react';

/** Row of filter inputs shared by the three tool tables. */
export function FilterBar({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
      {children}
    </div>
  );
}

export function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <label className={`flex flex-col gap-1 text-xs font-medium text-slate-600 ${className ?? ''}`}>
      {label}
      {children}
    </label>
  );
}

export const inputClass =
  'rounded-md border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700 shadow-sm ' +
  'focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500';
