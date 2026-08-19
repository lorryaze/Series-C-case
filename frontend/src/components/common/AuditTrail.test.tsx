import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AuditTrail } from './AuditTrail';
import type { AuditLogEntry } from '../../types';

function entry(overrides: Partial<AuditLogEntry> = {}): AuditLogEntry {
  return {
    id: 1,
    entity_type: 'kyc_review',
    entity_id: 7,
    action: 'status_changed',
    field: 'status',
    previous_value: 'in_review',
    new_value: 'approved',
    reason: 'Documents match the applicant',
    actor_id: 1,
    actor_email: 'reviewer@fintech.com',
    created_at: '2026-08-18T13:18:00Z',
    ...overrides,
  };
}

describe('AuditTrail', () => {
  it('shows what changed, who did it and why', () => {
    render(<AuditTrail entries={[entry()]} />);

    expect(screen.getByText('Status Changed')).toBeInTheDocument();
    expect(screen.getByText(/In Review\s*→\s*Approved/)).toBeInTheDocument();
    expect(screen.getByText(/reviewer@fintech.com/)).toBeInTheDocument();
    expect(screen.getByText(/Documents match the applicant/)).toBeInTheDocument();
  });

  it('renders the empty state instead of an empty list', () => {
    render(<AuditTrail entries={[]} emptyMessage="No decisions recorded yet." />);

    expect(screen.getByText('No decisions recorded yet.')).toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('hides pagination controls for a single page', () => {
    render(
      <AuditTrail
        entries={[entry()]}
        pagination={{ page: 1, pages: 1, total: 1, onPageChange: vi.fn() }}
      />,
    );

    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument();
  });

  it('pages through a long trail and disables the boundaries', async () => {
    const onPageChange = vi.fn();
    const { rerender } = render(
      <AuditTrail entries={[entry()]} pagination={{ page: 1, pages: 3, total: 60, onPageChange }} />,
    );

    expect(screen.getByText('Page 1 of 3 · 60 entries')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(onPageChange).toHaveBeenCalledWith(2);

    rerender(
      <AuditTrail entries={[entry()]} pagination={{ page: 3, pages: 3, total: 60, onPageChange }} />,
    );
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Previous' }));
    expect(onPageChange).toHaveBeenLastCalledWith(2);
  });
});
