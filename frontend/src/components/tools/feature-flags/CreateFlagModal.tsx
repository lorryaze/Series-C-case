import { useMemo, useState } from 'react';
import { Button } from '../../common/Button';
import { Modal } from '../../common/Modal';
import { inputClass } from '../../common/FilterBar';
import { useCreateFlag } from '../../../hooks/useFeatureFlags';
import { ApiError } from '../../../services/apiClient';

/** Mirrors the backend slug rule so the generated key is visible before saving. */
function slugify(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

export function CreateFlagModal({ onClose }: { onClose: () => void }): JSX.Element {
  const createFlag = useCreateFlag();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [defaultEnabled, setDefaultEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const key = useMemo(() => slugify(name), [name]);

  const submit = async () => {
    setError(null);
    try {
      await createFlag.mutateAsync({ name, description, default_enabled: defaultEnabled });
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'The flag could not be created.');
    }
  };

  return (
    <Modal
      open
      width="md"
      title="Create feature flag"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={name.trim().length < 3 || description.trim().length < 3 || createFlag.isPending}
          >
            Create flag
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          Name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Enable instant transfers"
            className={`${inputClass} mt-1 w-full`}
          />
        </label>
        <p className="text-xs text-slate-500">
          SDK key: <code className="rounded bg-slate-100 px-1">{key || '—'}</code>
        </p>
        <label className="block text-sm font-medium text-slate-700">
          Description
          <textarea
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="What does this flag control?"
            className={`${inputClass} mt-1 w-full`}
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={defaultEnabled}
            onChange={(event) => setDefaultEnabled(event.target.checked)}
          />
          Enable in every environment at 100% on creation
        </label>
        {error && <p className="text-sm text-rose-700">{error}</p>}
      </div>
    </Modal>
  );
}
