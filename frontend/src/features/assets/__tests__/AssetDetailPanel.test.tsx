import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { AssetDetailPanel } from '../AssetDetailPanel';
import { apiClient } from '../../../lib/api/client';
import type { Asset, MaintenanceRecord, AssetTimeline } from '../../../lib/types/api';

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: (params: Record<string, string | number | undefined | null>) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        q.set(k, String(v));
      }
    }
    const str = q.toString();
    return str ? `?${str}` : '';
  },
}));

const mockAsset: Asset = {
  id: 'asset-501',
  code: 'CRANE-MOBILE-01',
  serial_number: 'LIEB-LTR-1100',
  type: 'MOBILE_CRANE',
  status: 'AVAILABLE',
  criticality: 'MISSION_CRITICAL',
  condition: 'OPERATIONAL',
  location_id: 'loc-wharf-01',
  description: 'Heavy wharf cargo unloading crane',
  commissioned_at: '2021-03-15T00:00:00Z',
  retired_at: null,
  operational_metadata: {},
  data_provenance: 'MEASURED',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockMaintenance: MaintenanceRecord[] = [
  {
    id: 'maint-601',
    asset_id: 'asset-501',
    maintenance_type: 'PREVENTIVE',
    status: 'IN_PROGRESS',
    priority: 2,
    description: 'Quarterly hydraulic hose inspection',
    scheduled_start_at: '2026-02-01T08:00:00Z',
    estimated_duration_hours: 4,
    technician_name: 'Tech Specialist Rao',
    actual_start_at: '2026-02-01T08:30:00Z',
    actual_completed_at: null,
    findings: null,
    corrective_action: null,
    operational_metadata: {},
    data_provenance: 'MEASURED',
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-02-01T00:00:00Z',
  },
];

const mockTimeline: AssetTimeline = {
  asset_id: 'asset-501',
  code: 'CRANE-MOBILE-01',
  status: 'AVAILABLE',
  condition: 'OPERATIONAL',
  location_id: 'loc-wharf-01',
  history: [
    {
      id: 'event-701',
      timestamp: '2026-01-10T10:00:00Z',
      event_type: 'ASSET_RELOCATED',
      description: 'Relocated to Wharf Berth 1 for icebreaker cargo ops',
      actor: 'LOGISTICS_CHIEF',
      data_provenance: 'MEASURED',
    },
  ],
};

describe('AssetDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders asset specifications and timeline events', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      if (path.includes('/maintenance')) return Promise.resolve(mockMaintenance);
      return Promise.resolve(null);
    });

    renderWithProviders(<AssetDetailPanel asset={mockAsset} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('CRANE-MOBILE-01')).toBeInTheDocument();
      expect(screen.getByText('LIEB-LTR-1100', { exact: false })).toBeInTheDocument();
      expect(screen.getByText('Quarterly hydraulic hose inspection')).toBeInTheDocument();
      expect(screen.getByText('Relocated to Wharf Berth 1 for icebreaker cargo ops')).toBeInTheDocument();
    });
  });

  it('enforces terminal RETIRED state behavior', async () => {
    const retiredAsset: Asset = {
      ...mockAsset,
      status: 'RETIRED',
      retired_at: '2026-02-15T00:00:00Z',
    };

    vi.mocked(apiClient.get).mockResolvedValue([]);
    renderWithProviders(<AssetDetailPanel asset={retiredAsset} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/No state transitions or movements are permitted/i)).toBeInTheDocument();
    });
  });

  it('completes maintenance order with findings and corrective action', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/maintenance')) return Promise.resolve(mockMaintenance);
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      return Promise.resolve(null);
    });
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockMaintenance[0], status: 'COMPLETED' });

    const user = userEvent.setup();
    renderWithProviders(<AssetDetailPanel asset={mockAsset} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Quarterly hydraulic hose inspection')).toBeInTheDocument();
    });

    // Select the record
    const actionBtn = screen.getByRole('button', { name: 'Action' });
    await user.click(actionBtn);

    const findingsInput = screen.getByLabelText(/Inspection Findings/i);
    await user.type(findingsInput, 'Minor surface abrasion on line #3');

    const correctiveInput = screen.getByLabelText(/Corrective Action Taken/i);
    await user.type(correctiveInput, 'Fitted protective Kevlar sleeve and pressure tested');

    const completeBtn = screen.getByRole('button', { name: /Complete Maintenance/i });
    await user.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Complete maintenance order maint-60/i)).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole('button', { name: 'Confirm' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/assets/maintenance/maint-601/complete',
        expect.objectContaining({
          findings: 'Minor surface abrasion on line #3',
          corrective_action: 'Fitted protective Kevlar sleeve and pressure tested',
        })
      );
    });
  });
});
