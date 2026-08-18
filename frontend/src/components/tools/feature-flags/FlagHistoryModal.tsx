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
  const { data, isLoading } = useFlagHistory(flagId);

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
        <AuditTrail entries={data?.entries ?? []} emptyMessage="This flag has not changed yet." />
      )}
    </Modal>
  );
}
