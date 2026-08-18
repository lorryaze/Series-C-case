import { request } from './apiClient';
import type {
  Page,
  RefundDetail,
  RefundFilters,
  RefundListItem,
  RefundSummary,
  RefundTrendPoint,
} from '../types';

export const refundService = {
  list(filters: RefundFilters): Promise<Page<RefundListItem>> {
    return request<Page<RefundListItem>>('/refunds', { params: { ...filters } });
  },

  summary(): Promise<RefundSummary> {
    return request<RefundSummary>('/refunds/summary');
  },

  trend(days = 30): Promise<RefundTrendPoint[]> {
    return request<RefundTrendPoint[]>('/refunds/trend', { params: { days } });
  },

  detail(refundId: number): Promise<RefundDetail> {
    return request<RefundDetail>(`/refunds/${refundId}`);
  },

  decide(
    refundId: number,
    action: 'approve' | 'reject' | 'request-info',
    reason: string,
  ): Promise<RefundDetail> {
    return request<RefundDetail>(`/refunds/${refundId}/${action}`, {
      method: 'POST',
      body: { reason },
    });
  },
};
