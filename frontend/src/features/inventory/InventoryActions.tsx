import { useState } from 'react';
import {
  useReceiveStock,
  useReserveStock,
  useReleaseStock,
  useIssueStock,
  useQuarantineStock,
  useTransitionStock,
} from './hooks/useInventoryMutations';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { INVENTORY_TRANSITIONS, type InventoryStockLot, type InventoryStatus } from '../../lib/types/api';

interface Props {
  lot: InventoryStockLot;
  onActionComplete?: () => void;
}

type ActionTab = 'RECEIVE' | 'RESERVE' | 'RELEASE' | 'ISSUE' | 'QUARANTINE' | 'TRANSITION';

export function InventoryActions({ lot, onActionComplete }: Props) {
  const [activeTab, setActiveTab] = useState<ActionTab>('RECEIVE');
  const [quantity, setQuantity] = useState<string>('1');
  const [reference, setReference] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [targetStatus, setTargetStatus] = useState<InventoryStatus | ''>('');
  const [issuedTo, setIssuedTo] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [confirmOpen, setConfirmOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<(() => Promise<unknown>) | null>(null);
  const [confirmTitle, setConfirmTitle] = useState<string>('');
  const [confirmMessage, setConfirmMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const receiveMutation = useReceiveStock(lot.id);
  const reserveMutation = useReserveStock(lot.id);
  const releaseMutation = useReleaseStock(lot.id);
  const issueMutation = useIssueStock(lot.id);
  const quarantineMutation = useQuarantineStock(lot.id);
  const transitionMutation = useTransitionStock(lot.id);

  const isSubmitting =
    receiveMutation.isPending ||
    reserveMutation.isPending ||
    releaseMutation.isPending ||
    issueMutation.isPending ||
    quarantineMutation.isPending ||
    transitionMutation.isPending;

  const validNextStatuses = INVENTORY_TRANSITIONS[lot.status] || [];

  const handleAction = (tab: ActionTab) => {
    setErrorMessage(null);
    const parsedQty = parseFloat(quantity);

    if (tab !== 'TRANSITION' && (!parsedQty || parsedQty <= 0)) {
      setErrorMessage('Quantity must be greater than 0.');
      return;
    }

    if (tab === 'ISSUE' && !issuedTo.trim()) {
      setErrorMessage('Issued-To recipient is required.');
      return;
    }

    if (tab === 'QUARANTINE' && !reason.trim()) {
      setErrorMessage('Quarantine reason is required.');
      return;
    }

    if (tab === 'TRANSITION' && !targetStatus) {
      setErrorMessage('Please select a valid target status.');
      return;
    }

    let title = '';
    let msg = '';
    let actionFn: () => Promise<unknown>;

    switch (tab) {
      case 'RECEIVE':
        title = 'Receive Stock';
        msg = `Receive ${parsedQty} units into lot ${lot.lot_number}?`;
        actionFn = () =>
          receiveMutation.mutateAsync({
            quantity: parsedQty,
            supplier: reference.trim() || undefined,
            receipt_reference: reference.trim() || undefined,
            notes: notes.trim() || undefined,
          });
        break;
      case 'RESERVE':
        title = 'Reserve Stock';
        msg = `Reserve ${parsedQty} units from available stock in lot ${lot.lot_number}?`;
        actionFn = () =>
          reserveMutation.mutateAsync({
            quantity: parsedQty,
            reservation_reference: reference.trim() || undefined,
            notes: notes.trim() || undefined,
          });
        break;
      case 'RELEASE':
        title = 'Release Reservation';
        msg = `Release ${parsedQty} reserved units back to available stock in lot ${lot.lot_number}?`;
        actionFn = () =>
          releaseMutation.mutateAsync({
            quantity: parsedQty,
            release_reference: reference.trim() || undefined,
            notes: notes.trim() || undefined,
          });
        break;
      case 'ISSUE':
        title = 'Issue Stock';
        msg = `Issue ${parsedQty} units from lot ${lot.lot_number} to recipient ${issuedTo}?`;
        actionFn = () =>
          issueMutation.mutateAsync({
            quantity: parsedQty,
            issued_to: issuedTo.trim(),
            issue_reference: reference.trim() || undefined,
            notes: notes.trim() || undefined,
          });
        break;
      case 'QUARANTINE':
        title = 'Quarantine Stock';
        msg = `Quarantine ${parsedQty} units from lot ${lot.lot_number}?`;
        actionFn = () =>
          quarantineMutation.mutateAsync({
            quantity: parsedQty,
            quarantine_reason: reason.trim(),
            notes: notes.trim() || undefined,
          });
        break;
      case 'TRANSITION':
        title = 'Transition Lot Status';
        msg = `Transition lot status from ${lot.status} to ${targetStatus}?`;
        actionFn = () =>
          transitionMutation.mutateAsync({
            status: targetStatus as InventoryStatus,
            reason: reason.trim() || undefined,
          });
        break;
    }

    setConfirmTitle(title);
    setConfirmMessage(msg);
    setPendingAction(() => actionFn);
    setConfirmOpen(true);
  };

  const executeConfirmedAction = async () => {
    if (!pendingAction) return;
    try {
      await pendingAction();
      setConfirmOpen(false);
      setPendingAction(null);
      setQuantity('1');
      setReference('');
      setNotes('');
      setIssuedTo('');
      setReason('');
      setTargetStatus('');
      onActionComplete?.();
    } catch (err) {
      setConfirmOpen(false);
      setErrorMessage(err instanceof Error ? err.message : 'Operation failed.');
    }
  };

  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
      <div className="flex border-b border-slate-800 pb-2 mb-4 gap-1 overflow-x-auto text-xs font-mono">
        {(['RECEIVE', 'RESERVE', 'RELEASE', 'ISSUE', 'QUARANTINE', 'TRANSITION'] as ActionTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => {
              setActiveTab(tab);
              setErrorMessage(null);
            }}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap ${
              activeTab === tab
                ? 'bg-cyan-900/60 text-cyan-200 border border-cyan-700'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {errorMessage && (
        <div className="mb-4">
          <ErrorDisplay error={new Error(errorMessage)} title="Inventory Action Failed" />
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAction(activeTab);
        }}
        className="space-y-3 font-mono text-xs"
      >
        {activeTab !== 'TRANSITION' ? (
          <div>
            <label htmlFor="lot-quantity" className="block text-slate-400 mb-1">
              Quantity <span className="text-rose-400">*</span>
            </label>
            <input
              id="lot-quantity"
              type="number"
              step="any"
              min="0.001"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>
        ) : (
          <div>
            <label htmlFor="target-status" className="block text-slate-400 mb-1">
              Target Status <span className="text-rose-400">*</span>
            </label>
            <select
              id="target-status"
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value as InventoryStatus)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            >
              <option value="">Select next status...</option>
              {validNextStatuses.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
            {validNextStatuses.length === 0 && (
              <p className="mt-1 text-slate-500 text-[11px]">
                Status {lot.status} has no further valid state machine transitions.
              </p>
            )}
          </div>
        )}

        {activeTab === 'ISSUE' && (
          <div>
            <label htmlFor="issued-to" className="block text-slate-400 mb-1">
              Issued To (Recipient/Team) <span className="text-rose-400">*</span>
            </label>
            <input
              id="issued-to"
              type="text"
              value={issuedTo}
              onChange={(e) => setIssuedTo(e.target.value)}
              placeholder="e.g. Field Team Charlie"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>
        )}

        {activeTab === 'QUARANTINE' && (
          <div>
            <label htmlFor="quarantine-reason" className="block text-slate-400 mb-1">
              Quarantine Reason <span className="text-rose-400">*</span>
            </label>
            <input
              id="quarantine-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Cold chain excursion detected"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>
        )}

        {activeTab === 'TRANSITION' && (
          <div>
            <label htmlFor="transition-reason" className="block text-slate-400 mb-1">
              Transition Justification
            </label>
            <input
              id="transition-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Operational justification"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
        )}

        {activeTab !== 'TRANSITION' && (
          <div>
            <label htmlFor="lot-reference" className="block text-slate-400 mb-1">
              Reference / Identifier
            </label>
            <input
              id="lot-reference"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. PO-9812 / MISSION-ALFA"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
        )}

        <div>
          <label htmlFor="lot-notes" className="block text-slate-400 mb-1">
            Operational Notes
          </label>
          <input
            id="lot-notes"
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Audit/operational remarks"
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting || (activeTab === 'TRANSITION' && validNextStatuses.length === 0)}
          className="w-full mt-2 py-2 px-4 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-colors"
        >
          {isSubmitting ? 'Processing...' : `Execute ${activeTab}`}
        </button>
      </form>

      <ConfirmDialog
        open={confirmOpen}
        title={confirmTitle}
        message={confirmMessage}
        confirmLabel="Confirm Action"
        onConfirm={executeConfirmedAction}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
