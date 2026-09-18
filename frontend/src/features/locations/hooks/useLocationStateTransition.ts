import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { Location, LocationStatusUpdate } from '../../../lib/types/api';

interface TransitionPayload {
  id: string;
  body: LocationStatusUpdate;
}

export function useLocationStateTransition() {
  const qc = useQueryClient();
  return useMutation<Location, Error, TransitionPayload>({
    mutationFn: ({ id, body }) => apiClient.patch<Location>(`/locations/${id}/state`, body),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['locations'] });
      qc.setQueryData(['location', updated.id], updated);
      qc.invalidateQueries({ queryKey: ['location-hierarchy', updated.id] });
    },
  });
}
