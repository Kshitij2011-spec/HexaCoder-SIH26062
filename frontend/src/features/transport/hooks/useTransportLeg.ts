import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { TransportLeg } from '../../../lib/types/api';

export function useTransportLeg(id: string | null) {
  return useQuery<TransportLeg>({
    queryKey: ['transport-leg', id],
    queryFn: ({ signal }) => apiClient.get<TransportLeg>(`/transport/legs/${id}`, signal),
    enabled: !!id,
  });
}
