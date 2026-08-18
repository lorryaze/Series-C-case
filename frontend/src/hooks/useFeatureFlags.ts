import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { featureFlagService } from '../services/featureFlagService';
import type { FeatureFlagCreateInput } from '../services/featureFlagService';
import type { FeatureFlagFilters, FlagEnvironment } from '../types';

const FLAG_KEY = ['feature-flags'] as const;

export function useFeatureFlags(filters: FeatureFlagFilters) {
  return useQuery({
    queryKey: [...FLAG_KEY, 'list', filters],
    queryFn: () => featureFlagService.list(filters),
  });
}

export function useFlagHistory(flagId: number | null) {
  return useQuery({
    queryKey: [...FLAG_KEY, 'history', flagId],
    queryFn: () => featureFlagService.history(flagId as number),
    enabled: flagId !== null,
  });
}

function useFlagInvalidation() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: FLAG_KEY });
}

export function useCreateFlag() {
  const invalidate = useFlagInvalidation();
  return useMutation({
    mutationFn: (input: FeatureFlagCreateInput) => featureFlagService.create(input),
    onSuccess: invalidate,
  });
}

export function useToggleFlag() {
  const invalidate = useFlagInvalidation();
  return useMutation({
    mutationFn: ({
      flagId,
      environment,
      enabled,
    }: {
      flagId: number;
      environment: FlagEnvironment;
      enabled: boolean;
    }) => featureFlagService.toggle(flagId, environment, enabled),
    onSuccess: invalidate,
  });
}

export function useUpdateFlagState() {
  const invalidate = useFlagInvalidation();
  return useMutation({
    mutationFn: ({
      flagId,
      environment,
      rolloutPercentage,
      enabled,
    }: {
      flagId: number;
      environment: FlagEnvironment;
      rolloutPercentage?: number;
      enabled?: boolean;
    }) =>
      featureFlagService.updateState(flagId, environment, {
        ...(rolloutPercentage === undefined ? {} : { rollout_percentage: rolloutPercentage }),
        ...(enabled === undefined ? {} : { enabled }),
      }),
    onSuccess: invalidate,
  });
}
