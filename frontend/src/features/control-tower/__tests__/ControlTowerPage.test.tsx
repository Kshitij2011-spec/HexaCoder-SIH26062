import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ControlTowerPage } from '../ControlTowerPage';
import { renderWithProviders } from '../../../test-utils';
import { apiClient } from '../../../lib/api/client';
import type {
  ControlTowerOverview,
  ExpeditionControlSummary,
  MissionOperationsItem,
} from '../../../lib/types/api';

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

const mockOverview: ControlTowerOverview = {
  total_expeditions: 2,
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
    {
      expedition_id: 'exp-2',
      code: 'EXP-46',
      name: '46th Indian Antarctic Expedition',
      season: '2027-2028',
      lifecycle_status: 'PLANNED',
      readiness_state: 'READY',
      total_missions: 0,
      ready_missions_count: 0,
      at_risk_missions_count: 0,
      blocked_missions_count: 0,
      active_incidents_count: 0,
      active_hard_constraint_violations_count: 0,
      pending_replans_count: 0,
      pending_approvals_count: 0,
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

const mockMissions: MissionOperationsItem[] = [
  {
    mission_id: 'msn-1',
    code: 'MSN-ICE-01',
    title: 'Ice Core Drilling at Larsemann Hills',
    status: 'ACTIVE',
    priority: 1,
    type: 'SCIENTIFIC',
    readiness_state: 'READY',
    readiness_blockers: [],
    warnings: [],
    unknown_requirements: [],
    violated_constraints: [],
    pending_replans: [],
    latest_event: null,
    data_provenance: 'DERIVED',
  },
];

describe('ControlTowerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeletons while fetching overview', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ControlTowerPage />);

    expect(screen.getByText('Control Tower')).toBeInTheDocument();
    expect(screen.getAllByLabelText(/loading data/i).length).toBeGreaterThan(0);
  });

  it('renders empty state when overview has no expeditions', async () => {
    const emptyOverview: ControlTowerOverview = {
      ...mockOverview,
      total_expeditions: 0,
      expeditions: [],
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce(emptyOverview);

    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(screen.getByText('No expeditions available')).toBeInTheDocument();
    });
  });

  it('renders full page shell and child components successfully', async () => {
    const mockConstraint = {
      constraint_id: 'cst-1',
      code: 'CST-COLD-CHAIN',
      name: 'Cold Chain Storage Integrity',
      type: 'STORAGE',
      rule_code: 'RULE-TEMP-01',
      subject_type: 'CARGO',
      subject_id: 'crg-101',
      hard_or_soft: 'HARD',
      severity: 'CRITICAL',
      state: 'VIOLATED',
      reason: 'Temperature exceeded threshold -20C',
      evidence: {},
      data_provenance: 'DERIVED',
    };

    const mockEvent = {
      event_id: 'ev-1',
      event_type: 'MissionApproved',
      entity_type: 'MISSION',
      entity_id: 'msn-1',
      previous_state: 'PROPOSED',
      new_state: 'APPROVED',
      occurred_at: '2026-09-19T09:30:00Z',
      source: 'API',
      evidence: {},
      data_provenance: 'MEASURED',
    };

    const mockDecisions = {
      expedition_id: 'exp-1',
      total_pending_replans: 1,
      total_pending_recommendations: 1,
      total_pending_approvals: 1,
      pending_approvals: [
        {
          approval_id: 'appr-1',
          recommendation_id: 'rec-1',
          recommendation_title: 'Divert Cargo Flight to Maitri',
          status: 'PENDING',
          required_approver_role: 'OPERATOR',
          what_changed: 'Weather disruption',
          why_it_matters: 'Flight safety',
          what_constraint_is_involved: 'CST-COLD-CHAIN',
          available_options_count: 1,
          created_at: '2026-09-19T09:00:00Z',
        },
      ],
      pending_recommendations: [],
      pending_replans: [],
      data_provenance: 'DERIVED',
      generated_at: '2026-09-19T09:00:00Z',
    };

    const mockAudit = [
      {
        approval_id: 'appr-1',
        recommendation_id: 'rec-1',
        decision: 'APPROVED',
        approver_person_id: 'PER-OPS',
        action_summary: 'Divert Cargo Flight Execution',
        applied_changes: [],
        resulting_event_id: 'evt-audit-1',
        created_at: '2026-09-19T09:15:00Z',
        data_provenance: 'DERIVED',
      },
    ];

    vi.mocked(apiClient.get).mockImplementation(async (path: string) => {
      if (path === '/control-tower/overview') return mockOverview;
      if (path === '/control-tower/expeditions/exp-1') return mockOverview.expeditions[0];
      if (path.startsWith('/control-tower/expeditions/exp-1/missions')) return mockMissions;
      if (path.startsWith('/control-tower/expeditions/exp-1/constraints')) return [mockConstraint];
      if (path.startsWith('/control-tower/expeditions/exp-1/events')) return [mockEvent];
      if (path.startsWith('/control-tower/expeditions/exp-1/decisions')) return mockDecisions;
      if (path.startsWith('/control-tower/expeditions/exp-1/audit')) return mockAudit;
      return null;
    });

    renderWithProviders(<ControlTowerPage />);

    // Top Header
    expect(screen.getByText('Control Tower')).toBeInTheDocument();
    expect(
      screen.getByText('Operational command center & mission readiness posture'),
    ).toBeInTheDocument();

    // Wait for overview, context bar, and all child sections
    await waitFor(() => {
      expect(screen.getByText('Campaigns: 2')).toBeInTheDocument();
      expect(screen.getByText('EXP-45')).toBeInTheDocument();
      expect(screen.getByText('45th Indian Antarctic Expedition')).toBeInTheDocument();

      // Mission Readiness Grid
      expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
      expect(screen.getByText('Ice Core Drilling at Larsemann Hills')).toBeInTheDocument();

      // Decision Queue Panel
      expect(
        screen.getByRole('heading', { name: /decision queue & human governance/i }),
      ).toBeInTheDocument();
      expect(screen.getByText('Divert Cargo Flight to Maitri')).toBeInTheDocument();

      // Active Constraints Feed
      expect(
        screen.getByRole('heading', { name: /active constraints & invariants/i }),
      ).toBeInTheDocument();
      expect(screen.getAllByText('CST-COLD-CHAIN').length).toBeGreaterThanOrEqual(1);

      // Operational Events Feed
      expect(
        screen.getByRole('heading', { name: /operational events feed/i }),
      ).toBeInTheDocument();
      expect(screen.getByText('MissionApproved')).toBeInTheDocument();

      // Consequential Audit Timeline
      expect(
        screen.getByRole('heading', { name: /consequential audit timeline/i }),
      ).toBeInTheDocument();
      expect(screen.getByText('Divert Cargo Flight Execution')).toBeInTheDocument();
    });
  });

  it('renders error display when overview fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Gateway timeout'));

    renderWithProviders(<ControlTowerPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load control tower operational overview/i),
      ).toBeInTheDocument();
      expect(screen.getByText('Gateway timeout')).toBeInTheDocument();
    });
  });
});
