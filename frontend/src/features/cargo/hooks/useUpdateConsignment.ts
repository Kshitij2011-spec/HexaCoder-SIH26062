import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { CargoConsignment } from '../../../lib/types/api';

interface Payload {
  id: string;
  data: Partial<Pick<CargoConsignment, 'status' | 'priority' | 'transport_plan_summary' | 'compliance_status'>>;
}

export function useUpdateConsignment() {
  const qc = useQueryClient();
  return useMutation<CargoConsignment, Error, Payload>({
    mutationFn: ({ id, data }) => apiClient.patch<CargoConsignment>(`/cargo/consignments/${id}`, data),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['cargo-consignments'] });
      qc.setQueryData(['cargo-consignment', updated.id], updated);
      qc.invalidateQueries({ queryKey: ['cargo-timeline', updated.id] });
    },
  });
}
