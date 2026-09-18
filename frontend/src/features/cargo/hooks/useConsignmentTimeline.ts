import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoTimeline } from '../../../lib/types/api';

export function useConsignmentTimeline(id: string | null) {
  return useQuery<CargoTimeline>({
    queryKey: ['cargo-timeline', id],
    queryFn: ({ signal }) => apiClient.get<CargoTimeline>(`/cargo/consignments/${id}/timeline`, signal),
    enabled: !!id,
  });
}
