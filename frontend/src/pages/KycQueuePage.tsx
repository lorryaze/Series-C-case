import { useMemo, useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card, StatCard } from '../components/common/Card';
import { Pagination, Table } from '../components/common/Table';
import type { Column } from '../components/common/Table';
import { RiskBadge, StatusBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { inputClass } from '../components/common/FilterBar';
import { KycFilterBar } from '../components/tools/kyc/KycFilters';
import { KycDetailModal } from '../components/tools/kyc/KycDetailModal';
import { useAuth } from '../context/AuthContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useKycBulkAssign, useKycCounts, useKycReviews } from '../hooks/useKyc';
import { useReviewers } from '../hooks/useUsers';
import type { KycFilters, KycReviewListItem, KycStatus } from '../types';
import { formatDate, humanize } from '../utils/format';

const PAGE_SIZE = 15;

export function KycQueuePage(): JSX.Element {
  const { canReview } = useAuth();
  const [filters, setFilters] = useState<KycFilters>({ page: 1, page_size: PAGE_SIZE });
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [openReviewId, setOpenReviewId] = useState<number | null>(null);
  const [bulkReviewerId, setBulkReviewerId] = useState('');

  const debouncedSearch = useDebouncedValue(searchTerm);
  const effectiveFilters = useMemo<KycFilters>(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch],
  );

  const { data: counts } = useKycCounts();
  const { data, isLoading } = useKycReviews(effectiveFilters);
  const { data: reviewers = [] } = useReviewers(canReview);
  const bulkAssign = useKycBulkAssign();

  const patchFilters = (patch: Partial<KycFilters>) =>
    setFilters((current) => ({ ...current, ...patch, page: 1 }));

  const toggleSelected = (id: number) =>
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );

  const rows = data?.items ?? [];

  const columns: Column<KycReviewListItem>[] = [
    ...(canReview
      ? [
          {
            key: 'select',
            header: '',
            className: 'w-8',
            render: (row: KycReviewListItem) => (
              <input
                type="checkbox"
                checked={selectedIds.includes(row.id)}
                onClick={(event) => event.stopPropagation()}
                onChange={() => toggleSelected(row.id)}
                aria-label={`Select ${row.case_reference}`}
              />
            ),
          },
        ]
      : []),
    {
      key: 'customer',
      header: 'Customer',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-900">{row.customer_name}</p>
          <p className="text-xs text-slate-500">{row.case_reference}</p>
        </div>
      ),
    },
    { key: 'submitted', header: 'Submitted', render: (row) => formatDate(row.submitted_at) },
    {
      key: 'risk',
      header: 'Risk',
      render: (row) => <RiskBadge level={row.risk_level} score={row.risk_score} />,
    },
    {
      key: 'document',
      header: 'Document',
      render: (row) => humanize(row.primary_document_type),
    },
    {
      key: 'reviewer',
      header: 'Reviewer',
      render: (row) => row.assigned_reviewer?.full_name ?? <span className="text-slate-400">Unassigned</span>,
    },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge status={row.status} /> },
  ];

  const statusCards: Array<{ label: string; value: number; status?: KycStatus }> = [
    { label: 'Pending', value: counts?.pending ?? 0, status: 'pending' },
    { label: 'In review', value: counts?.in_review ?? 0, status: 'in_review' },
    { label: 'Approved', value: counts?.approved ?? 0, status: 'approved' },
    { label: 'Rejected', value: counts?.rejected ?? 0, status: 'rejected' },
    { label: 'Escalated', value: counts?.escalated ?? 0, status: 'escalated' },
    { label: 'Total cases', value: counts?.total ?? 0 },
  ];

  return (
    <>
      <Header
        title="KYC Review Queue"
        subtitle="Compliance onboarding decisions with a full audit trail"
      />
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {statusCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              active={card.status ? filters.status === card.status : filters.status === undefined}
              onClick={() => patchFilters({ status: card.status })}
            />
          ))}
        </div>

        <Card className="overflow-hidden" >
          <div className="-m-4">
            <KycFilterBar
              filters={filters}
              reviewers={reviewers}
              searchTerm={searchTerm}
              onSearchTermChange={setSearchTerm}
              onChange={patchFilters}
              onReset={() => {
                setFilters({ page: 1, page_size: PAGE_SIZE });
                setSearchTerm('');
              }}
            />

            {canReview && selectedIds.length > 0 && (
              <div className="flex items-center gap-3 border-b border-brand-200 bg-brand-50 px-4 py-2 text-sm">
                <span className="font-medium text-brand-800">
                  {selectedIds.length} case{selectedIds.length === 1 ? '' : 's'} selected
                </span>
                <select
                  value={bulkReviewerId}
                  onChange={(event) => setBulkReviewerId(event.target.value)}
                  className={inputClass}
                >
                  <option value="">Assign to…</option>
                  {reviewers.map((reviewer) => (
                    <option key={reviewer.id} value={reviewer.id}>
                      {reviewer.full_name}
                    </option>
                  ))}
                </select>
                <Button
                  size="sm"
                  disabled={!bulkReviewerId || bulkAssign.isPending}
                  onClick={async () => {
                    await bulkAssign.mutateAsync({
                      reviewIds: selectedIds,
                      reviewerId: Number(bulkReviewerId),
                    });
                    setSelectedIds([]);
                    setBulkReviewerId('');
                  }}
                >
                  Assign
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>
                  Clear
                </Button>
              </div>
            )}

            <Table
              columns={columns}
              rows={rows}
              rowKey={(row) => row.id}
              isLoading={isLoading}
              onRowClick={(row) => setOpenReviewId(row.id)}
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

      {openReviewId !== null && (
        <KycDetailModal reviewId={openReviewId} onClose={() => setOpenReviewId(null)} />
      )}
    </>
  );
}
