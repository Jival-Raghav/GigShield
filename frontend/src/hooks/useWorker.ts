import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workersApi } from '@/lib/api';
import type { WorkerUpdate } from '@/types';

export function useWorker(workerId: string | null) {
  return useQuery({
    queryKey: ['worker', workerId],
    queryFn: () => workersApi.getById(workerId!),
    enabled: !!workerId,
    staleTime: 60 * 1000, // 1 minute
  });
}

export function useUpdateWorker(workerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: WorkerUpdate) => workersApi.update(workerId, payload),
    onSuccess: (updatedWorker) => {
      queryClient.setQueryData(['worker', workerId], updatedWorker);
      queryClient.invalidateQueries({ queryKey: ['worker', workerId] });
    },
  });
}

export function useWorkerWallet(workerId: string | null) {
  return useQuery({
    queryKey: ['wallet', workerId],
    queryFn: () => workersApi.getWallet(workerId!),
    enabled: !!workerId,
    refetchInterval: 30 * 1000,
    staleTime: 10 * 1000,
  });
}
