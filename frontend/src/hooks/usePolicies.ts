import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { policiesApi, premiumApi } from '@/lib/api';
import type { PolicyCreate, PremiumQuoteRequest } from '@/types';

export function usePolicies(workerId: string | null) {
  return useQuery({
    queryKey: ['policies', workerId],
    queryFn: () => policiesApi.getByWorkerId(workerId!),
    enabled: !!workerId,
    staleTime: 30 * 1000,
  });
}

export function useCreatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PolicyCreate) => policiesApi.create(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies', variables.worker_id] });
    },
  });
}

export function useDeletePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ policyId }: { policyId: string; workerId: string }) => policiesApi.delete(policyId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies', variables.workerId] });
    },
  });
}

export function useBaseline(workerId: string | null) {
  return useQuery({
    queryKey: ['baseline', workerId],
    queryFn: () => premiumApi.computeBaseline(workerId!),
    enabled: !!workerId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function usePremiumQuote() {
  return useMutation({
    mutationFn: (payload: PremiumQuoteRequest) => premiumApi.getQuote(payload),
  });
}
