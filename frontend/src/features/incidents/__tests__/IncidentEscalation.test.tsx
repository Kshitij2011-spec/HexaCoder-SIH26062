import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { IncidentDetailPanel } from '../IncidentDetailPanel';
import { apiClient } from '../../../lib/api/client';
import type { Incident, IncidentContextView } from '../../../lib/types/api';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: () => '',
}));

const mockIncident: Incident = {
  id: 'inc-esc-101',
  code: 'INC-2026-101',
  title: 'Hydro-Power Fluid Leakage',
  description: 'Primary hydraulic manifold rupture near fuel cache',
  incident_type: 'FACILITY_DAMAGE',
  severity: 'CRITICAL',
  priority: 1,
  status: 'OPEN',
  location_id: 'loc-maitri-main',
  asset_id: 'asset-generator-01',
  detected_at: '2026-01-20T06:00:00Z',
  acknowledged_at: null,
  resolved_at: null,
  closed_at: null,
  operational_metadata: {},
  data_provenance: 'SYNTHETIC_DEMO',
  created_at: '2026-01-20T06:00:00Z',
  updated_at: '2026-01-20T06:00:00Z',
};

const mockIncidentContext: IncidentContextView = {
  incident_id: 'inc-esc-101',
  incident_code: 'INC-2026-101',
  title: 'Hydro-Power Fluid Leakage',
  severity: 'CRITICAL',
  status: 'OPEN',
  location_id: 'loc-maitri-main',
  location_name: 'Maitri Station Station Complex',
  propagation_summary: 'Blast radius propagated across 3 operational entities and 1 active mission.',
  affected_entities: [
    { entity_type: 'ASSET', entity_id: 'asset-gen-01', relationship: 'DAMAGED' },
  ],
  affected_missions: [
    { mission_id: 'msn-01', code: 'MSN-ENV-01', title: 'Environmental Deep Ice Sampling' },
  ],
  affected_constraints: [
    { code: 'CST-01', name: 'Life Support Power Invariant', hard_or_soft: 'HARD' },
  ],
  correlation_id: 'corr-trace-esc-101',
  data_provenance: 'DERIVED',
};

describe('A7 Incident Escalation in IncidentDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders escalation action when incident is in OPEN status with propagated context', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/references')) return Promise.resolve([]);
      if (path.includes('/timeline')) return Promise.resolve({ history: [] });
      return Promise.resolve(null);
    });

    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /escalate to replan/i })).toBeInTheDocument();
      expect(screen.getByText(/hydro-power fluid leakage/i)).toBeInTheDocument();
      expect(screen.getByText(/blast radius propagated across 3 operational entities/i)).toBeInTheDocument();
      expect(screen.getByText('MSN-ENV-01')).toBeInTheDocument();
    });
  });

  it('hides escalation action when incident is CLOSED or RESOLVED', async () => {
    const closedIncident: Incident = {
      ...mockIncident,
      status: 'CLOSED',
    };

    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/references')) return Promise.resolve([]);
      if (path.includes('/timeline')) return Promise.resolve({ history: [] });
      return Promise.resolve(null);
    });

    renderWithProviders(<IncidentDetailPanel incident={closedIncident} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(closedIncident.code)).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /escalate to replan/i })).not.toBeInTheDocument();
  });

  it('submits correct incident ID and handles successful navigation handoff', async () => {
    const user = userEvent.setup();

    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/references')) return Promise.resolve([]);
      if (path.includes('/timeline')) return Promise.resolve({ history: [] });
      return Promise.resolve(null);
    });

    vi.mocked(apiClient.post).mockImplementation((path: string) => {
      if (path.includes('/escalate')) {
        return Promise.resolve({
          incident_id: 'inc-esc-101',
          replan_id: 'replan-esc-202',
          expedition_id: 'exp-45',
          affected_entities: mockIncidentContext.affected_entities,
          violated_constraints: mockIncidentContext.affected_constraints,
          is_existing: false,
          data_provenance: 'DERIVED',
          message: 'Incident escalated to replanning',
        });
      }
      return Promise.resolve({});
    });

    const onCloseMock = vi.fn();
    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={onCloseMock} />);

    const escalateBtn = await screen.findByRole('button', { name: /escalate to replan/i });
    await user.click(escalateBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/control-tower/incidents/inc-esc-101/escalate',
        expect.objectContaining({
          requested_by: expect.any(String),
          reason: expect.stringContaining('INC-2026-101'),
        })
      );
      expect(onCloseMock).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith(
        '/control-tower?incidentId=inc-esc-101&replanId=replan-esc-202'
      );
    });
  });

  it('displays error display when escalation fails', async () => {
    const user = userEvent.setup();

    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/references')) return Promise.resolve([]);
      if (path.includes('/timeline')) return Promise.resolve({ history: [] });
      return Promise.resolve(null);
    });

    vi.mocked(apiClient.post).mockImplementation((path: string) => {
      if (path.includes('/escalate')) {
        return Promise.reject(new Error('Downstream replanning service unavailable'));
      }
      return Promise.resolve({});
    });

    renderWithProviders(<IncidentDetailPanel incident={mockIncident} onClose={vi.fn()} />);

    const escalateBtn = await screen.findByRole('button', { name: /escalate to replan/i });
    await user.click(escalateBtn);

    await waitFor(() => {
      expect(screen.getByText(/incident escalation failed/i)).toBeInTheDocument();
      expect(screen.getByText(/downstream replanning service unavailable/i)).toBeInTheDocument();
    });
  });
});
