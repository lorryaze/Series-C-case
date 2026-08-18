import { request } from './apiClient';
import type {
  AuditLogEntry,
  FeatureFlag,
  FeatureFlagFilters,
  FlagEnvironment,
  Page,
} from '../types';

export interface FeatureFlagCreateInput {
  name: string;
  description: string;
  key?: string;
  default_enabled: boolean;
}

export const featureFlagService = {
  list(filters: FeatureFlagFilters): Promise<Page<FeatureFlag>> {
    return request<Page<FeatureFlag>>('/feature-flags', { params: { ...filters } });
  },

  create(input: FeatureFlagCreateInput): Promise<FeatureFlag> {
    return request<FeatureFlag>('/feature-flags', { method: 'POST', body: input });
  },

  update(flagId: number, input: Partial<FeatureFlagCreateInput>): Promise<FeatureFlag> {
    return request<FeatureFlag>(`/feature-flags/${flagId}`, { method: 'PATCH', body: input });
  },

  toggle(flagId: number, environment: FlagEnvironment, enabled: boolean): Promise<FeatureFlag> {
    return request<FeatureFlag>(`/feature-flags/${flagId}/toggle`, {
      method: 'POST',
      body: { environment, enabled },
    });
  },

  updateState(
    flagId: number,
    environment: FlagEnvironment,
    state: { enabled?: boolean; rollout_percentage?: number },
  ): Promise<FeatureFlag> {
    return request<FeatureFlag>(`/feature-flags/${flagId}/environments/${environment}`, {
      method: 'PATCH',
      body: state,
    });
  },

  history(flagId: number): Promise<{ flag_id: number; entries: AuditLogEntry[] }> {
    return request(`/feature-flags/${flagId}/history`);
  },
};
