import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../lib/api/client';
import type { Location } from '../../../lib/types/api';

interface UpdateLocationPayload {
  id: string;
  data: Partial<Pick<Location, 'name' | 'description' | 'type'>>;
}

export function useUpdateLocation() {
  const qc = useQueryClient();
  return useMutation<Location, Error, UpdateLocationPayload>({
    mutationFn: ({ id, data }) => apiClient.patch<Location>(`/locations/${id}`, data),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['locations'] });
      qc.invalidateQueries({ queryKey: ['location', updated.id] });
    },
  });
}
