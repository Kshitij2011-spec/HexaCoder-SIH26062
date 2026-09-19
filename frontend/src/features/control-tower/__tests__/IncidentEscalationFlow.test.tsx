import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { ControlTowerPage } from '../ControlTowerPage';
import { apiClient } from '../../../lib/api/client';
import type { ControlTowerOverview, IncidentContextView } from '../../../lib/types/api';

const mockSetSearchParams = vi.fn();
let mockSearchParams = new URLSearchParams('incidentId=inc-a7-1&replanId=replan-a7-1');

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useSearchParams: () => [mockSearchParams, mockSetSearchParams],
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

const mockOverview: ControlTowerOverview = {
  total_expeditions: 1,
  expeditions: [
    {
      expedition_id: 'exp-1',
      code: 'EXP-45',
      name: '45th Indian Antarctic Expedition',
      season: '2026-2027',
      lifecycle_status: 'ACTIVE',
      readiness_state: 'AT_RISK',
      total_missions: 1,
      ready_missions_count: 0,
      at_risk_missions_count: 1,
      blocked_missions_count: 0,
      active_incidents_count: 1,
      active_hard_constraint_violations_count: 0,
      pending_replans_count: 1,
      pending_approvals_count: 1,
      latest_events: [],
      blockers: [],
      warnings: [],
      unknown_requirements: [],
      data_provenance: 'DERIVED',
      generated_at: '2026-09-19T10:00:00Z',
    },
  ],
  total_missions: 1,
  missions_by_readiness: { AT_RISK: 1 },
  missions_by_status: { ACTIVE: 1 },
  active_incidents_count: 1,
  critical_constraints_violated_count: 0,
  pending_replans_count: 1,
  pending_recommendations_count: 1,
  pending_approvals_count: 1,
  offline_sync_summary: {},
  recent_operational_events: [],
  data_provenance: 'DERIVED',
  generated_at: '2026-09-19T10:00:00Z',
};

const mockIncidentContext: IncidentContextView = {
  incident_id: 'inc-a7-1',
  incident_code: 'INC-2026-A7',
  title: 'Glacier Runway Crevasse Encroachment',
  severity: 'HIGH',
  status: 'MITIGATING',
  location_id: 'loc-blue-ice',
  location_name: 'Blue Ice Skiway Bravo',
  propagation_summary: 'Air transit suspended. Blast radius affects 2 scheduled flight legs and ice-core logistics.',
  affected_entities: [
    { entity_type: 'TRANSPORT_LEG', entity_id: 'leg-air-01', relationship: 'BLOCKED' },
  ],
  affected_missions: [
    { mission_id: 'msn-air-01', code: 'MSN-CORE-02', title: 'Deep Dome Core Retrieval' },
  ],
  affected_constraints: [
    { code: 'CST-RUNWAY-01', name: 'Safe Runway Geometry Invariant', hard_or_soft: 'HARD' },
  ],
  correlation_id: 'corr-trace-a7-blueice',
  data_provenance: 'DERIVED',
};

describe('A7 ControlTower Incident Escalation Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams('incidentId=inc-a7-1&replanId=replan-a7-1');
  });

  it('renders Incident Escalation Context banner when incidentId and replanId are in URL', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/control-tower/overview')) return Promise.resolve(mockOverview);
      if (path.includes('/control-tower/incidents/inc-a7-1/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/replans/replan-a7-1')) {
        return Promise.resolve({
          id: 'replan-a7-1',
          replan_code: 'RPL-A7-001',
          status: 'REQUESTED',
          expedition_id: 'exp-1',
          data_provenance: 'DERIVED',
          affected_entities: mockIncidentContext.affected_entities,
          violated_constraints: mockIncidentContext.affected_constraints,
        });
      }
      return Promise.resolve([]);
    });

    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(screen.getByText('INC-2026-A7')).toBeInTheDocument();
      expect(screen.getByText('Glacier Runway Crevasse Encroachment')).toBeInTheDocument();
      expect(screen.getByText('Blue Ice Skiway Bravo')).toBeInTheDocument();
      expect(screen.getByText(/Air transit suspended/i)).toBeInTheDocument();
      expect(screen.getByText('MSN-CORE-02')).toBeInTheDocument();
      expect(screen.getByText('CST-RUNWAY-01')).toBeInTheDocument();
      expect(screen.getByText('corr-trace-a7-blueice')).toBeInTheDocument();
    });

    // Verify provenance labels rendered
    expect(screen.getAllByText('[SYNTHETIC/DEMO]').length).toBeGreaterThan(0);
    expect(screen.getAllByText('[DERIVED]').length).toBeGreaterThan(0);
  });

  it('opens Candidate Mitigation Options Explorer when explore button clicked', async () => {
    const user = userEvent.setup();

    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/control-tower/overview')) return Promise.resolve(mockOverview);
      if (path.includes('/control-tower/incidents/inc-a7-1/context')) return Promise.resolve(mockIncidentContext);
      if (path.includes('/replans/replan-a7-1/options') || path.includes('/replans/replan-a7-1/recommendations')) {
        return Promise.resolve([]);
      }
      if (path.includes('/replans/replan-a7-1')) {
        return Promise.resolve({
          id: 'replan-a7-1',
          replan_code: 'RPL-A7-001',
          status: 'REQUESTED',
          expedition_id: 'exp-1',
          data_provenance: 'DERIVED',
          affected_entities: mockIncidentContext.affected_entities,
          violated_constraints: mockIncidentContext.affected_constraints,
        });
      }
      return Promise.resolve([]);
    });

    renderWithProviders(<ControlTowerPage />);

    const exploreBtn = await screen.findByRole('button', { name: /explore candidate options/i });
    await user.click(exploreBtn);

    await waitFor(() => {
      // Mitigation Options Explorer dialog should be opened
      expect(screen.getByRole('dialog', { name: /candidate mitigation options/i })).toBeInTheDocument();
    });
  });

  it('governance invariant: escalation only requests replan and does not auto-apply', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/control-tower/overview')) return Promise.resolve(mockOverview);
      if (path.includes('/control-tower/incidents/inc-a7-1/context')) return Promise.resolve(mockIncidentContext);
      return Promise.resolve([]);
    });

    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(screen.getByText('INC-2026-A7')).toBeInTheDocument();
    });

    // Verify NO mutation endpoint (apply or approve) was called during escalation view
    expect(apiClient.post).not.toHaveBeenCalledWith(
      expect.stringMatching(/\/apply|\/decide/),
      expect.anything()
    );
  });
});
