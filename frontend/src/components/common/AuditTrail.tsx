import type { AuditLogEntry } from '../../types';
import { Button } from './Button';
import { formatDateTime, humanize } from '../../utils/format';

interface AuditPagination {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

/**
 * Renders the shared audit trail. All three tools write to the same backend
 * table, so one component covers KYC decisions, refund approvals and flag changes.
 * Pass ``pagination`` when the trail is served page by page.
 */
export function AuditTrail({
  entries,
  emptyMessage = 'No audit entries yet.',
  pagination,
}: {
  entries: AuditLogEntry[];
  emptyMessage?: string;
  pagination?: AuditPagination;
}): JSX.Element {
  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <>
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
      {pagination && pagination.pages > 1 && (
        <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
          <p className="text-xs text-slate-500">
            Page {pagination.page} of {pagination.pages} · {pagination.total} entries
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={pagination.page <= 1}
              onClick={() => pagination.onPageChange(pagination.page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={pagination.page >= pagination.pages}
              onClick={() => pagination.onPageChange(pagination.page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
