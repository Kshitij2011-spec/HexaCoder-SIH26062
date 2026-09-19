import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExpeditionContextBar } from '../ExpeditionContextBar';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ExpeditionControlSummary } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
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

const mockExpeditions: ExpeditionControlSummary[] = [
  {
    expedition_id: 'exp-1',
    code: 'EXP-45',
    name: '45th Indian Antarctic Expedition',
    season: '2026-2027',
    lifecycle_status: 'ACTIVE',
    readiness_state: 'AT_RISK',
    total_missions: 12,
    ready_missions_count: 8,
    at_risk_missions_count: 3,
    blocked_missions_count: 1,
    active_incidents_count: 2,
    active_hard_constraint_violations_count: 1,
    pending_replans_count: 1,
    pending_approvals_count: 1,
    latest_events: [],
    blockers: [{ blocker_type: 'WEATHER', message: 'Blizzard at Maitri' }],
    warnings: [{ warning_type: 'FUEL', message: 'Fuel reserve low' }],
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
    total_missions: 6,
    ready_missions_count: 6,
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
];

describe('ExpeditionContextBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders expedition metadata, metrics, and readiness posture', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockExpeditions[0]);

    renderWithProviders(
      <ExpeditionContextBar
        selectedExpeditionId="exp-1"
        onSelectExpedition={vi.fn()}
        expeditions={mockExpeditions}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('EXP-45')).toBeInTheDocument();
      expect(screen.getByText('45th Indian Antarctic Expedition')).toBeInTheDocument();
      expect(screen.getByText('2026-2027')).toBeInTheDocument();
      expect(screen.getByText('ACTIVE')).toBeInTheDocument();
      expect(screen.getByText('AT RISK')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
      expect(screen.getByText('8 ready')).toBeInTheDocument();
      expect(screen.getByText('3 risk')).toBeInTheDocument();
      expect(screen.getByText('1 blocked')).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith('/control-tower/expeditions/exp-1');
  });

  it('triggers onSelectExpedition when selector option is changed', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockExpeditions[0]);
    const onSelectMock = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(
      <ExpeditionContextBar
        selectedExpeditionId="exp-1"
        onSelectExpedition={onSelectMock}
        expeditions={mockExpeditions}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('EXP-45')).toBeInTheDocument();
    });

    const selector = screen.getByLabelText(/select expedition campaign/i);
    await user.selectOptions(selector, 'exp-2');

    expect(onSelectMock).toHaveBeenCalledWith('exp-2');
  });

  it('renders skeleton when expeditions are loading', () => {
    renderWithProviders(
      <ExpeditionContextBar
        selectedExpeditionId="exp-1"
        onSelectExpedition={vi.fn()}
        expeditions={[]}
        isLoadingExpeditions={true}
      />,
    );

    expect(screen.getByLabelText(/loading data/i)).toBeInTheDocument();
  });

  it('renders error display when expedition summary fails to load', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Expedition not found'));

    renderWithProviders(
      <ExpeditionContextBar
        selectedExpeditionId="exp-99"
        onSelectExpedition={vi.fn()}
        expeditions={mockExpeditions}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/failed to load expedition summary/i)).toBeInTheDocument();
      expect(screen.getByText('Expedition not found')).toBeInTheDocument();
    });
  });
});
