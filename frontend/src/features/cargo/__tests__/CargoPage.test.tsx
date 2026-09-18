import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CargoPage } from '../CargoPage';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { CargoConsignment } from '../../../lib/types/api';

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

const mockConsignments: CargoConsignment[] = [
  {
    id: 'c-1',
    code: 'CSG-2026-MED-01',
    expedition_id: 'exp-1',
    status: 'READY',
    risk_level: 'NOMINAL',
    priority: 1,
    origin_location_id: 'loc-11111111-1111-1111-1111-111111111111',
    destination_location_id: 'loc-22222222-2222-2222-2222-222222222222',
    required_by_at: '2026-12-01T00:00:00Z',
    planned_arrival_at: '2026-11-20T00:00:00Z',
    estimated_arrival_at: '2026-11-20T00:00:00Z',
    transport_plan_summary: 'Direct air transport to Maitri',
    compliance_status: 'COMPLIANT',
    handling_classification: 'TEMPERATURE_CONTROLLED',
    exception_reason: null,
    data_provenance: 'SYNTHETIC_DEMO',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'c-2',
    code: 'CSG-2026-FUEL-02',
    expedition_id: 'exp-1',
    status: 'DELAYED',
    risk_level: 'CRITICAL',
    priority: 2,
    origin_location_id: 'loc-11111111-1111-1111-1111-111111111111',
    destination_location_id: 'loc-33333333-3333-3333-3333-333333333333',
    required_by_at: '2026-10-01T00:00:00Z',
    planned_arrival_at: '2026-09-25T00:00:00Z',
    estimated_arrival_at: '2026-10-05T00:00:00Z',
    transport_plan_summary: 'Vessel transit blocked by pack ice',
    compliance_status: 'COMPLIANT',
    handling_classification: 'HAZMAT',
    exception_reason: 'Sea ice obstruction',
    data_provenance: 'SYNTHETIC_DEMO',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('CargoPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders cargo consignments list with risk badges and priorities', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockConsignments);

    renderWithProviders(<CargoPage />);

    expect(screen.getByText('Cargo Consignments')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('CSG-2026-MED-01')).toBeInTheDocument();
      expect(screen.getByText('CSG-2026-FUEL-02')).toBeInTheDocument();
      expect(screen.getByText('NOMINAL')).toBeInTheDocument();
      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
      expect(screen.getByText('P1')).toBeInTheDocument();
      expect(screen.getByText('P2')).toBeInTheDocument();
    });
  });

  it('filters consignments by code search', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockConsignments);
    const user = userEvent.setup();

    renderWithProviders(<CargoPage />);

    await waitFor(() => {
      expect(screen.getByText('CSG-2026-MED-01')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('searchbox', { name: /search consignments/i });
    await user.type(searchInput, 'FUEL');

    expect(screen.queryByText('CSG-2026-MED-01')).not.toBeInTheDocument();
    expect(screen.getByText('CSG-2026-FUEL-02')).toBeInTheDocument();
  });
});
