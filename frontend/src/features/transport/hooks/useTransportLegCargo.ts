import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoConsignment } from '../../../lib/types/api';

export function useTransportLegCargo(legId: string | null) {
  return useQuery<CargoConsignment[]>({
    queryKey: ['transport-leg-cargo', legId],
    queryFn: ({ signal }) =>
      apiClient.get<CargoConsignment[]>(`/transport/legs/${legId}/cargo`, signal),
    enabled: !!legId,
  });
}
