import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConsequentialAuditTimeline } from '../ConsequentialAuditTimeline';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ConsequentialActionItem } from '../../../../lib/types/api';

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

const mockAuditItems: ConsequentialActionItem[] = [
  {
    approval_id: 'appr-001',
    recommendation_id: 'rec-001',
    replan_id: 'rep-001',
    decision: 'APPROVED',
    approver_person_id: 'PER-COMMANDER-01',
    approver_role: 'EXPEDITION_LEADER',
    comment: 'Authorized emergency diversion for weather safety.',
    decided_at: '2026-09-18T16:00:00Z',
    action_summary: 'Divert Cargo Flight to Maitri Airfield',
    applied_changes: [
      { action: 'DIVERT', target_destination: 'Maitri' },
      { action: 'UPDATE_ETA', new_eta: '2026-09-18T19:30:00Z' },
    ],
    resulting_event_id: 'evt-audit-999',
    correlation_id: 'cor-flow-101',
    created_at: '2026-09-18T16:00:00Z',
    data_provenance: 'DERIVED',
  },
  {
    approval_id: 'appr-002',
    recommendation_id: 'rec-002',
    replan_id: 'rep-002',
    decision: 'APPROVED',
    approver_person_id: 'PER-LOGISTICS-02',
    approver_role: 'LOGISTICS_DIRECTOR',
    comment: 'Spares transferred to support power generation.',
    decided_at: '2026-09-18T16:30:00Z',
    action_summary: 'Reallocate Generator Spares to Bharati Station',
    applied_changes: [{ action: 'REASSIGN', location: 'Bharati' }],
    resulting_event_id: 'evt-audit-1000',
    correlation_id: 'cor-flow-102',
    created_at: '2026-09-18T16:30:00Z',
    data_provenance: 'DERIVED',
  },
];

describe('ConsequentialAuditTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton while fetching audit records', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    expect(screen.getByText('Consequential Audit Timeline')).toBeInTheDocument();
    expect(screen.getAllByLabelText(/loading data/i).length).toBeGreaterThan(0);
  });

  it('renders error display when audit fetching fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Audit database unreachable'));
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    expect(
      await screen.findByText('Failed to load consequential audit trail'),
    ).toBeInTheDocument();
    expect(screen.getByText('Audit database unreachable')).toBeInTheDocument();
  });

  it('renders empty state when no audit records exist', async () => {
    vi.mocked(apiClient.get).mockResolvedValue([]);
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    expect(
      await screen.findByText('No consequential audit records'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No approved decisions or operational changes have been executed/i),
    ).toBeInTheDocument();
  });

  it('renders audit entries with approver, comment, resulting event ID, and provenance', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(mockAuditItems);
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    expect(
      await screen.findByText('Divert Cargo Flight to Maitri Airfield'),
    ).toBeInTheDocument();
    expect(screen.getByText('PER-COMMANDER-01')).toBeInTheDocument();
    expect(screen.getByText('EXPEDITION_LEADER')).toBeInTheDocument();
    expect(
      screen.getByText(/"Authorized emergency diversion for weather safety."/),
    ).toBeInTheDocument();
    expect(screen.getByText('evt-audit-999')).toBeInTheDocument();
    expect(screen.getByText('rec-001')).toBeInTheDocument();
  });

  it('toggles expandable applied changes', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValue(mockAuditItems);
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    const toggleButton = await screen.findByRole('button', {
      name: /show executed operational changes \(2\)/i,
    });
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Maitri')).toBeInTheDocument();
    expect(screen.getByText('2026-09-18T19:30:00Z')).toBeInTheDocument();

    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('handles page pagination controls', async () => {
    const user = userEvent.setup();
    // 20 items to enable next page button
    const fullPageItems = Array.from({ length: 20 }, (_, i) => ({
      ...mockAuditItems[0],
      approval_id: `appr-${i + 1}`,
      action_summary: `Operational Action ${i + 1}`,
    }));

    vi.mocked(apiClient.get).mockResolvedValue(fullPageItems);
    renderWithProviders(<ConsequentialAuditTimeline expeditionId="exp-1" />);

    expect(await screen.findByText('Page 1')).toBeInTheDocument();
    const prevBtn = screen.getByRole('button', { name: /previous/i });
    const nextBtn = screen.getByRole('button', { name: /next/i });

    expect(prevBtn).toBeDisabled();
    expect(nextBtn).toBeEnabled();

    await user.click(nextBtn);
    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('page=2'),
    );
  });
});
