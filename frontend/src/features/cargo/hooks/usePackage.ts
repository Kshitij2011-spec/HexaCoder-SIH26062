import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoPackage } from '../../../lib/types/api';

export function usePackage(id: string | null) {
  return useQuery<CargoPackage>({
    queryKey: ['cargo-package', id],
    queryFn: ({ signal }) => apiClient.get<CargoPackage>(`/cargo/packages/${id}`, signal),
    enabled: !!id,
  });
}
