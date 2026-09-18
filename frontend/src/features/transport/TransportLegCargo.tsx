import { useState } from 'react';
import { Package, Plus } from 'lucide-react';
import { useTransportLegCargo } from './hooks/useTransportLegCargo';
import { AssignCargoWorkflow } from './AssignCargoWorkflow';
import { EntityCode } from '../../components/shared/EntityCode';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { RiskBadge } from '../cargo/RiskBadge';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import type { CargoConsignment, CargoRiskLevel } from '../../lib/types/api';

interface Props {
  legId: string;
  onSelectConsignment?: (consignmentId: string) => void;
}

export function TransportLegCargo({ legId, onSelectConsignment }: Props) {
  const { data: cargoList, isLoading, error } = useTransportLegCargo(legId);
  const [showAssign, setShowAssign] = useState(false);

  if (isLoading) {
    return <LoadingSkeleton lines={3} />;
  }

  if (error) {
    return <ErrorDisplay error={error} title="Failed to load manifested cargo" />;
  }

  const items = cargoList ?? [];
  const assignedIds = items.map((c) => c.id);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-cyan-400" aria-hidden="true" />
          <h4 className="text-xs font-semibold text-slate-200">
            Manifested Cargo ({items.length})
          </h4>
        </div>
        <button
          type="button"
          onClick={() => setShowAssign(!showAssign)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-cyan-950/70 text-cyan-300 border border-cyan-800/80 hover:bg-cyan-900/60 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          {showAssign ? 'Cancel' : 'Manifest Cargo'}
        </button>
      </div>

      {showAssign && (
        <AssignCargoWorkflow
          legId={legId}
          alreadyAssignedIds={assignedIds}
          onSuccess={() => setShowAssign(false)}
          onCancel={() => setShowAssign(false)}
        />
      )}

      {items.length === 0 ? (
        <div className="p-4 text-center rounded-lg border border-dashed border-slate-800 text-slate-500 text-xs">
          No cargo consignments currently manifested on this leg.
        </div>
      ) : (
        <div className="rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-medium">
                <th className="py-2 px-3 font-mono">Consignment</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Risk Level</th>
                <th className="py-2 px-3 text-right">Priority</th>
                <th className="py-2 px-3">Required By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {items.map((c: CargoConsignment) => (
                <tr
                  key={c.id}
                  onClick={() => onSelectConsignment?.(c.id)}
                  className="hover:bg-slate-900/40 cursor-pointer"
                >
                  <td className="py-2 px-3">
                    <EntityCode code={c.code} />
                  </td>
                  <td className="py-2 px-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="py-2 px-3">
                    <RiskBadge level={c.risk_level as CargoRiskLevel} />
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-slate-300">
                    P{c.priority}
                  </td>
                  <td className="py-2 px-3 font-mono text-slate-400">
                    {new Date(c.required_by_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
