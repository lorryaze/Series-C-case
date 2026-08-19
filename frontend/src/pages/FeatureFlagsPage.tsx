import { useMemo, useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card } from '../components/common/Card';
import { Pagination, Table } from '../components/common/Table';
import type { Column } from '../components/common/Table';
import { Button } from '../components/common/Button';
import { Field, FilterBar, inputClass } from '../components/common/FilterBar';
import { CreateFlagModal } from '../components/tools/feature-flags/CreateFlagModal';
import { DeleteFlagDialog } from '../components/tools/feature-flags/DeleteFlagDialog';
import { FlagEnvironmentControls } from '../components/tools/feature-flags/FlagEnvironmentControls';
import { FlagHistoryModal } from '../components/tools/feature-flags/FlagHistoryModal';
import { useAuth } from '../context/AuthContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useFeatureFlags } from '../hooks/useFeatureFlags';
import type { FeatureFlag, FeatureFlagFilters, FlagEnvironment } from '../types';
import { formatDateTime, humanize } from '../utils/format';

const PAGE_SIZE = 20;
const ENVIRONMENTS: FlagEnvironment[] = ['production', 'staging', 'development'];

export function FeatureFlagsPage(): JSX.Element {
  const { canAdminister } = useAuth();
  const [filters, setFilters] = useState<FeatureFlagFilters>({ page: 1, page_size: PAGE_SIZE });
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [historyFlag, setHistoryFlag] = useState<FeatureFlag | null>(null);
  const [flagToDelete, setFlagToDelete] = useState<FeatureFlag | null>(null);

  const debouncedSearch = useDebouncedValue(searchTerm);
  const effectiveFilters = useMemo<FeatureFlagFilters>(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch],
  );

  const { data, isLoading } = useFeatureFlags(effectiveFilters);

  const patchFilters = (patch: Partial<FeatureFlagFilters>) =>
    setFilters((current) => ({ ...current, ...patch, page: 1 }));

  const columns: Column<FeatureFlag>[] = [
    {
      key: 'flag',
      header: 'Flag',
      render: (row) => (
        <div className="max-w-sm">
          <p className="font-medium text-slate-900">{row.name}</p>
          <code className="text-xs text-brand-700">{row.key}</code>
          <p className="mt-1 text-xs text-slate-500">{row.description}</p>
        </div>
      ),
    },
    {
      key: 'environments',
      header: 'Environments · rollout',
      render: (row) => <FlagEnvironmentControls flag={row} editable={canAdminister} />,
    },
    {
      key: 'modified',
      header: 'Last modified',
      render: (row) => (
        <div className="text-xs text-slate-500">
          <p className="text-slate-700">{formatDateTime(row.updated_at)}</p>
          <p>{row.modified_by?.full_name ?? 'System'}</p>
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="sm" onClick={() => setHistoryFlag(row)}>
            History
          </Button>
          {canAdminister && (
            <Button variant="ghost" size="sm" onClick={() => setFlagToDelete(row)}>
              Delete
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <Header
        title="Feature Flags"
        subtitle="Release control per environment with an audited changelog"
      />
      <div className="space-y-6 p-6">
        {!canAdminister && (
          <p className="rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-800">
            Feature flag changes require an admin account. This view is read-only.
          </p>
        )}

        <Card className="overflow-hidden">
          <div className="-m-4">
            <FilterBar>
              <Field label="Search">
                <input
                  type="search"
                  value={searchTerm}
                  placeholder="Name, key or description"
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className={`${inputClass} w-60`}
                />
              </Field>
              <Field label="Environment">
                <select
                  value={filters.environment ?? ''}
                  onChange={(event) =>
                    patchFilters({
                      environment: (event.target.value || undefined) as FlagEnvironment,
                    })
                  }
                  className={inputClass}
                >
                  <option value="">All environments</option>
                  {ENVIRONMENTS.map((environment) => (
                    <option key={environment} value={environment}>
                      {humanize(environment)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="State">
                <select
                  value={filters.enabled === undefined ? '' : String(filters.enabled)}
                  onChange={(event) =>
                    patchFilters({
                      enabled: event.target.value === '' ? undefined : event.target.value === 'true',
                    })
                  }
                  className={inputClass}
                >
                  <option value="">Any state</option>
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
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
              <div className="ml-auto">
                <Button size="sm" disabled={!canAdminister} onClick={() => setIsCreating(true)}>
                  New flag
                </Button>
              </div>
            </FilterBar>

            <Table
              columns={columns}
              rows={data?.items ?? []}
              rowKey={(row) => row.id}
              isLoading={isLoading}
              emptyMessage="No flags match the current filters."
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

      {isCreating && <CreateFlagModal onClose={() => setIsCreating(false)} />}
      {historyFlag && (
        <FlagHistoryModal
          flagId={historyFlag.id}
          flagName={historyFlag.name}
          onClose={() => setHistoryFlag(null)}
        />
      )}
      {flagToDelete && (
        <DeleteFlagDialog flag={flagToDelete} onClose={() => setFlagToDelete(null)} />
      )}
    </>
  );
}
