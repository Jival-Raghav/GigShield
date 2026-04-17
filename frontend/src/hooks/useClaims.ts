import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { claimsApi, payoutsApi } from '@/lib/api';
import type { ClaimCreate, ClaimStatusUpdate, PayoutGateway } from '@/types';

export function useClaims(workerId: string | null) {
  return useQuery({
    queryKey: ['claims', workerId],
    queryFn: () => claimsApi.getByWorkerId(workerId!),
    enabled: !!workerId,
    refetchInterval: 10 * 1000, // Refresh every 10 seconds
    staleTime: 5 * 1000,
  });
}

export function useClaim(claimId: string | null) {
  return useQuery({
    queryKey: ['claim', claimId],
    queryFn: () => claimsApi.getById(claimId!),
    enabled: !!claimId,
    refetchInterval: 10 * 1000,
  });
}

export function useInitiateClaim() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ClaimCreate) => claimsApi.initiate(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['claims', variables.worker_id] });
    },
  });
}

export function useUpdateClaimStatus(claimId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ClaimStatusUpdate) => claimsApi.updateStatus(claimId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claim', claimId] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'flaggedClaims'] });
    },
  });
}

export function useInitiatePayout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: string | { claimId: string; gateway?: PayoutGateway }) => {
      if (typeof payload === 'string') {
        return payoutsApi.initiate(payload);
      }
      return payoutsApi.initiate(payload.claimId, payload.gateway ?? 'upi_simulator');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
  });
}
