import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransportLegDetailPanel } from '../TransportLegDetailPanel';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { TransportLeg } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn(),
}));

const mockLeg: TransportLeg = {
  id: 'leg-1',
  code: 'LEG-2026-VESSEL-01',
  expedition_id: 'exp-1',
  mode: 'VESSEL',
  status: 'PLANNED',
  origin_location_id: 'loc-11111111-1111-1111-1111-111111111111',
  destination_location_id: 'loc-22222222-2222-2222-2222-222222222222',
  departure_window_open: null,
  departure_window_close: null,
  arrival_window_open: null,
  arrival_window_close: null,
  planned_departure_at: '2026-11-01T00:00:00Z',
  planned_arrival_at: '2026-11-15T00:00:00Z',
  estimated_departure_at: '2026-11-01T00:00:00Z',
  estimated_arrival_at: '2026-11-15T00:00:00Z',
  actual_departure_at: null,
  actual_arrival_at: null,
  capacity: '500',
  capacity_unit: 'tonnes',
  delay_reason: null,
  operational_metadata: {},
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('TransportLegDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders transport leg overview and switches to cargo tab', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/cargo')) return Promise.resolve([]);
      return Promise.resolve(mockLeg);
    });

    const user = userEvent.setup();
    renderWithProviders(
      <TransportLegDetailPanel legId="leg-1" onClose={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getAllByText('LEG-2026-VESSEL-01').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('500 tonnes')).toBeInTheDocument();
      expect(screen.getByText('VESSEL')).toBeInTheDocument();
    });

    // Switch to Cargo Manifest tab
    const cargoTab = screen.getByRole('button', { name: 'Cargo Manifest' });
    await user.click(cargoTab);

    await waitFor(() => {
      expect(screen.getByText('Manifested Cargo (0)')).toBeInTheDocument();
      expect(
        screen.getByText('No cargo consignments currently manifested on this leg.'),
      ).toBeInTheDocument();
    });
  });

  it('switches to operations tab and shows delay propagation button', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/cargo')) return Promise.resolve([]);
      return Promise.resolve(mockLeg);
    });

    const user = userEvent.setup();
    renderWithProviders(
      <TransportLegDetailPanel legId="leg-1" onClose={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getAllByText('LEG-2026-VESSEL-01').length).toBeGreaterThanOrEqual(1);
    });

    const opsTab = screen.getByRole('button', { name: 'Operations' });
    await user.click(opsTab);

    await waitFor(() => {
      expect(screen.getByText('Operational Delay Propagation')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Record Delay' })).toBeInTheDocument();
      expect(screen.getByText('Leg Lifecycle State Transition')).toBeInTheDocument();
    });
  });
});
