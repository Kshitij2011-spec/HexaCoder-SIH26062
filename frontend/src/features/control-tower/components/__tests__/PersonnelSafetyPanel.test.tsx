import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PersonnelSafetyPanel } from '../PersonnelSafetyPanel';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { PersonnelPostureSummary } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn(() => ''),
}));

const mockSummary: PersonnelPostureSummary = {
  expedition_id: 'exp-44-a',
  overall_status: 'BLOCKED',
  total_personnel: 8,
  cleared_count: 6,
  medical_hold_count: 2,
  unavailable_count: 0,
  at_station_count: 5,
  field_deployed_count: 3,
  in_transit_count: 0,
  evaluated_at: '2026-09-20T12:00:00Z',
  data_provenance: 'DERIVED',
  findings: [
    {
      finding_id: 'FIND-DISQ-01',
      rule_id: 'PERS_READINESS_DISQUALIFIED',
      status: 'BLOCKED',
      subject_type: 'PERSON',
      subject_id: 'person-1',
      subject_code: 'P-04',
      subject_name: 'Anil Kumar',
      mission_id: 'mis-1',
      mission_code: 'MIS-GLAC-01',
      team_id: 'team-1',
      team_code: 'TM-ALPHA',
      reason: "Personnel member 'P-04' (Anil Kumar) is on medical hold while assigned to active field team.",
      evidence: {
        readiness_state: 'NOT_CLEARED',
        role: 'Ice Core Specialist',
      },
      recommended_action: "Initiate operational replanning to substitute 'P-04' with an available specialist.",
      data_provenance: 'DERIVED',
    },
    {
      finding_id: 'FIND-HEADCOUNT-02',
      rule_id: 'TEAM_HEADCOUNT_DEFICIT',
      status: 'BLOCKED',
      subject_type: 'TEAM',
      subject_id: 'team-2',
      subject_code: 'TM-SOLO',
      subject_name: 'Solo Traverse Recon',
      mission_id: 'mis-2',
      mission_code: 'MIS-SOLO-02',
      team_id: 'team-2',
      team_code: 'TM-SOLO',
      reason: "Field team 'TM-SOLO' has only 1 assigned member, breaching mandatory polar buddy safety invariant.",
      evidence: {
        current_headcount: 1,
        minimum_required: 2,
      },
      recommended_action: 'Assign additional personnel from station complement to satisfy safety floor.',
      data_provenance: 'DERIVED',
    },
  ],
  teams: [
    {
      team_id: 'team-1',
      team_code: 'TM-ALPHA',
      team_name: 'Glacier Drill Team',
      status: 'STATION',
      leader_person_id: 'person-ldr',
      leader_name: 'Sunita Rao',
      leader_readiness: 'READY',
      mission_id: 'mis-1',
      mission_code: 'MIS-GLAC-01',
      location_id: 'loc-1',
      location_name: 'Maitri Research Base',
      headcount: 2,
      members: [
        {
          person_id: 'person-ldr',
          person_code: 'P-01',
          full_name: 'Sunita Rao',
          role: 'Field Safety Leader',
          readiness_state: 'READY',
          movement_state: 'AT_STATION',
          is_leader: true,
        },
        {
          person_id: 'person-1',
          person_code: 'P-04',
          full_name: 'Anil Kumar',
          role: 'Ice Core Specialist',
          readiness_state: 'NOT_CLEARED',
          movement_state: 'AT_STATION',
          is_leader: false,
        },
      ],
      deployment_status: 'BLOCKED',
      unmet_requirements: ["Disqualified member 'P-04' (NOT_CLEARED) requires substitution"],
      data_provenance: 'DERIVED',
    },
  ],
  reassignment_opportunities: [
    {
      team_id: 'team-1',
      team_code: 'TM-ALPHA',
      mission_id: 'mis-1',
      mission_code: 'MIS-GLAC-01',
      displaced_person_id: 'person-1',
      displaced_person_code: 'P-04',
      displaced_role: 'Ice Core Specialist',
      candidate_person_id: 'person-8',
      candidate_person_code: 'P-08',
      candidate_full_name: 'Priya Patel',
      candidate_role: 'Ice Core Specialist',
      candidate_readiness: 'READY',
      rationale: 'Substitute disqualified P-04 with cleared station personnel P-08 (Priya Patel).',
      data_provenance: 'ADVISORY',
    },
  ],
};

