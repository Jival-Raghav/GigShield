import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '@/lib/api';
import type { ClaimStatusUpdate } from '@/types';

export function useAdminDashboard() {
  return useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: () => adminApi.getDashboard(),
    refetchInterval: 15 * 1000, // Refresh every 15 seconds
    staleTime: 5 * 1000,
  });
}

export function useFlaggedClaims(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['admin', 'flaggedClaims', limit, offset],
    queryFn: () => adminApi.getFlaggedClaims(limit, offset),
    refetchInterval: 10 * 1000,
    staleTime: 5 * 1000,
  });
}

export function useZoneRisk() {
  return useQuery({
    queryKey: ['admin', 'zoneRisk'],
    queryFn: () => adminApi.getZoneRisk(),
    staleTime: 60 * 1000,
  });
}

export function usePayoutLog(limit = 100) {
  return useQuery({
    queryKey: ['admin', 'payoutLog', limit],
    queryFn: () => adminApi.getPayoutLog(limit),
    refetchInterval: 15 * 1000,
    staleTime: 5 * 1000,
  });
}

export function useAdminUpdateClaimStatus() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: string; payload: ClaimStatusUpdate }) => 
      adminApi.updateClaimStatus(claimId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'flaggedClaims'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] });
    },
  });
}

export function useRunSettlement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mode: 'previous_week' | 'current_week' = 'current_week') => adminApi.runSettlement(mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'flaggedClaims'] });
    },
  });
}
