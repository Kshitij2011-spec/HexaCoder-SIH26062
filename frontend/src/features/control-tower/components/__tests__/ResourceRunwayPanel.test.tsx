import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResourceRunwayPanel } from '../ResourceRunwayPanel';
import { renderWithProviders } from '../../../../test-utils';
import { apiClient } from '../../../../lib/api/client';
import type { ResourceRunwaySummary } from '../../../../lib/types/api';

vi.mock('../../../../lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  buildQuery: vi.fn(() => ''),
}));

const mockSummary: ResourceRunwaySummary = {
  expedition_id: 'exp-1',
  evaluated_at: '2026-09-20T12:00:00Z',
  total_candidates: 5,
  items_with_resupply_gap: 1,
  items_at_risk: 2,
  minimum_runway_days: 10.0,
  data_provenance: 'DERIVED',
  runways: [
    {
      stock_lot_id: 'lot-fuel-1',
      inventory_item_id: 'item-fuel-1',
      lot_code: 'LOT-JET-01',
      item_code: 'JET-A1',
      item_name: 'Jet A-1 Aviation Fuel',
      category: 'FUEL',
      criticality: 'CRITICAL',
      unit: 'LITERS',
      location_id: 'loc-1',
      location_name: 'Maitri Fuel Depot',
      on_hand_quantity: '120.00',
      reserved_quantity: '20.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '100.00',
      reorder_point: '40.00',
      replenishment_lead_days: 20,
      reorder_buffer_days: 8.0,
      daily_burn_rate: '5.00',
      burn_rate_source: 'OBSERVED_TRANSACTIONS_14D',
      burn_rate_evidence: { observations: 4, window_days: 14 },
      runway_days: 20.0,
      exhaustion_at: '2026-10-10T12:00:00Z',
      next_inbound_at: '2026-10-17T12:00:00Z',
      resupply_gap_days: 7.0,
      runway_state: 'RESUPPLY_GAP',
      dependent_mission_id: 'msn-air-01',
      data_provenance: 'FORECAST',
    },
    {
      stock_lot_id: 'lot-rations-2',
      inventory_item_id: 'item-rations-2',
      lot_code: 'LOT-RAT-02',
      item_code: 'RAT-EMERG',
      item_name: 'Field Emergency Rations',
      category: 'FOOD',
      criticality: 'HIGH',
      unit: 'PACKS',
      location_id: 'loc-1',
      location_name: 'Maitri Main Store',
      on_hand_quantity: '60.00',
      reserved_quantity: '10.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '50.00',
      reorder_point: '60.00',
      replenishment_lead_days: 15,
      reorder_buffer_days: 12.0,
      daily_burn_rate: '5.00',
      burn_rate_source: 'CATALOG_BASELINE',
      burn_rate_evidence: { baseline_daily_burn_rate: 5.0 },
      runway_days: 10.0,
      exhaustion_at: '2026-09-30T12:00:00Z',
      next_inbound_at: '2026-09-28T12:00:00Z',
      resupply_gap_days: 0.0,
      runway_state: 'AT_RISK',
      dependent_mission_id: null,
      data_provenance: 'FORECAST',
    },
    {
      stock_lot_id: 'lot-oxygen-3',
      inventory_item_id: 'item-oxygen-3',
      lot_code: 'LOT-O2-03',
      item_code: 'MED-O2',
      item_name: 'Medical Oxygen Cylinders',
      category: 'MEDICAL',
      criticality: 'LIFE_SUPPORT',
      unit: 'CYLINDERS',
      location_id: 'loc-1',
      location_name: 'Maitri Medical Bay',
      on_hand_quantity: '25.00',
      reserved_quantity: '5.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '20.00',
      reorder_point: '30.00',
      replenishment_lead_days: 20,
      reorder_buffer_days: 15.0,
      daily_burn_rate: '2.00',
      burn_rate_source: 'OBSERVED_TRANSACTIONS_14D',
      burn_rate_evidence: { observations: 2, window_days: 14 },
      runway_days: 10.0,
      exhaustion_at: '2026-09-30T12:00:00Z',
      next_inbound_at: null,
      resupply_gap_days: 0.0,
      runway_state: 'NO_INBOUND_SCHEDULED',
      dependent_mission_id: null,
      data_provenance: 'FORECAST',
    },
    {
      stock_lot_id: 'lot-water-4',
      inventory_item_id: 'item-water-4',
      lot_code: 'LOT-H2O-04',
      item_code: 'POT-H2O',
      item_name: 'Potable Water Reserve',
      category: 'WATER',
      criticality: 'HIGH',
      unit: 'LITERS',
      location_id: 'loc-1',
      location_name: 'Maitri Tank 1',
      on_hand_quantity: '1000.00',
      reserved_quantity: '0.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '1000.00',
      reorder_point: '200.00',
      replenishment_lead_days: 10,
      reorder_buffer_days: 10.0,
      daily_burn_rate: '20.00',
      burn_rate_source: 'OBSERVED_TRANSACTIONS_14D',
      burn_rate_evidence: { observations: 7, window_days: 14 },
      runway_days: 50.0,
      exhaustion_at: '2026-11-09T12:00:00Z',
      next_inbound_at: '2026-10-01T12:00:00Z',
      resupply_gap_days: 0.0,
      runway_state: 'COVERED',
      dependent_mission_id: null,
      data_provenance: 'FORECAST',
    },
    {
      stock_lot_id: 'lot-hyd-5',
      inventory_item_id: 'item-hyd-5',
      lot_code: 'LOT-HYD-05',
      item_code: 'HYD-FLUID',
      item_name: 'Hydraulic System Oil',
      category: 'CONSUMABLES',
      criticality: 'CRITICAL',
      unit: 'LITERS',
      location_id: 'loc-1',
      location_name: 'Maitri Maintenance Shed',
      on_hand_quantity: '40.00',
      reserved_quantity: '0.00',
      quarantined_quantity: '0.00',
      damaged_quantity: '0.00',
      available_quantity: '40.00',
      reorder_point: null,
      replenishment_lead_days: null,
      reorder_buffer_days: null,
      daily_burn_rate: '0.00',
      burn_rate_source: 'NO_CONSUMPTION_OBSERVED',
      burn_rate_evidence: { observations: 0, window_days: 14 },
      runway_days: null,
      exhaustion_at: null,
      next_inbound_at: null,
      resupply_gap_days: 0.0,
      runway_state: 'NO_CONSUMPTION_OBSERVED',
      dependent_mission_id: null,
      data_provenance: 'MEASURED',
    },
  ],
};

