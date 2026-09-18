import { useQuery } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type { TransportLeg } from '../../../lib/types/api';

export interface TransportLegFilters {
  mode?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export function useTransportLegs(filters: TransportLegFilters = {}) {
  const query = buildQuery({
    ...filters,
    page: filters.page ?? 1,
    page_size: filters.page_size ?? 50,
  });

  return useQuery<TransportLeg[]>({
    queryKey: ['transport-legs', filters],
    queryFn: ({ signal }) => apiClient.get<TransportLeg[]>(`/transport/legs${query}`, signal),
  });
}
