import clsx from 'clsx';
import type { ReactNode } from 'react';
import { humanize } from '../../utils/format';

export type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  info: 'bg-brand-50 text-brand-700 ring-brand-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-700 ring-amber-200',
  danger: 'bg-rose-50 text-rose-700 ring-rose-200',
};

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}

const KYC_TONES: Record<string, BadgeTone> = {
  pending: 'neutral',
  in_review: 'info',
  approved: 'success',
  rejected: 'danger',
  escalated: 'warning',
  info_requested: 'warning',
};

const RISK_TONES: Record<string, BadgeTone> = {
  low: 'success',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
};

/** Status pill shared by the KYC queue and the refunds table. */
export function StatusBadge({ status }: { status: string }): JSX.Element {
  return <Badge tone={KYC_TONES[status] ?? 'neutral'}>{humanize(status)}</Badge>;
}

export function RiskBadge({ level, score }: { level: string; score?: number }): JSX.Element {
  return (
    <Badge tone={RISK_TONES[level] ?? 'neutral'}>
      {humanize(level)}
      {score === undefined ? '' : ` · ${score}`}
    </Badge>
  );
}
