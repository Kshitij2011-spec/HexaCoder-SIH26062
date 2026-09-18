import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { IncidentDetailPanel } from '../IncidentDetailPanel';
import { apiClient } from '../../../lib/api/client';
import type { Incident, IncidentReference, IncidentTimeline } from '../../../lib/types/api';

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

const mockIncident: Incident = {
  id: 'inc-901',
  code: 'INC-2026-099',
  title: 'Antenna Array Power Fluctuations',
  description: 'Comms tower array intermittently dropping telemetry link',
  incident_type: 'COMMUNICATIONS_LOSS',
  severity: 'HIGH',
  priority: 2,
  status: 'OPEN',
  location_id: 'loc-bharati-comms',
  asset_id: 'asset-comms-array',
  detected_at: '2026-01-20T06:00:00Z',
  acknowledged_at: null,
  resolved_at: null,
  closed_at: null,
  operational_metadata: {},
  data_provenance: 'MEASURED',
  created_at: '2026-01-20T06:00:00Z',
  updated_at: '2026-01-20T06:00:00Z',
};

const mockReferences: IncidentReference[] = [
  {
    id: 'ref-111',
    incident_id: 'inc-901',
    reference_type: 'ASSET',
    reference_id: 'asset-comms-array',
    notes: 'Direct physical failure of power rectifier',
    created_at: '2026-01-20T06:30:00Z',
  },
];

const mockTimeline: IncidentTimeline = {
  incident_id: 'inc-901',
  code: 'INC-2026-099',
  status: 'OPEN',
  severity: 'HIGH',
  priority: 2,
  history: [
    {
      id: 'event-222',
      timestamp: '2026-01-20T06:00:00Z',
      event_type: 'INCIDENT_DETECTED',
      summary: 'Automated telemetry loss detected',
      actor: 'STATION_DAEMON',
      provenance: 'MEASURED',
    },
  ],
};

describe('IncidentDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders incident specifications, references, and timeline', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/references')) return Promise.resolve(mockReferences);
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      return Promise.resolve(null);
    });

    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('INC-2026-099')).toBeInTheDocument();
      expect(screen.getByText('Antenna Array Power Fluctuations')).toBeInTheDocument();
      expect(screen.getByText('Direct physical failure of power rectifier')).toBeInTheDocument();
      expect(screen.getByText('Automated telemetry loss detected')).toBeInTheDocument();
    });
  });

  it('acknowledges incident with confirmation dialog', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/references')) return Promise.resolve(mockReferences);
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      return Promise.resolve(null);
    });
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockIncident, status: 'ACKNOWLEDGED' });

    const user = userEvent.setup();
    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('INC-2026-099')).toBeInTheDocument();
    });

    const ackBtn = screen.getByRole('button', { name: /Acknowledge/i });
    await user.click(ackBtn);

    await waitFor(() => {
      expect(screen.getByText(/Acknowledge operational incident INC-2026-099\?/i)).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole('button', { name: 'Confirm' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/incidents/inc-901/acknowledge', {});
    });
  });

  it('enforces terminal CLOSED state behavior', async () => {
    const closedIncident: Incident = {
      ...mockIncident,
      status: 'CLOSED',
      closed_at: '2026-01-21T18:00:00Z',
    };

    vi.mocked(apiClient.get).mockResolvedValue([]);
    renderWithProviders(<IncidentDetailPanel incident={closedIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/No further lifecycle actions or transitions are permitted/i)).toBeInTheDocument();
    });
  });

  it('attaches new cross-domain reference', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/references')) return Promise.resolve(mockReferences);
      if (path.includes('/timeline')) return Promise.resolve(mockTimeline);
      return Promise.resolve(null);
    });
    vi.mocked(apiClient.post).mockResolvedValue({
      id: 'ref-112',
      incident_id: 'inc-901',
      reference_type: 'LOCATION',
      reference_id: 'loc-bharati-comms',
      notes: 'Tower site inspection pending',
      created_at: '2026-01-20T07:00:00Z',
    });

    const user = userEvent.setup();
    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Attach Reference')).toBeInTheDocument();
    });

    const openAttachBtn = screen.getByRole('button', { name: 'Attach Reference' });
    await user.click(openAttachBtn);

    const refIdInput = screen.getByLabelText(/Resource Entity ID \/ UUID/i);
    await user.type(refIdInput, 'loc-bharati-comms');

    const notesInput = screen.getByLabelText(/Operational Notes/i);
    await user.type(notesInput, 'Tower site inspection pending');

    const saveBtn = screen.getByRole('button', { name: 'Save Reference' });
    await user.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/incidents/inc-901/references',
        expect.objectContaining({
          reference_id: 'loc-bharati-comms',
          notes: 'Tower site inspection pending',
        })
      );
    });
  });
});
