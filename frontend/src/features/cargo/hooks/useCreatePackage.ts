import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoPackage } from '../../../lib/types/api';

interface Payload {
  consignmentId: string;
  data: {
    code: string;
    status?: string;
    contents_summary?: string;
    quantity?: number;
    weight_kg?: number;
    condition?: string;
  };
}

export function useCreatePackage() {
  const qc = useQueryClient();
  return useMutation<CargoPackage, Error, Payload>({
    mutationFn: ({ consignmentId, data }) =>
      apiClient.post<CargoPackage>(`/cargo/consignments/${consignmentId}/packages`, data),
    onSuccess: (pkg) => {
      qc.invalidateQueries({ queryKey: ['cargo-packages', pkg.consignment_id] });
    },
  });
}
