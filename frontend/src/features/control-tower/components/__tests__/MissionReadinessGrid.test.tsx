import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MissionReadinessGrid } from '../MissionReadinessGrid';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { MissionOperationsItem } from '../../../../lib/types/api';

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
    latest_event: {
      event_id: 'ev-1',
      event_type: 'MissionStarted',
      entity_type: 'MISSION',
      entity_id: 'msn-1',
      occurred_at: '2026-09-19T08:00:00Z',
      source: 'API',
      evidence: {},
      data_provenance: 'DERIVED',
    },
    data_provenance: 'DERIVED',
  },
  {
    mission_id: 'msn-2',
    code: 'MSN-TRAV-02',
    title: 'Fuel Resupply Traverse to Maitri',
    status: 'PLANNED',
    priority: 2,
    type: 'LOGISTICS',
    readiness_state: 'BLOCKED',
    readiness_blockers: [
      { blocker_type: 'CREVASSE_RISK', reason: 'Unmapped crevasse field on route' },
    ],
    warnings: [],
    unknown_requirements: [],
    violated_constraints: [
      { code: 'CST-WEATHER-01', hard_or_soft: 'HARD', reason: 'Wind exceeds safe threshold' },
    ],
    pending_replans: [
      { replan_id: 'rpl-1', replan_code: 'RPL-2026-001', status: 'OPTIONS_READY' },
    ],
    latest_event: null,
    data_provenance: 'DERIVED',
  },
];

describe('MissionReadinessGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders missions with codes, titles, readiness states, and status badges', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockMissions);

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
      expect(screen.getByText('Ice Core Drilling at Larsemann Hills')).toBeInTheDocument();
      expect(screen.getByText('MSN-TRAV-02')).toBeInTheDocument();
      expect(screen.getByText('Fuel Resupply Traverse to Maitri')).toBeInTheDocument();
      expect(screen.getByRole('status', { name: /readiness: ready/i })).toBeInTheDocument();
      expect(screen.getByRole('status', { name: /readiness: blocked/i })).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/control-tower/expeditions/exp-1/missions'),
    );
  });

  it('opens mission detail inspector and shows blockers and violated constraints', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockMissions);
    const user = userEvent.setup();

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MSN-TRAV-02')).toBeInTheDocument();
    });

    const inspectBtn = screen.getByLabelText(/inspect details for msn-trav-02/i);
    await user.click(inspectBtn);

    // Inspector opens
    expect(screen.getByText(/readiness blockers \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText('Unmapped crevasse field on route')).toBeInTheDocument();
    expect(screen.getByText(/violated constraints \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText('CST-WEATHER-01')).toBeInTheDocument();
    expect(screen.getByText('Wind exceeds safe threshold')).toBeInTheDocument();
    expect(screen.getByText('RPL-2026-001')).toBeInTheDocument();

    // Close inspector
    const closeBtn = screen.getByLabelText(/close mission inspection panel/i);
    await user.click(closeBtn);

    expect(screen.queryByText(/readiness blockers \(1\)/i)).not.toBeInTheDocument();
  });

  it('filters missions via readiness filter pills', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockMissions);
    const user = userEvent.setup();

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
    });

    const blockedPill = screen.getByRole('button', { name: /blocked/i });
    await user.click(blockedPill);

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('readiness=BLOCKED'),
    );
  });

  it('filters missions via status select dropdown', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockMissions);
    const user = userEvent.setup();

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/filter by lifecycle status/i);
    await user.selectOptions(statusSelect, 'SCHEDULED');

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('status=SCHEDULED'),
    );
  });

  it('filters missions on current page via client-side search', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockMissions);
    const user = userEvent.setup();

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
      expect(screen.getByText('MSN-TRAV-02')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('searchbox', {
      name: /search current missions by code or title/i,
    });
    await user.type(searchInput, 'Larsemann');

    expect(screen.getByText('MSN-ICE-01')).toBeInTheDocument();
    expect(screen.queryByText('MSN-TRAV-02')).not.toBeInTheDocument();
  });

  it('renders empty state when no missions are found', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce([]);

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('No missions found')).toBeInTheDocument();
    });
  });

  it('renders error display when API call fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network failure'));

    renderWithProviders(<MissionReadinessGrid expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load mission operations/i)).toBeInTheDocument();
      expect(screen.getByText('Network failure')).toBeInTheDocument();
    });
  });
});