describe('ResourceRunwayPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton when loading', () => {
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ResourceRunwayPanel expeditionId="exp-1" />);

    expect(screen.getByText('Polar Consumables & Utility Runway')).toBeInTheDocument();
  });

  it('renders error state on API error', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'));
    renderWithProviders(<ResourceRunwayPanel expeditionId="exp-1" />);

    await waitFor(() => {
      expect(
        screen.getByText('Failed to evaluate polar resource runway projections')
      ).toBeInTheDocument();
    });
  });

  it('renders empty state when no candidates found', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      ...mockSummary,
      total_candidates: 0,
      items_with_resupply_gap: 0,
      items_at_risk: 0,
      runways: [],
    });

    renderWithProviders(<ResourceRunwayPanel expeditionId="exp-1" />);

    await waitFor(() => {
      expect(
        screen.getByText('No consumable inventory items tracked for this expedition.')
      ).toBeInTheDocument();
    });
  });

  it('renders normal runway cards with distinct states, values, and provenance tags', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);
    renderWithProviders(<ResourceRunwayPanel expeditionId="exp-1" />);

    await waitFor(() => {
      // Header and compact disclaimer
      expect(screen.getByText('Polar Consumables & Utility Runway')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Runway is projected from recorded inventory issues and scheduled inbound stock.'
        )
      ).toBeInTheDocument();

      // Summary metrics
      expect(screen.getByText('Monitored Lots')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('Resupply Gaps')).toBeInTheDocument();
      expect(screen.getByText('At Risk / No Inbound')).toBeInTheDocument();
      expect(screen.getByText('10.0 d')).toBeInTheDocument();

      // Items rendered
      expect(screen.getByText('Jet A-1 Aviation Fuel')).toBeInTheDocument();
      expect(screen.getByText('Field Emergency Rations')).toBeInTheDocument();
      expect(screen.getByText('Medical Oxygen Cylinders')).toBeInTheDocument();
      expect(screen.getByText('Potable Water Reserve')).toBeInTheDocument();
      expect(screen.getByText('Hydraulic System Oil')).toBeInTheDocument();

      // State Badges
      expect(screen.getByText('RESUPPLY GAP')).toBeInTheDocument();
      expect(screen.getByText('AT RISK')).toBeInTheDocument();
      expect(screen.getByText('NO INBOUND SCHEDULED')).toBeInTheDocument();
      expect(screen.getByText('COVERED')).toBeInTheDocument();
      expect(screen.getByText('NO CONSUMPTION')).toBeInTheDocument();

      // Provenance tags
      const forecastTags = screen.getAllByText('[FORECAST]');
      expect(forecastTags.length).toBeGreaterThan(0);
      const measuredTags = screen.getAllByText('[MEASURED]');
      expect(measuredTags.length).toBeGreaterThan(0);
      const derivedTags = screen.getAllByText('[DERIVED]');
      expect(derivedTags.length).toBeGreaterThan(0);

      // Resupply Gap critical notice
      expect(screen.getByText(/Resupply Gap Deficit: 7.0 days/i)).toBeInTheDocument();
    });
  });

  it('invokes onInitiateReplan callback with item context when Initiate Replan is clicked', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);
    const onInitiateReplan = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(
      <ResourceRunwayPanel expeditionId="exp-1" onInitiateReplan={onInitiateReplan} />
    );

    await waitFor(() => {
      expect(screen.getByText('Jet A-1 Aviation Fuel')).toBeInTheDocument();
    });

    // Find Initiate Replan buttons
    const replanButtons = screen.getAllByRole('button', { name: /initiate replan/i });
    expect(replanButtons.length).toBeGreaterThan(0);

    // Click the first one (for Jet A-1 which has RESUPPLY_GAP)
    await user.click(replanButtons[0]);

    expect(onInitiateReplan).toHaveBeenCalledTimes(1);
    expect(onInitiateReplan).toHaveBeenCalledWith(
      expect.objectContaining({
        item_code: 'JET-A1',
        runway_state: 'RESUPPLY_GAP',
        resupply_gap_days: 7.0,
      })
    );
  });

  it('filters resource cards when filter pills are clicked', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockSummary);
    const user = userEvent.setup();

    renderWithProviders(<ResourceRunwayPanel expeditionId="exp-1" />);

    await waitFor(() => {
      expect(screen.getByText('Jet A-1 Aviation Fuel')).toBeInTheDocument();
    });

    // Filter to Resupply Gaps only
    const gapsPill = screen.getByRole('button', { name: /resupply gaps/i });
    await user.click(gapsPill);

    expect(screen.getByText('Jet A-1 Aviation Fuel')).toBeInTheDocument();
    expect(screen.queryByText('Potable Water Reserve')).not.toBeInTheDocument();
    expect(screen.queryByText('Hydraulic System Oil')).not.toBeInTheDocument();

    // Filter to Covered
    const coveredPill = screen.getByRole('button', { name: /covered/i });
    await user.click(coveredPill);

    expect(screen.getByText('Potable Water Reserve')).toBeInTheDocument();
    expect(screen.queryByText('Jet A-1 Aviation Fuel')).not.toBeInTheDocument();
  });
});
