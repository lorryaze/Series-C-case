import { useState } from 'react';
import { AuditTrail } from '../../common/AuditTrail';
import { Button } from '../../common/Button';
import { Modal } from '../../common/Modal';
import { StatusBadge } from '../../common/Badge';
import { inputClass } from '../../common/FilterBar';
import { useAuth } from '../../../context/AuthContext';
import { useRefund, useRefundDecision } from '../../../hooks/useRefunds';
import { ApiError } from '../../../services/apiClient';
import { formatCurrency, formatDateTime, formatHours, humanize } from '../../../utils/format';

function DetailRow({ label, value }: { label: string; value: React.ReactNode }): JSX.Element {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-1.5 text-sm last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}

export function RefundDetailModal({
  refundId,
  onClose,
}: {
  refundId: number;
  onClose: () => void;
}): JSX.Element {
  const { canReview } = useAuth();
  const { data: refund, isLoading } = useRefund(refundId);
  const decision = useRefundDecision(refundId);
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = async (action: 'approve' | 'reject' | 'request-info') => {
    setError(null);
    if (reason.trim().length < 3) {
      setError('A reason of at least 3 characters is required.');
      return;
    }
    try {
      await decision.mutateAsync({ action, reason: reason.trim() });
      setReason('');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'The decision could not be saved.');
    }
  };

  return (
    <Modal
      open
      width="xl"
      title={refund ? `${refund.refund_reference} · ${refund.customer_name}` : 'Refund'}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          {canReview && (
            <>
              <Button
                variant="secondary"
                onClick={() => submit('request-info')}
                disabled={decision.isPending}
              >
                Request more info
              </Button>
              <Button
                variant="danger"
                onClick={() => submit('reject')}
                disabled={decision.isPending}
              >
                Reject
              </Button>
              <Button onClick={() => submit('approve')} disabled={decision.isPending}>
                Approve
              </Button>
            </>
          )}
        </>
      }
    >
      {isLoading || !refund ? (
        <p className="text-sm text-slate-500">Loading refund…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-5">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Refund
              </h3>
              <dl className="mt-2">
                <DetailRow label="Amount" value={formatCurrency(refund.amount)} />
                <DetailRow label="Status" value={<StatusBadge status={refund.status} />} />
                <DetailRow label="Reason" value={humanize(refund.reason)} />
                <DetailRow label="Detail" value={refund.reason_detail ?? '—'} />
                <DetailRow label="Transaction" value={refund.transaction_reference} />
                <DetailRow label="Requested" value={formatDateTime(refund.requested_at)} />
                <DetailRow label="Processed" value={formatDateTime(refund.processed_at)} />
                <DetailRow label="Processing time" value={formatHours(refund.processing_hours)} />
                <DetailRow label="Processed by" value={refund.processed_by?.full_name ?? '—'} />
                {refund.decision_reason && (
                  <DetailRow label="Decision reason" value={refund.decision_reason} />
                )}
              </dl>
            </section>

            {canReview && (
              <section className="space-y-2 rounded-md bg-slate-50 p-3">
                <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Decision reason (required)
                  <textarea
                    rows={3}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Why are you approving, rejecting or requesting more information?"
                    className={`${inputClass} mt-1 w-full font-normal normal-case`}
                  />
                </label>
                {error && <p className="text-sm text-rose-700">{error}</p>}
              </section>
            )}
          </div>

          <div className="space-y-5">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Customer history
              </h3>
              <ul className="mt-2 space-y-1 text-sm">
                {refund.customer_history.map((item) => (
                  <li key={item.id} className="flex items-center justify-between">
                    <span className="text-slate-700">
                      {item.refund_reference} · {formatCurrency(item.amount)}
                    </span>
                    <StatusBadge status={item.status} />
                  </li>
                ))}
                {refund.customer_history.length === 0 && (
                  <li className="text-slate-500">No other refunds for this customer.</li>
                )}
              </ul>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Approval chain
              </h3>
              <div className="mt-2 max-h-64 overflow-y-auto pr-1">
                <AuditTrail
                  entries={refund.approval_chain}
                  emptyMessage="No decisions recorded yet."
                />
              </div>
            </section>
          </div>
        </div>
      )}
    </Modal>
  );
}
