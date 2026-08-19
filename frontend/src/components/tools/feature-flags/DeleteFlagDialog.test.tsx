import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '../../../test/render';
import { featureFlagService } from '../../../services/featureFlagService';
import { ApiError } from '../../../services/apiClient';
import { DeleteFlagDialog } from './DeleteFlagDialog';
import type { FeatureFlag } from '../../../types';

const flag: FeatureFlag = {
  id: 3,
  key: 'enable_instant_transfers',
  name: 'Enable instant transfers',
  description: 'Routes eligible payouts through the instant rail',
  default_enabled: false,
  environments: [{ environment: 'production', enabled: true, rollout_percentage: 25 }],
  modified_by: null,
  created_at: '2026-08-01T10:00:00Z',
  updated_at: '2026-08-10T10:00:00Z',
};

describe('DeleteFlagDialog', () => {
  it('deletes the flag and closes only after the API confirms', async () => {
    const remove = vi
      .spyOn(featureFlagService, 'remove')
      .mockResolvedValue({ message: "Feature flag 'enable_instant_transfers' was deleted" });
    const onClose = vi.fn();

    renderWithQueryClient(<DeleteFlagDialog flag={flag} onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: 'Delete flag' }));

    expect(remove).toHaveBeenCalledWith(3);
    expect(onClose).toHaveBeenCalled();
  });

  it('requires confirmation — cancelling never calls the API', async () => {
    const remove = vi.spyOn(featureFlagService, 'remove');
    const onClose = vi.fn();

    renderWithQueryClient(<DeleteFlagDialog flag={flag} onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(remove).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('keeps the dialog open and surfaces a server rejection', async () => {
    vi.spyOn(featureFlagService, 'remove').mockRejectedValue(
      new ApiError(403, 'authorization_error', 'Requires one of roles: admin', {}),
    );
    const onClose = vi.fn();

    renderWithQueryClient(<DeleteFlagDialog flag={flag} onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: 'Delete flag' }));

    expect(await screen.findByText('Requires one of roles: admin')).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });
});
