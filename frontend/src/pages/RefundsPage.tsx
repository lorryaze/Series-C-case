import { useMemo, useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card, StatCard } from '../components/common/Card';
import { Pagination, Table } from '../components/common/Table';
import type { Column } from '../components/common/Table';
import { StatusBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Field, FilterBar, inputClass } from '../components/common/FilterBar';
import { RefundTrendChart } from '../components/tools/refunds/RefundTrendChart';
import { RefundDetailModal } from '../components/tools/refunds/RefundDetailModal';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useRefundSummary, useRefundTrend, useRefunds } from '../hooks/useRefunds';
import type { RefundFilters, RefundListItem, RefundReason, RefundStatus } from '../types';
import { formatCurrency, formatDate, formatHours, humanize } from '../utils/format';

const PAGE_SIZE = 15;
const STATUSES: RefundStatus[] = ['pending', 'approved', 'rejected', 'info_requested'];
const REASONS: RefundReason[] = [
  'duplicate_charge',
  'service_not_rendered',
  'fraud',
  'customer_request',
  'processing_error',
];

export function RefundsPage(): JSX.Element {
  const [filters, setFilters] = useState<RefundFilters>({ page: 1, page_size: PAGE_SIZE });
  const [searchTerm, setSearchTerm] = useState('');
  const [openRefundId, setOpenRefundId] = useState<number | null>(null);

  const debouncedSearch = useDebouncedValue(searchTerm);
  const effectiveFilters = useMemo<RefundFilters>(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch],
  );

  const { data: summary } = useRefundSummary();
  const { data: trend = [] } = useRefundTrend(30);
  const { data, isLoading } = useRefunds(effectiveFilters);

  const patchFilters = (patch: Partial<RefundFilters>) =>
    setFilters((current) => ({ ...current, ...patch, page: 1 }));

  const columns: Column<RefundListItem>[] = [
    {
      key: 'reference',
      header: 'Refund',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-900">{row.refund_reference}</p>
          <p className="text-xs text-slate-500">{row.customer_name}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (row) => <span className="font-medium">{formatCurrency(row.amount)}</span>,
    },
    { key: 'reason', header: 'Reason', render: (row) => humanize(row.reason) },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'requested', header: 'Requested', render: (row) => formatDate(row.requested_at) },
    { key: 'processed', header: 'Processed', render: (row) => formatDate(row.processed_at) },
  ];

  return (
    <>
      <Header title="Refunds Dashboard" subtitle="Dispute triage, approvals and payout volume" />
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatCard
            label="Total refunds"
            value={summary?.total_count ?? 0}
            hint={summary ? formatCurrency(summary.total_amount) : undefined}
            active={filters.status === undefined}
            onClick={() => patchFilters({ status: undefined })}
          />
          <StatCard
            label="Pending"
            value={summary?.pending_count ?? 0}
            hint={summary ? formatCurrency(summary.pending_amount) : undefined}
            active={filters.status === 'pending'}
            onClick={() => patchFilters({ status: 'pending' })}
          />
          <StatCard
            label="Approved"
            value={summary?.approved_count ?? 0}
            hint={summary ? formatCurrency(summary.approved_amount) : undefined}
            active={filters.status === 'approved'}
            onClick={() => patchFilters({ status: 'approved' })}
          />
          <StatCard
            label="Rejected"
            value={summary?.rejected_count ?? 0}
            hint={summary ? formatCurrency(summary.rejected_amount) : undefined}
            active={filters.status === 'rejected'}
            onClick={() => patchFilters({ status: 'rejected' })}
          />
          <StatCard
            label="Avg processing"
            value={formatHours(summary?.average_processing_hours ?? null)}
            hint={`${summary?.info_requested_count ?? 0} awaiting info`}
          />
        </div>

        <Card title="Refund volume · last 30 days">
          <RefundTrendChart points={trend} />
        </Card>

        <Card className="overflow-hidden">
          <div className="-m-4">
            <FilterBar>
              <Field label="Search">
                <input
                  type="search"
                  value={searchTerm}
                  placeholder="Customer, refund or transaction ref"
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className={`${inputClass} w-60`}
                />
              </Field>
              <Field label="Status">
                <select
                  value={filters.status ?? ''}
                  onChange={(event) =>
                    patchFilters({ status: (event.target.value || undefined) as RefundStatus })
                  }
                  className={inputClass}
                >
                  <option value="">All statuses</option>
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {humanize(status)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Reason">
                <select
                  value={filters.reason ?? ''}
                  onChange={(event) =>
                    patchFilters({ reason: (event.target.value || undefined) as RefundReason })
                  }
                  className={inputClass}
                >
                  <option value="">All reasons</option>
                  {REASONS.map((reason) => (
                    <option key={reason} value={reason}>
                      {humanize(reason)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Min amount">
                <input
                  type="number"
                  min={0}
                  value={filters.min_amount ?? ''}
                  onChange={(event) => patchFilters({ min_amount: event.target.value || undefined })}
                  className={`${inputClass} w-24`}
                />
              </Field>
              <Field label="Max amount">
                <input
                  type="number"
                  min={0}
                  value={filters.max_amount ?? ''}
                  onChange={(event) => patchFilters({ max_amount: event.target.value || undefined })}
                  className={`${inputClass} w-24`}
                />
              </Field>
              <Field label="Requested from">
                <input
                  type="date"
                  value={filters.requested_from?.slice(0, 10) ?? ''}
                  onChange={(event) =>
                    patchFilters({
                      requested_from: event.target.value ? `${event.target.value}T00:00:00` : undefined,
                    })
                  }
                  className={inputClass}
                />
              </Field>
              <Field label="Requested to">
                <input
                  type="date"
                  value={filters.requested_to?.slice(0, 10) ?? ''}
                  onChange={(event) =>
                    patchFilters({
                      requested_to: event.target.value ? `${event.target.value}T23:59:59` : undefined,
                    })
                  }
                  className={inputClass}
                />
              </Field>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setFilters({ page: 1, page_size: PAGE_SIZE });
                  setSearchTerm('');
                }}
              >
                Reset
              </Button>
            </FilterBar>

            <Table
              columns={columns}
              rows={data?.items ?? []}
              rowKey={(row) => row.id}
              isLoading={isLoading}
              onRowClick={(row) => setOpenRefundId(row.id)}
            />
            <Pagination
              page={data?.page ?? 1}
              pages={data?.pages ?? 1}
              total={data?.total ?? 0}
              onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            />
          </div>
        </Card>
      </div>

      {openRefundId !== null && (
        <RefundDetailModal refundId={openRefundId} onClose={() => setOpenRefundId(null)} />
      )}
    </>
  );
}
