import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { kycService } from '../services/kycService';
import type { KycFilters } from '../types';

const KYC_KEY = ['kyc'] as const;

export function useKycReviews(filters: KycFilters) {
  return useQuery({
    queryKey: [...KYC_KEY, 'list', filters],
    queryFn: () => kycService.list(filters),
  });
}

export function useKycCounts() {
  return useQuery({ queryKey: [...KYC_KEY, 'counts'], queryFn: () => kycService.counts() });
}

export function useKycReview(reviewId: number | null) {
  return useQuery({
    queryKey: [...KYC_KEY, 'detail', reviewId],
    queryFn: () => kycService.detail(reviewId as number),
    enabled: reviewId !== null,
  });
}

export function useKycAuditTrail(reviewId: number | null) {
  return useQuery({
    queryKey: [...KYC_KEY, 'audit', reviewId],
    queryFn: () => kycService.auditTrail(reviewId as number),
    enabled: reviewId !== null,
  });
}

/** Invalidate every KYC query after a mutation so counts and rows stay in sync. */
function useKycInvalidation() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: KYC_KEY });
}

export function useKycDecision(reviewId: number) {
  const invalidate = useKycInvalidation();
  return useMutation({
    mutationFn: ({
      action,
      reason,
    }: {
      action: 'approve' | 'reject' | 'escalate';
      reason: string;
    }) => kycService.decide(reviewId, action, reason),
    onSuccess: invalidate,
  });
}

export function useKycAssignment(reviewId: number) {
  const invalidate = useKycInvalidation();
  return useMutation({
    mutationFn: (reviewerId: number) => kycService.assign(reviewId, reviewerId),
    onSuccess: invalidate,
  });
}

export function useKycNote(reviewId: number) {
  const invalidate = useKycInvalidation();
  return useMutation({
    mutationFn: (body: string) => kycService.addNote(reviewId, body),
    onSuccess: invalidate,
  });
}

export function useKycBulkAssign() {
  const invalidate = useKycInvalidation();
  return useMutation({
    mutationFn: ({ reviewIds, reviewerId }: { reviewIds: number[]; reviewerId: number }) =>
      kycService.bulkAssign(reviewIds, reviewerId),
    onSuccess: invalidate,
  });
}
