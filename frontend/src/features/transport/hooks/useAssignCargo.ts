import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { TransportCargoAssignment, AssignCargoRequest } from '../../../lib/types/api';

interface AssignPayload {
  legId: string;
  data: AssignCargoRequest;
}

export function useAssignCargo() {
  const qc = useQueryClient();
  return useMutation<TransportCargoAssignment, Error, AssignPayload>({
    mutationFn: ({ legId, data }) =>
      apiClient.post<TransportCargoAssignment>(`/transport/legs/${legId}/assign-cargo`, data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['transport-leg-cargo', variables.legId] });
      qc.invalidateQueries({ queryKey: ['cargo-consignments'] });
    },
  });
}
