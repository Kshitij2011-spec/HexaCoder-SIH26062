import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransportPage } from '../TransportPage';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { TransportLeg } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn((params) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
    }
    const str = q.toString();
    return str ? `?${str}` : '';
  }),
}));

const mockLegs: TransportLeg[] = [
  {
    id: 'leg-1',
    code: 'LEG-2026-VESSEL-01',
    expedition_id: 'exp-1',
    mode: 'VESSEL',
    status: 'IN_TRANSIT',
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
    actual_departure_at: '2026-11-01T06:00:00Z',
    actual_arrival_at: null,
    capacity: '500',
    capacity_unit: 'tonnes',
    delay_reason: null,
    operational_metadata: {},
    data_provenance: 'SYNTHETIC_DEMO',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'leg-2',
    code: 'LEG-2026-AIR-02',
    expedition_id: 'exp-1',
    mode: 'AIR',
    status: 'DELAYED',
    origin_location_id: 'loc-22222222-2222-2222-2222-222222222222',
    destination_location_id: 'loc-33333333-3333-3333-3333-333333333333',
    departure_window_open: null,
    departure_window_close: null,
    arrival_window_open: null,
    arrival_window_close: null,
    planned_departure_at: '2026-11-16T00:00:00Z',
    planned_arrival_at: '2026-11-16T08:00:00Z',
    estimated_departure_at: '2026-11-18T00:00:00Z',
    estimated_arrival_at: '2026-11-18T08:00:00Z',
    actual_departure_at: null,
    actual_arrival_at: null,
    capacity: '2000',
    capacity_unit: 'kg',
    delay_reason: 'Antarctic whiteout condition',
    operational_metadata: {},
    data_provenance: 'SYNTHETIC_DEMO',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('TransportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders transport legs list with mode and status', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockLegs);

    renderWithProviders(<TransportPage />);

    expect(screen.getByText('Transport Legs')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('LEG-2026-VESSEL-01')).toBeInTheDocument();
      expect(screen.getByText('LEG-2026-AIR-02')).toBeInTheDocument();
      expect(screen.getByText('VESSEL')).toBeInTheDocument();
      expect(screen.getByText('AIR')).toBeInTheDocument();
      expect(screen.getByText('IN_TRANSIT')).toBeInTheDocument();
      expect(screen.getByText('DELAYED')).toBeInTheDocument();
      expect(screen.getByText('500 tonnes')).toBeInTheDocument();
    });
  });

  it('filters transport legs by search input', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockLegs);
    const user = userEvent.setup();

    renderWithProviders(<TransportPage />);

    await waitFor(() => {
      expect(screen.getByText('LEG-2026-VESSEL-01')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('searchbox', { name: /search transport legs/i });
    await user.type(searchInput, 'whiteout');

    expect(screen.queryByText('LEG-2026-VESSEL-01')).not.toBeInTheDocument();
    expect(screen.getByText('LEG-2026-AIR-02')).toBeInTheDocument();
  });
});
