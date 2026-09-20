import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createTestQueryClient } from '../../../../test-utils';
import { runwayKeys, useResourceRunways } from '../useResourceRunways';
import { apiClient } from '../../../../lib/api/client';
import type { ResourceRunwaySummary } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const mockSummary: ResourceRunwaySummary = {
  expedition_id: 'exp-1',
  evaluated_at: '2026-09-20T12:00:00Z',
  total_candidates: 1,
  items_with_resupply_gap: 1,
  items_at_risk: 0,
  minimum_runway_days: 18.0,
  data_provenance: 'DERIVED',
  runways: [
    {
      stock_lot_id: 'lot-1',
      inventory_item_id: 'item-1',
      item_code: 'JET-A1',
      item_name: 'Jet A-1 Aviation Fuel',
      category: 'FUEL',
      criticality: 'CRITICAL',
      unit: 'LITERS',
      location_id: 'loc-1',
      on_hand_quantity: '100.00',
      reserved_quantity: '10.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '90.00',
      daily_burn_rate: '5.00',
      burn_rate_source: 'OBSERVED_TRANSACTIONS_14D',
      burn_rate_evidence: {},
      runway_days: 18.0,
      resupply_gap_days: 7.0,
      runway_state: 'RESUPPLY_GAP',
      data_provenance: 'FORECAST',
    },
  ],
};

describe('useResourceRunways hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('generates consistent hierarchical query keys', () => {
    expect(runwayKeys.all).toEqual(['control-tower', 'runways']);
    expect(runwayKeys.expedition('exp-1')).toEqual([
      'control-tower',
      'expeditions',
      'exp-1',
      'runways',
    ]);
  });

  it('does not execute fetch when expeditionId is undefined', () => {
    const queryClient = createTestQueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useResourceRunways(undefined), { wrapper });

    expect(result.current.fetchStatus).toBe('idle');
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('fetches runway summary data for an expedition', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);
    const queryClient = createTestQueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useResourceRunways('exp-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/expeditions/exp-1/runways');
    expect(result.current.data?.total_candidates).toBe(1);
    expect(result.current.data?.runways[0].item_code).toBe('JET-A1');
    expect(result.current.data?.runways[0].runway_state).toBe('RESUPPLY_GAP');
  });
});
