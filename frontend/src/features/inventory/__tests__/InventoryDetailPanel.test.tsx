import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { InventoryDetailPanel } from '../InventoryDetailPanel';
import { apiClient } from '../../../lib/api/client';
import type { InventoryItem, InventoryStockLot, StockAvailability, InventoryTransaction } from '../../../lib/types/api';

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

const mockItem: InventoryItem = {
  id: 'item-101',
  code: 'RATION-PACK-01',
  name: 'Polar Field Rations 7-Day',
  category: 'FOOD',
  description: 'Freeze-dried 3500kcal daily pack',
  criticality: 'LIFE_SUPPORT',
  unit_of_measure: 'PACK',
  minimum_temperature_c: '-50',
  maximum_temperature_c: '20',
  hazmat_class: null,
  is_shelf_life_controlled: true,
  default_shelf_life_days: 720,
  data_provenance: 'MEASURED',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockStockLots: InventoryStockLot[] = [
  {
    id: 'lot-201',
    lot_number: 'LOT-2026-001',
    inventory_item_id: 'item-101',
    location_id: 'loc-bharati-storage',
    status: 'AVAILABLE',
    on_hand_quantity: '150',
    reserved_quantity: '20',
    quarantined_quantity: '0',
    damaged_quantity: '0',
    available_quantity: '130',
    reorder_point: '50',
    is_deficit: false,
    received_at: '2026-01-05T00:00:00Z',
    expiry_date: '2027-12-31T00:00:00Z',
    notes: 'Stored in main food vault',
    data_provenance: 'MEASURED',
    created_at: '2026-01-05T00:00:00Z',
    updated_at: '2026-01-05T00:00:00Z',
  },
];

const mockAvailability: StockAvailability = {
  stock_lot_id: 'lot-201',
  on_hand_quantity: '150',
  reserved_quantity: '20',
  quarantined_quantity: '0',
  damaged_quantity: '0',
  available_quantity: '130',
  reorder_point: '50',
  is_deficit: false,
  status: 'AVAILABLE',
};

const mockTransactions: InventoryTransaction[] = [
  {
    id: 'tx-301',
    stock_lot_id: 'lot-201',
    transaction_type: 'RECEIPT',
    quantity: '150',
    balance_after: '150',
    reference_id: 'PO-9811',
    notes: 'Initial expedition stocking',
    data_provenance: 'MEASURED',
    created_at: '2026-01-05T08:00:00Z',
  },
];

describe('InventoryDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders item specifications, stock lots, and availability indicator', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/availability')) return Promise.resolve(mockAvailability);
      if (path.includes('/transactions')) return Promise.resolve(mockTransactions);
      if (path.includes('/stock-lots')) return Promise.resolve(mockStockLots);
      return Promise.resolve(null);
    });

    renderWithProviders(<InventoryDetailPanel item={mockItem} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText('LOT-2026-001').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Authoritative Availability')).toBeInTheDocument();
      expect(screen.getAllByText('130').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('STOCKED')).toBeInTheDocument();
      expect(screen.getByText('PO-9811')).toBeInTheDocument();
    });
  });

  it('displays deficit badge when is_deficit is true', async () => {
    const deficitAvailability: StockAvailability = {
      ...mockAvailability,
      available_quantity: '10',
      is_deficit: true,
    };

    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/availability')) return Promise.resolve(deficitAvailability);
      if (path.includes('/transactions')) return Promise.resolve(mockTransactions);
      if (path.includes('/stock-lots')) return Promise.resolve(mockStockLots);
      return Promise.resolve(null);
    });

    renderWithProviders(<InventoryDetailPanel item={mockItem} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('DEFICIT')).toBeInTheDocument();
    });
  });

  it('executes stock receipt workflow with confirmation dialog', async () => {
    vi.mocked(apiClient.get).mockImplementation((path: string) => {
      if (path.includes('/availability')) return Promise.resolve(mockAvailability);
      if (path.includes('/transactions')) return Promise.resolve(mockTransactions);
      if (path.includes('/stock-lots')) return Promise.resolve(mockStockLots);
      return Promise.resolve(null);
    });
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockStockLots[0], on_hand_quantity: '160' });

    const user = userEvent.setup();
    renderWithProviders(<InventoryDetailPanel item={mockItem} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText('LOT-2026-001').length).toBeGreaterThanOrEqual(1);
    });

    const qtyInput = screen.getByLabelText(/Quantity/i);
    await user.clear(qtyInput);
    await user.type(qtyInput, '10');

    const submitBtn = screen.getByRole('button', { name: /Execute RECEIVE/i });
    await user.click(submitBtn);

    // Confirm dialog appears
    await waitFor(() => {
      expect(screen.getByText(/Receive 10 units into lot LOT-2026-001\?/i)).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole('button', { name: 'Confirm Action' });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/inventory/stock-lots/lot-201/receive',
        expect.objectContaining({ quantity: 10 })
      );
    });
  });
});
