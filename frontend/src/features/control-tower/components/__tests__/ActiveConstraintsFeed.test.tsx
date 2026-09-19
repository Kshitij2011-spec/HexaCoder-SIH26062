import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActiveConstraintsFeed } from '../ActiveConstraintsFeed';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ControlTowerConstraintItem } from '../../../../lib/types/api';

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

const mockConstraints: ControlTowerConstraintItem[] = [
  {
    constraint_id: 'cst-1',
    code: 'CST-COLD-CHAIN',
    name: 'Cold Chain Storage Integrity',
    type: 'STORAGE',
    rule_code: 'RULE-TEMP-01',
    subject_type: 'CARGO',
    subject_id: 'crg-101',
    subject_code: 'PKG-MED-01',
    hard_or_soft: 'HARD',
    severity: 'CRITICAL',
    state: 'VIOLATED',
    reason: 'Temperature exceeded threshold -20C for 45 minutes.',
    evidence: { max_temperature_recorded: -14.2, duration_minutes: 45, threshold: -20 },
    data_provenance: 'DERIVED',
  },
  {
    constraint_id: 'cst-2',
    code: 'CST-FUEL-RESERVE',
    name: 'Minimum Emergency Fuel Reserve',
    type: 'SAFETY',
    rule_code: 'RULE-FUEL-02',
    subject_type: 'EXPEDITION',
    subject_id: 'exp-1',
    subject_code: 'EXP-45',
    hard_or_soft: 'HARD',
    severity: 'HIGH',
    state: 'SATISFIED',
    reason: 'Reserve levels within acceptable nominal limits.',
    evidence: { current_liters: 15400, minimum_required: 12000 },
    data_provenance: 'DERIVED',
  },
  {
    constraint_id: 'cst-3',
    code: 'CST-CREV-SURVEY',
    name: 'Glacial Crevasse Radar Survey',
    type: 'ENVIRONMENTAL',
    rule_code: 'RULE-ENV-03',
    subject_type: 'TRANSPORT_LEG',
    subject_id: 'leg-301',
    subject_code: 'LEG-MAITRI-03',
    hard_or_soft: 'SOFT',
    severity: 'MEDIUM',
    state: 'NOT_EVALUABLE',
    reason: 'Radar survey telemetry pending satellite uplink.',
    evidence: {},
    data_provenance: 'DERIVED',
  },
];

describe('ActiveConstraintsFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton while fetching constraints', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    expect(
      screen.getByRole('heading', { name: /active constraints & invariants/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/loading data/i)).toBeInTheDocument();
  });

  it('renders error display when API call fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Database connectivity error'));

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load active constraints/i)).toBeInTheDocument();
      expect(screen.getByText('Database connectivity error')).toBeInTheDocument();
    });
  });

  it('renders empty state when no constraints exist', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce([]);

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText(/no active constraints found/i)).toBeInTheDocument();
    });
  });

  it('renders violated, satisfied, and not evaluable constraints with codes, subjects, and reasons', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockConstraints);

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      // Violated constraint
      expect(screen.getByText('CST-COLD-CHAIN')).toBeInTheDocument();
      expect(screen.getByText('Cold Chain Storage Integrity')).toBeInTheDocument();
      expect(screen.getByText('Temperature exceeded threshold -20C for 45 minutes.')).toBeInTheDocument();
      expect(screen.getByRole('status', { name: /constraint state: violated/i })).toBeInTheDocument();
      expect(screen.getByText('1 VIOLATED')).toBeInTheDocument();

      // Satisfied constraint
      expect(screen.getByText('CST-FUEL-RESERVE')).toBeInTheDocument();
      expect(screen.getByRole('status', { name: /constraint state: satisfied/i })).toBeInTheDocument();

      // Not evaluable constraint
      expect(screen.getByText('CST-CREV-SURVEY')).toBeInTheDocument();
      expect(screen.getByRole('status', { name: /constraint state: not evaluable/i })).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/control-tower/expeditions/exp-1/constraints'),
    );
  });

  it('filters constraints by state select dropdown', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockConstraints);
    const user = userEvent.setup();

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('CST-COLD-CHAIN')).toBeInTheDocument();
    });

    const stateSelect = screen.getByLabelText(/filter by constraint evaluation state/i);
    await user.selectOptions(stateSelect, 'VIOLATED');

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('state=VIOLATED'),
    );
  });

  it('filters constraints by rigidity (hard/soft) dropdown', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockConstraints);
    const user = userEvent.setup();

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('CST-COLD-CHAIN')).toBeInTheDocument();
    });

    const rigiditySelect = screen.getByLabelText(/filter by constraint rigidity/i);
    await user.selectOptions(rigiditySelect, 'HARD');

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('hard_or_soft=HARD'),
    );
  });

  it('toggles evidence expansion to display structured key-value diagnostics', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockConstraints);
    const user = userEvent.setup();

    renderWithProviders(<ActiveConstraintsFeed expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('CST-COLD-CHAIN')).toBeInTheDocument();
    });

    const toggleButton = screen.getAllByRole('button', {
      name: /show evidence & diagnostics/i,
    })[0];
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    // Click to expand
    await user.click(toggleButton);

    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('max_temperature_recorded:')).toBeInTheDocument();
    expect(screen.getByText('-14.2')).toBeInTheDocument();
    expect(screen.getByText('duration_minutes:')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();

    // Click again to hide
    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('max_temperature_recorded:')).not.toBeInTheDocument();
  });
});
