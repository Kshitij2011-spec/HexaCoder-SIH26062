import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConsignmentDetailPanel } from '../ConsignmentDetailPanel';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type { CargoConsignment, CargoTimeline } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn(),
}));

const mockConsignment: CargoConsignment = {
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
  transport_plan_summary: 'Direct flight route',
  compliance_status: 'COMPLIANT',
  handling_classification: 'TEMPERATURE_CONTROLLED',
  exception_reason: null,
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockTimeline: CargoTimeline = {
  consignment_id: 'c-1',
  code: 'CSG-2026-MED-01',
  required_by_at: '2026-12-01T00:00:00Z',
  planned_arrival_at: '2026-11-20T00:00:00Z',
  estimated_arrival_at: '2026-11-20T00:00:00Z',
  buffer_hours: 264.0,
  status: 'READY',
  risk_level: 'NOMINAL',
  is_delayed: false,
  exception_reason: null,
};

describe('ConsignmentDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders consignment overview and switches tabs', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      if (path.includes('/packages')) return Promise.resolve([]);
      return Promise.resolve(mockConsignment);
    });

    const user = userEvent.setup();
    renderWithProviders(
      <ConsignmentDetailPanel consignmentId="c-1" onClose={vi.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getAllByText('CSG-2026-MED-01').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Direct flight route')).toBeInTheDocument();
      expect(screen.getByText('TEMPERATURE_CONTROLLED')).toBeInTheDocument();
    });

    // Switch to Timeline tab
    const timelineTab = screen.getByRole('button', { name: 'Timeline' });
    await user.click(timelineTab);

    await waitFor(() => {
      expect(screen.getByText('Schedule Milestones')).toBeInTheDocument();
      expect(screen.getByText('+264.0 hrs')).toBeInTheDocument();
    });
  });
});
