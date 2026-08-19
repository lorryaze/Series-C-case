import { useState } from 'react';
import { Button } from '../../common/Button';
import { Modal } from '../../common/Modal';
import { useDeleteFlag } from '../../../hooks/useFeatureFlags';
import { ApiError } from '../../../services/apiClient';
import type { FeatureFlag } from '../../../types';

/**
 * Confirms deletion of a flag. Retiring a flag drops its per-environment state,
 * so the SDK key stops resolving — worth an explicit confirmation step.
 */
export function DeleteFlagDialog({
  flag,
  onClose,
}: {
  flag: FeatureFlag;
  onClose: () => void;
}): JSX.Element {
  const deletion = useDeleteFlag();
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    setError(null);
    try {
      await deletion.mutateAsync(flag.id);
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'The flag could not be deleted.');
    }
  };

  return (
    <Modal
      open
      title={`Delete ${flag.name}?`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" onClick={confirm} disabled={deletion.isPending}>
            Delete flag
          </Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">
        This removes <code className="text-brand-700">{flag.key}</code> and its state in every
        environment. Any client still evaluating the key falls back to its own default. The
        deletion is recorded in the audit trail.
      </p>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </Modal>
  );
}
