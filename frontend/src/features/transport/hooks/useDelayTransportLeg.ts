import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { TransportDelayImpact, DelayRequest } from '../../../lib/types/api';

interface DelayPayload {
  legId: string;
  data: DelayRequest;
}

export function useDelayTransportLeg() {
  const qc = useQueryClient();
  return useMutation<TransportDelayImpact, Error, DelayPayload>({
    mutationFn: ({ legId, data }) =>
      apiClient.post<TransportDelayImpact>(`/transport/legs/${legId}/delay`, data),
    onSuccess: (impact, variables) => {
      qc.invalidateQueries({ queryKey: ['transport-legs'] });
      qc.setQueryData(['transport-leg', variables.legId], impact.transport_leg);
      qc.invalidateQueries({ queryKey: ['cargo-consignments'] });
      qc.invalidateQueries({ queryKey: ['cargo-timeline'] });
      qc.invalidateQueries({ queryKey: ['transport-leg-cargo', variables.legId] });
    },
  });
}
