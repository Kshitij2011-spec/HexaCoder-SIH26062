import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoPackage } from '../../../lib/types/api';

export function useConsignmentPackages(consignmentId: string | null) {
  return useQuery<CargoPackage[]>({
    queryKey: ['cargo-packages', consignmentId],
    queryFn: ({ signal }) =>
      apiClient.get<CargoPackage[]>(`/cargo/consignments/${consignmentId}/packages`, signal),
    enabled: !!consignmentId,
  });
}