describe('PersonnelSafetyPanel Component (Milestone A10)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton then displays personnel safety overview', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(<PersonnelSafetyPanel expeditionId="exp-44-a" />);

    expect(await screen.findByTestId('personnel-safety-panel')).toBeInTheDocument();
    expect(screen.getByText(/Personnel & Field Team Safety/i)).toBeInTheDocument();
    expect(screen.getByTestId('overall-posture-badge')).toHaveTextContent('BLOCKED');
  });

  it('renders complement metrics correctly', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(<PersonnelSafetyPanel expeditionId="exp-44-a" />);

    await screen.findByTestId('personnel-safety-panel');

    expect(screen.getByText('Total Force')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument(); // total_personnel

    expect(screen.getByText('Medically Cleared')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument(); // cleared_count

    expect(screen.getByText('Medical Hold')).toBeInTheDocument();
    expect(screen.getAllByText('2').length).toBeGreaterThan(0); // medical_hold_count

    expect(screen.getByText('Station Base')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // at_station_count
  });

  it('renders explainable safety findings with evidence and rules', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(<PersonnelSafetyPanel expeditionId="exp-44-a" />);

    await screen.findByTestId('personnel-safety-panel');

    expect(screen.getByTestId('finding-card-PERS_READINESS_DISQUALIFIED')).toBeInTheDocument();
    expect(screen.getByTestId('finding-card-TEAM_HEADCOUNT_DEFICIT')).toBeInTheDocument();

    expect(screen.getAllByText(/Anil Kumar/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Solo Traverse Recon/i).length).toBeGreaterThan(0);
  });

  it('triggers onInitiateReplan callback when Review Reassignment is clicked', async () => {
    const user = userEvent.setup();
    const mockReplan = vi.fn();
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(
      <PersonnelSafetyPanel expeditionId="exp-44-a" onInitiateReplan={mockReplan} />
    );

    await screen.findByTestId('personnel-safety-panel');

    const reviewButtons = screen.getAllByRole('button', { name: /Review Reassignment/i });
    expect(reviewButtons.length).toBeGreaterThan(0);

    await user.click(reviewButtons[0]);

    expect(mockReplan).toHaveBeenCalledTimes(1);
    expect(mockReplan).toHaveBeenCalledWith(
      expect.objectContaining({
        personId: 'person-1',
        personCode: 'P-04',
        teamId: 'team-1',
        reason: expect.stringContaining("Safety finding: Personnel member 'P-04'"),
      })
    );
  });

  it('allows switching to Teams & Crews tab to inspect roster and buddy status', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(<PersonnelSafetyPanel expeditionId="exp-44-a" />);

    await screen.findByTestId('personnel-safety-panel');

    const teamsTab = screen.getByRole('button', { name: /Teams & Crews/i });
    await user.click(teamsTab);

    expect(screen.getByText('Glacier Drill Team')).toBeInTheDocument();
    expect(screen.getAllByText(/Sunita Rao/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Assigned Roster:/i)).toBeInTheDocument();
  });

  it('renders reassignment opportunities tab and lets operator propose reassignment', async () => {
    const user = userEvent.setup();
    const mockReplan = vi.fn();
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);

    renderWithProviders(
      <PersonnelSafetyPanel expeditionId="exp-44-a" onInitiateReplan={mockReplan} />
    );

    await screen.findByTestId('personnel-safety-panel');

    const oppTab = screen.getByRole('button', { name: /Reassignment Candidates/i });
    await user.click(oppTab);

    expect(screen.getAllByText(/Priya Patel/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Substitute disqualified P-04 with cleared station personnel P-08/i)).toBeInTheDocument();

    const proposeButton = screen.getByRole('button', { name: /Propose Reassignment/i });
    await user.click(proposeButton);

    expect(mockReplan).toHaveBeenCalledTimes(1);
    expect(mockReplan).toHaveBeenCalledWith(
      expect.objectContaining({
        personId: 'person-1',
        personCode: 'P-04',
        teamId: 'team-1',
        teamCode: 'TM-ALPHA',
      })
    );
  });
});
