import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { TransportLeg } from '../../../lib/types/api';

interface UpdatePayload {
  id: string;
  data: Partial<
    Pick<
      TransportLeg,
      | 'status'
      | 'planned_departure_at'
      | 'planned_arrival_at'
      | 'estimated_departure_at'
      | 'estimated_arrival_at'
      | 'actual_departure_at'
      | 'actual_arrival_at'
      | 'capacity'
      | 'capacity_unit'
      | 'delay_reason'
    >
  >;
}

export function useUpdateTransportLeg() {
  const qc = useQueryClient();
  return useMutation<TransportLeg, Error, UpdatePayload>({
    mutationFn: ({ id, data }) => apiClient.patch<TransportLeg>(`/transport/legs/${id}`, data),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['transport-legs'] });
      qc.setQueryData(['transport-leg', updated.id], updated);
    },
  });
}
