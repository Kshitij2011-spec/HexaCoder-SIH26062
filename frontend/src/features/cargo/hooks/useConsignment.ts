import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoConsignment } from '../../../lib/types/api';

export function useConsignment(id: string | null) {
  return useQuery<CargoConsignment>({
    queryKey: ['cargo-consignment', id],
    queryFn: ({ signal }) => apiClient.get<CargoConsignment>(`/cargo/consignments/${id}`, signal),
    enabled: !!id,
  });
}
