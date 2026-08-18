import type { ReactNode } from 'react';

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <section
      className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className ?? ''}`}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          {title && <h2 className="text-sm font-semibold text-slate-700">{title}</h2>}
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

/** Metric tile used by the KYC queue counts and the refunds summary. */
export function StatCard({
  label,
  value,
  hint,
  onClick,
  active = false,
}: {
  label: string;
  value: string | number;
  hint?: string;
  onClick?: () => void;
  active?: boolean;
}): JSX.Element {
  const interactive = Boolean(onClick);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      className={[
        'rounded-lg border bg-white p-4 text-left shadow-sm transition',
        interactive ? 'hover:border-brand-400 hover:shadow' : 'cursor-default',
        active ? 'border-brand-500 ring-1 ring-brand-500' : 'border-slate-200',
      ].join(' ')}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </button>
  );
}
