import type { AuditLogEntry } from '../../types';
import { formatDateTime, humanize } from '../../utils/format';

/**
 * Renders the shared audit trail. All three tools write to the same backend
 * table, so one component covers KYC decisions, refund approvals and flag changes.
 */
export function AuditTrail({
  entries,
  emptyMessage = 'No audit entries yet.',
}: {
  entries: AuditLogEntry[];
  emptyMessage?: string;
}): JSX.Element {
  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <ol className="space-y-3">
      {entries.map((entry) => (
        <li key={entry.id} className="border-l-2 border-brand-200 pl-3">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
            <span className="font-medium">{humanize(entry.action)}</span>
            {entry.field && <span className="text-slate-500">· {entry.field}</span>}
            {entry.previous_value !== null && (
              <span className="text-slate-500">
                {humanize(entry.previous_value)} → {humanize(entry.new_value)}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            {entry.actor_email} · {formatDateTime(entry.created_at)}
          </p>
          {entry.reason && <p className="mt-1 text-sm text-slate-600">“{entry.reason}”</p>}
        </li>
      ))}
    </ol>
  );
}
