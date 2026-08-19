import { useState } from 'react';
import { AuditTrail } from '../../common/AuditTrail';
import { Button } from '../../common/Button';
import { Modal } from '../../common/Modal';
import { useFlagHistory } from '../../../hooks/useFeatureFlags';

export function FlagHistoryModal({
  flagId,
  flagName,
  onClose,
}: {
  flagId: number;
  flagName: string;
  onClose: () => void;
}): JSX.Element {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useFlagHistory(flagId, page);

  return (
    <Modal
      open
      title={`Change history · ${flagName}`}
      onClose={onClose}
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {isLoading ? (
        <p className="text-sm text-slate-500">Loading history…</p>
      ) : (
        <AuditTrail
          entries={data?.items ?? []}
          emptyMessage="This flag has not changed yet."
          pagination={
            data
              ? {
                  page: data.page,
                  pages: data.pages,
                  total: data.total,
                  onPageChange: setPage,
                }
              : undefined
          }
        />
      )}
    </Modal>
  );
}
