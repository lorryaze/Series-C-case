import { useState } from 'react';
import { AuditTrail } from '../../common/AuditTrail';
import { Button } from '../../common/Button';
import { Modal } from '../../common/Modal';
import { RiskBadge, StatusBadge } from '../../common/Badge';
import { inputClass } from '../../common/FilterBar';
import { useAuth } from '../../../context/AuthContext';
import {
  useKycAssignment,
  useKycAuditTrail,
  useKycDecision,
  useKycNote,
  useKycReview,
} from '../../../hooks/useKyc';
import { useReviewers } from '../../../hooks/useUsers';
import { ApiError } from '../../../services/apiClient';
import { formatDateTime, humanize } from '../../../utils/format';

type Decision = 'approve' | 'reject' | 'escalate';

function DetailRow({ label, value }: { label: string; value: React.ReactNode }): JSX.Element {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-1.5 text-sm last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}

export function KycDetailModal({
  reviewId,
  onClose,
}: {
  reviewId: number;
  onClose: () => void;
}): JSX.Element {
  const { canReview } = useAuth();
  const { data: review, isLoading } = useKycReview(reviewId);
  const [auditPage, setAuditPage] = useState(1);
  const { data: audit } = useKycAuditTrail(reviewId, auditPage);
  const { data: reviewers = [] } = useReviewers(canReview);
  const decision = useKycDecision(reviewId);
  const assignment = useKycAssignment(reviewId);
  const note = useKycNote(reviewId);

  const [reason, setReason] = useState('');
  const [noteBody, setNoteBody] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submitDecision = async (action: Decision) => {
    setError(null);
    if (reason.trim().length < 3) {
      setError('A reason of at least 3 characters is required for every decision.');
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
      title={review ? `${review.case_reference} · ${review.customer_name}` : 'KYC case'}
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
                onClick={() => submitDecision('escalate')}
                disabled={decision.isPending}
              >
                Escalate
              </Button>
              <Button
                variant="danger"
                onClick={() => submitDecision('reject')}
                disabled={decision.isPending}
              >
                Reject
              </Button>
              <Button onClick={() => submitDecision('approve')} disabled={decision.isPending}>
                Approve
              </Button>
            </>
          )}
        </>
      }
    >
      {isLoading || !review ? (
        <p className="text-sm text-slate-500">Loading case…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-5">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Customer
              </h3>
              <dl className="mt-2">
                <DetailRow label="Name" value={review.customer_name} />
                <DetailRow label="Email" value={review.customer_email} />
                <DetailRow label="Country" value={review.customer_country} />
                <DetailRow label="Business" value={review.business_name ?? '—'} />
                <DetailRow label="Submitted" value={formatDateTime(review.submitted_at)} />
                <DetailRow label="Status" value={<StatusBadge status={review.status} />} />
                <DetailRow
                  label="Assigned reviewer"
                  value={review.assigned_reviewer?.full_name ?? 'Unassigned'}
                />
              </dl>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Risk assessment
              </h3>
              <div className="mt-2 flex items-center gap-2">
                <RiskBadge level={review.risk_level} score={review.risk_score} />
                {review.sanctions_hit && <StatusBadge status="escalated" />}
              </div>
              <p className="mt-2 text-sm text-slate-600">{review.risk_summary}</p>
              <dl className="mt-2">
                <DetailRow label="Sanctions hit" value={review.sanctions_hit ? 'Yes' : 'No'} />
                <DetailRow label="PEP match" value={review.pep_match ? 'Yes' : 'No'} />
                {review.decision_reason && (
                  <DetailRow label="Decision reason" value={review.decision_reason} />
                )}
              </dl>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Documents
              </h3>
              <ul className="mt-2 space-y-1 text-sm">
                {review.documents.map((document) => (
                  <li key={document.id} className="flex items-center justify-between">
                    <span className="text-slate-700">
                      {humanize(document.document_type)} · {document.file_name}
                    </span>
                    <StatusBadge status={document.verified ? 'approved' : 'pending'} />
                  </li>
                ))}
                {review.documents.length === 0 && (
                  <li className="text-slate-500">No documents submitted.</li>
                )}
              </ul>
            </section>
          </div>

          <div className="space-y-5">
            {canReview && (
              <section className="space-y-3 rounded-md bg-slate-50 p-3">
                <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Decision reason (required)
                  <textarea
                    rows={3}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Why are you approving, rejecting or escalating this case?"
                    className={`${inputClass} mt-1 w-full font-normal normal-case`}
                  />
                </label>
                {error && <p className="text-sm text-rose-700">{error}</p>}

                <div className="flex items-end gap-2">
                  <label className="flex-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Assign reviewer
                    <select
                      value={review.assigned_reviewer?.id ?? ''}
                      onChange={(event) =>
                        event.target.value && assignment.mutate(Number(event.target.value))
                      }
                      className={`${inputClass} mt-1 w-full font-normal normal-case`}
                    >
                      <option value="">Select a reviewer…</option>
                      {reviewers.map((reviewer) => (
                        <option key={reviewer.id} value={reviewer.id}>
                          {reviewer.full_name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </section>
            )}

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Reviewer notes
              </h3>
              {canReview && (
                <div className="mt-2 flex gap-2">
                  <input
                    value={noteBody}
                    onChange={(event) => setNoteBody(event.target.value)}
                    placeholder="Add a note"
                    className={`${inputClass} flex-1`}
                  />
                  <Button
                    size="sm"
                    disabled={noteBody.trim().length === 0 || note.isPending}
                    onClick={async () => {
                      await note.mutateAsync(noteBody.trim());
                      setNoteBody('');
                    }}
                  >
                    Add
                  </Button>
                </div>
              )}
              <ul className="mt-3 space-y-2 text-sm">
                {review.notes.map((item) => (
                  <li key={item.id} className="rounded bg-slate-50 p-2">
                    <p className="text-slate-700">{item.body}</p>
                    <p className="text-xs text-slate-500">
                      {item.author.full_name} · {formatDateTime(item.created_at)}
                    </p>
                  </li>
                ))}
                {review.notes.length === 0 && <li className="text-slate-500">No notes yet.</li>}
              </ul>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Audit log
              </h3>
              <div className="mt-2 max-h-64 overflow-y-auto pr-1">
                <AuditTrail
                  entries={audit?.items ?? []}
                  pagination={
                    audit
                      ? {
                          page: audit.page,
                          pages: audit.pages,
                          total: audit.total,
                          onPageChange: setAuditPage,
                        }
                      : undefined
                  }
                />
              </div>
            </section>
          </div>
        </div>
      )}
    </Modal>
  );
}
