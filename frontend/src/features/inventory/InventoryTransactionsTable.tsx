import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import type { InventoryTransaction } from '../../lib/types/api';

interface Props {
  transactions: InventoryTransaction[];
  isLoading?: boolean;
}

export function InventoryTransactionsTable({ transactions, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs">
        Loading transaction ledger...
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 font-mono text-xs border border-slate-800 rounded bg-slate-900/30">
        No transaction ledger entries recorded for this lot.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-slate-800">
      <table className="w-full text-left text-xs" role="table" aria-label="Transaction ledger">
        <thead className="bg-slate-900 font-mono text-slate-400 uppercase tracking-wider border-b border-slate-800">
          <tr>
            <th className="px-3 py-2">Timestamp</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2 text-right">Quantity</th>
            <th className="px-3 py-2 text-right">Balance After</th>
            <th className="px-3 py-2">Reference</th>
            <th className="px-3 py-2">Provenance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-mono">
          {transactions.map((tx) => (
            <tr key={tx.id} className="hover:bg-slate-800/30">
              <td className="px-3 py-2 text-slate-400 whitespace-nowrap">
                {new Date(tx.created_at).toLocaleString()}
              </td>
              <td className="px-3 py-2 font-semibold text-cyan-300">
                {tx.transaction_type}
              </td>
              <td className="px-3 py-2 text-right font-semibold text-slate-200">
                {tx.quantity}
              </td>
              <td className="px-3 py-2 text-right text-emerald-400">
                {tx.balance_after}
              </td>
              <td className="px-3 py-2 text-slate-400 truncate max-w-[120px]" title={tx.reference_id ?? ''}>
                {tx.reference_id ? (tx.reference_id.length > 8 ? `${tx.reference_id.slice(0, 8)}...` : tx.reference_id) : '-'}
              </td>
              <td className="px-3 py-2">
                <ProvenanceTag provenance={tx.data_provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
