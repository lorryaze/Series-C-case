import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '../../../test/render';
import { refundService } from '../../../services/refundService';
import { RefundDetailModal } from './RefundDetailModal';
import type { RefundDetail, RefundStatus, Role } from '../../../types';

const authState = { role: 'admin' as Role };

vi.mock('../../../context/AuthContext', () => ({
  useAuth: () => ({
    canReview: authState.role === 'admin' || authState.role === 'reviewer',
    canAdminister: authState.role === 'admin',
  }),
}));

function refund(status: RefundStatus): RefundDetail {
  return {
    id: 1,
    refund_reference: 'RF-1001',
    customer_name: 'Ana Costa',
    customer_email: 'ana@example.com',
    amount: '250.00',
    currency: 'EUR',
    reason: 'duplicate_charge',
    status,
    requested_at: '2026-08-10T10:00:00Z',
    processed_at: null,
    transaction_reference: 'TX-9001',
    reason_detail: null,
    decision_reason: null,
    processed_by: null,
    processing_hours: null,
    created_at: '2026-08-10T10:00:00Z',
    updated_at: '2026-08-10T10:00:00Z',
    customer_history: [
      {
        id: 2,
        refund_reference: 'RF-0900',
        amount: '80.00',
        currency: 'EUR',
        status: 'approved',
        requested_at: '2026-07-01T10:00:00Z',
      },
    ],
    approval_chain: [],
  };
}

describe('RefundDetailModal', () => {
  beforeEach(() => {
    authState.role = 'admin';
  });

  it('formats amounts in the currency of the refund, not USD', async () => {
    vi.spyOn(refundService, 'detail').mockResolvedValue(refund('pending'));

    renderWithQueryClient(<RefundDetailModal refundId={1} onClose={vi.fn()} />);

    expect(await screen.findByText('€250.00')).toBeInTheDocument();
    expect(screen.getByText(/RF-0900 · €80\.00/)).toBeInTheDocument();
  });

  it('offers decision actions for a pending refund', async () => {
    vi.spyOn(refundService, 'detail').mockResolvedValue(refund('pending'));

    renderWithQueryClient(<RefundDetailModal refundId={1} onClose={vi.fn()} />);

    expect(await screen.findByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Request more info' })).toBeInTheDocument();
  });

  it('hides decision actions once the refund is terminal', async () => {
    vi.spyOn(refundService, 'detail').mockResolvedValue(refund('approved'));

    renderWithQueryClient(<RefundDetailModal refundId={1} onClose={vi.fn()} />);

    expect(await screen.findByText(/already approved/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  });

  it('hides decision actions from a viewer', async () => {
    authState.role = 'viewer';
    vi.spyOn(refundService, 'detail').mockResolvedValue(refund('pending'));

    renderWithQueryClient(<RefundDetailModal refundId={1} onClose={vi.fn()} />);

    expect(await screen.findByText('€250.00')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
