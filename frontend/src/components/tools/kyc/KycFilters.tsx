import { Field, FilterBar, inputClass } from '../../common/FilterBar';
import { Button } from '../../common/Button';
import type { KycFilters as Filters, KycStatus, RiskLevel, User } from '../../../types';
import { humanize } from '../../../utils/format';

const STATUSES: KycStatus[] = ['pending', 'in_review', 'approved', 'rejected', 'escalated'];
const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'];

interface Props {
  filters: Filters;
  reviewers: User[];
  searchTerm: string;
  onSearchTermChange: (value: string) => void;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
}

export function KycFilterBar({
  filters,
  reviewers,
  searchTerm,
  onSearchTermChange,
  onChange,
  onReset,
}: Props): JSX.Element {
  return (
    <FilterBar>
      <Field label="Search">
        <input
          type="search"
          value={searchTerm}
          placeholder="Customer, email or case ref"
          onChange={(event) => onSearchTermChange(event.target.value)}
          className={`${inputClass} w-56`}
        />
      </Field>
      <Field label="Status">
        <select
          value={filters.status ?? ''}
          onChange={(event) => onChange({ status: (event.target.value || undefined) as KycStatus })}
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
      <Field label="Risk level">
        <select
          value={filters.risk_level ?? ''}
          onChange={(event) =>
            onChange({ risk_level: (event.target.value || undefined) as RiskLevel })
          }
          className={inputClass}
        >
          <option value="">All levels</option>
          {RISK_LEVELS.map((level) => (
            <option key={level} value={level}>
              {humanize(level)}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Reviewer">
        <select
          value={filters.unassigned ? 'unassigned' : (filters.reviewer_id ?? '')}
          onChange={(event) => {
            const value = event.target.value;
            if (value === 'unassigned') {
              onChange({ unassigned: true, reviewer_id: undefined });
            } else {
              onChange({ unassigned: false, reviewer_id: value ? Number(value) : undefined });
            }
          }}
          className={inputClass}
        >
          <option value="">Anyone</option>
          <option value="unassigned">Unassigned</option>
          {reviewers.map((reviewer) => (
            <option key={reviewer.id} value={reviewer.id}>
              {reviewer.full_name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Submitted from">
        <input
          type="date"
          value={filters.submitted_from?.slice(0, 10) ?? ''}
          onChange={(event) =>
            onChange({ submitted_from: event.target.value ? `${event.target.value}T00:00:00` : undefined })
          }
          className={inputClass}
        />
      </Field>
      <Field label="Submitted to">
        <input
          type="date"
          value={filters.submitted_to?.slice(0, 10) ?? ''}
          onChange={(event) =>
            onChange({ submitted_to: event.target.value ? `${event.target.value}T23:59:59` : undefined })
          }
          className={inputClass}
        />
      </Field>
      <Button variant="secondary" size="sm" onClick={onReset}>
        Reset
      </Button>
    </FilterBar>
  );
}
