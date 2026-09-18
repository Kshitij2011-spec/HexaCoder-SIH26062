import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { IncidentsPage } from '../IncidentsPage';
import { apiClient } from '../../../lib/api/client';
import type { Incident } from '../../../lib/types/api';

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

const mockIncidents: Incident[] = [
  {
    id: 'inc-001',
    code: 'INC-2026-001',
    title: 'Cold Storage Excursion at Maitri Depot',
    description: 'Temperature spike above -15C in vaccine depot',
    incident_type: 'COLD_CHAIN_EXCURSION',
    severity: 'CRITICAL',
    priority: 1,
    status: 'OPEN',
    location_id: 'loc-maitri-depot',
    asset_id: null,
    detected_at: '2026-01-10T04:00:00Z',
    acknowledged_at: null,
    resolved_at: null,
    closed_at: null,
    operational_metadata: {},
    data_provenance: 'MEASURED',
    created_at: '2026-01-10T04:00:00Z',
    updated_at: '2026-01-10T04:00:00Z',
  },
  {
    id: 'inc-002',
    code: 'INC-2026-002',
    title: 'Whiteout Warning on Traversal Corridor Delta',
    description: 'Zero visibility blizzard affecting convoy',
    incident_type: 'WEATHER_EXCURSION',
    severity: 'MEDIUM',
    priority: 3,
    status: 'ACKNOWLEDGED',
    location_id: 'loc-corridor-delta',
    asset_id: null,
    detected_at: '2026-01-11T12:00:00Z',
    acknowledged_at: '2026-01-11T12:15:00Z',
    resolved_at: null,
    closed_at: null,
    operational_metadata: {},
    data_provenance: 'FORECAST',
    created_at: '2026-01-11T12:00:00Z',
    updated_at: '2026-01-11T12:15:00Z',
  },
];

describe('IncidentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders operational incidents with code, title, severity, and status', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockIncidents);
    renderWithProviders(<IncidentsPage />);

    expect(screen.getByRole('heading', { name: 'Incident Response' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('INC-2026-001')).toBeInTheDocument();
      expect(screen.getByText('Cold Storage Excursion at Maitri Depot')).toBeInTheDocument();
      expect(screen.getAllByText('CRITICAL').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('OPEN').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('INC-2026-002')).toBeInTheDocument();
    });
  });

  it('filters incidents by severity level', async () => {
    vi.mocked(apiClient.get).mockResolvedValue([mockIncidents[0]]);
    const user = userEvent.setup();
    renderWithProviders(<IncidentsPage />);

    const select = screen.getByLabelText('Filter by Severity');
    await user.selectOptions(select, 'CRITICAL');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining('severity=CRITICAL'));
    });
  });

  it('declares a new operational incident through workflow modal', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockIncidents);
    vi.mocked(apiClient.post).mockResolvedValue({
      id: 'inc-003',
      code: 'INC-2026-003',
      title: 'Snowcat Hydraulic Line Severed',
      description: 'Hydraulic pressure dropped to 0 psi during fuel traverse',
      incident_type: 'EQUIPMENT_FAILURE',
      severity: 'HIGH',
      priority: 2,
      status: 'OPEN',
      location_id: null,
      asset_id: null,
      detected_at: '2026-01-12T00:00:00Z',
      acknowledged_at: null,
      resolved_at: null,
      closed_at: null,
      operational_metadata: {},
      data_provenance: 'MEASURED',
      created_at: '2026-01-12T00:00:00Z',
      updated_at: '2026-01-12T00:00:00Z',
    });

    const user = userEvent.setup();
    renderWithProviders(<IncidentsPage />);

    const declareBtn = screen.getByRole('button', { name: /Declare Incident/i });
    await user.click(declareBtn);

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Declare Operational Incident/i })).toBeInTheDocument();
    });

    const modal = screen.getByRole('dialog', { name: /Declare Operational Incident/i });

    const codeInput = screen.getByLabelText(/Incident Code/i);
    await user.type(codeInput, 'INC-2026-003');

    const titleInput = screen.getByLabelText(/Title/i);
    await user.type(titleInput, 'Snowcat Hydraulic Line Severed');

    const descInput = screen.getByLabelText(/Description/i);
    await user.type(descInput, 'Hydraulic pressure dropped to 0 psi during fuel traverse');

    const submitBtn = within(modal).getByRole('button', { name: 'Declare Incident' });
    await user.click(submitBtn);

    // Confirm dialog
    await waitFor(() => {
      expect(screen.getByText(/Confirm declaration of incident INC-2026-003/i)).toBeInTheDocument();
    });

    const dialogs = screen.getAllByRole('dialog');
    const confirmDialog = dialogs[dialogs.length - 1];
    const confirmBtn = within(confirmDialog).getByRole('button', { name: 'Declare Incident' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/incidents',
        expect.objectContaining({
          code: 'INC-2026-003',
          title: 'Snowcat Hydraulic Line Severed',
        })
      );
    });
  });
});
