import { request } from './apiClient';
import type {
  AuditLogEntry,
  KycFilters,
  KycNote,
  KycQueueCounts,
  KycReviewDetail,
  KycReviewListItem,
  Page,
} from '../types';

export const kycService = {
  list(filters: KycFilters): Promise<Page<KycReviewListItem>> {
    return request<Page<KycReviewListItem>>('/kyc/reviews', { params: { ...filters } });
  },

  counts(): Promise<KycQueueCounts> {
    return request<KycQueueCounts>('/kyc/reviews/counts');
  },

  detail(reviewId: number): Promise<KycReviewDetail> {
    return request<KycReviewDetail>(`/kyc/reviews/${reviewId}`);
  },

  auditTrail(reviewId: number): Promise<{ review_id: number; entries: AuditLogEntry[] }> {
    return request(`/kyc/reviews/${reviewId}/audit`);
  },

  decide(
    reviewId: number,
    action: 'approve' | 'reject' | 'escalate',
    reason: string,
  ): Promise<KycReviewDetail> {
    return request<KycReviewDetail>(`/kyc/reviews/${reviewId}/${action}`, {
      method: 'POST',
      body: { reason },
    });
  },

  assign(reviewId: number, reviewerId: number): Promise<KycReviewDetail> {
    return request<KycReviewDetail>(`/kyc/reviews/${reviewId}/assign`, {
      method: 'POST',
      body: { reviewer_id: reviewerId },
    });
  },

  bulkAssign(
    reviewIds: number[],
    reviewerId: number,
  ): Promise<{ assigned: number; review_ids: number[] }> {
    return request('/kyc/reviews/bulk-assign', {
      method: 'POST',
      body: { review_ids: reviewIds, reviewer_id: reviewerId },
    });
  },

  addNote(reviewId: number, body: string): Promise<KycNote> {
    return request<KycNote>(`/kyc/reviews/${reviewId}/notes`, { method: 'POST', body: { body } });
  },
};
