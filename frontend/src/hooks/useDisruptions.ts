import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { triggersApi } from '@/lib/api';
import type { DisruptionSimulate } from '@/types';

export function useDisruptions(zoneId: string | null) {
  return useQuery({
    queryKey: ['disruptions', zoneId],
    queryFn: () => triggersApi.getActive(zoneId!),
    enabled: !!zoneId,
    refetchInterval: 30 * 1000, // Refresh every 30 seconds
    staleTime: 10 * 1000,
  });
}

export function useClaimableDisruptions(zoneId: string | null) {
  return useQuery({
    queryKey: ['disruptions', 'claimable', zoneId],
    queryFn: () => triggersApi.getClaimable(zoneId!),
    enabled: !!zoneId,
    refetchInterval: 30 * 1000,
    staleTime: 10 * 1000,
  });
}

export function useSimulateDisruption() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DisruptionSimulate) => triggersApi.simulate(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['disruptions', variables.zone_id] });
    },
  });
}
