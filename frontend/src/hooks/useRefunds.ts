import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { refundService } from '../services/refundService';
import type { RefundFilters } from '../types';

const REFUND_KEY = ['refunds'] as const;

export function useRefunds(filters: RefundFilters) {
  return useQuery({
    queryKey: [...REFUND_KEY, 'list', filters],
    queryFn: () => refundService.list(filters),
  });
}

export function useRefundSummary() {
  return useQuery({ queryKey: [...REFUND_KEY, 'summary'], queryFn: () => refundService.summary() });
}

export function useRefundTrend(days = 30) {
  return useQuery({
    queryKey: [...REFUND_KEY, 'trend', days],
    queryFn: () => refundService.trend(days),
  });
}

export function useRefund(refundId: number | null) {
  return useQuery({
    queryKey: [...REFUND_KEY, 'detail', refundId],
    queryFn: () => refundService.detail(refundId as number),
    enabled: refundId !== null,
  });
}

export function useRefundDecision(refundId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      action,
      reason,
    }: {
      action: 'approve' | 'reject' | 'request-info';
      reason: string;
    }) => refundService.decide(refundId, action, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REFUND_KEY }),
  });
}
