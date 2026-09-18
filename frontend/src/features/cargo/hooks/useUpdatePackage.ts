import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoPackage } from '../../../lib/types/api';

interface UpdatePayload {
  id: string;
  data: Partial<Pick<CargoPackage, 'status' | 'condition' | 'contents_summary'>>;
}

export function useUpdatePackage() {
  const qc = useQueryClient();
  return useMutation<CargoPackage, Error, UpdatePayload>({
    mutationFn: ({ id, data }) => apiClient.patch<CargoPackage>(`/cargo/packages/${id}`, data),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['cargo-packages', updated.consignment_id] });
      qc.setQueryData(['cargo-package', updated.id], updated);
    },
  });
}
