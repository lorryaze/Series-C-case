import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  isLoading?: boolean;
  emptyMessage?: string;
}

/** Generic data table: every tool renders its rows through this component. */
export function Table<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isLoading = false,
  emptyMessage = 'No records match the current filters.',
}: TableProps<T>): JSX.Element {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 ${column.className ?? ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {isLoading && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500">
                Loading…
              </td>
            </tr>
          )}
          {!isLoading && rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500">
                {emptyMessage}
              </td>
            </tr>
          )}
          {!isLoading &&
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? 'cursor-pointer hover:bg-brand-50/60' : undefined}
              >
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-3 text-slate-700 ${column.className ?? ''}`}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  onPageChange,
}: {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}): JSX.Element {
  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span>
        Page {page} of {Math.max(pages, 1)} · {total} records
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded border border-slate-300 px-2 py-1 disabled:text-slate-300"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded border border-slate-300 px-2 py-1 disabled:text-slate-300"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
