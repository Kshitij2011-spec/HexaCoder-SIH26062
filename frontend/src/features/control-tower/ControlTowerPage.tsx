import { useState, useEffect } from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { EmptyState } from '../../components/shared/EmptyState';
import { useControlTowerOverview } from './hooks/useControlTower';
import { ExpeditionContextBar } from './components/ExpeditionContextBar';
import { MissionReadinessGrid } from './components/MissionReadinessGrid';
import { ActiveConstraintsFeed } from './components/ActiveConstraintsFeed';
import { DecisionQueuePanel } from './components/DecisionQueuePanel';
import { OperationalEventsFeed } from './components/OperationalEventsFeed';
import { ConsequentialAuditTimeline } from './components/ConsequentialAuditTimeline';

export function ControlTowerPage() {
  const { data: overview, isLoading, error } = useControlTowerOverview();
  const [selectedExpeditionId, setSelectedExpeditionId] = useState<string | null>(null);

  // Synchronize initial expedition selection with the overview response
  useEffect(() => {
    if (!selectedExpeditionId && overview?.expeditions && overview.expeditions.length > 0) {
      setSelectedExpeditionId(overview.expeditions[0].expedition_id);
    }
  }, [overview, selectedExpeditionId]);

  const activeExpeditionId =
    selectedExpeditionId ??
    (overview?.expeditions && overview.expeditions.length > 0
      ? overview.expeditions[0].expedition_id
      : null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Control Tower"
        subtitle="Operational command center & mission readiness posture"
        actions={
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">
              Campaigns: {overview?.total_expeditions ?? 0}
            </span>
            <ProvenanceTag provenance={overview?.data_provenance ?? 'DERIVED'} />
          </div>
        }
      />

      {/* ─── Loading State ─── */}
      {isLoading && (
        <div aria-busy="true" className="space-y-4">
          <LoadingSkeleton lines={4} />
          <LoadingSkeleton lines={8} />
        </div>
      )}

      {/* ─── Error State ─── */}
      {error && (
        <ErrorDisplay
          error={error}
          title="Failed to load Control Tower operational overview"
        />
      )}

      {/* ─── Empty State ─── */}
      {!isLoading && !error && (!overview?.expeditions || overview.expeditions.length === 0) && (
        <EmptyState
          title="No expeditions available"
          message="No active polar expeditions were found for operational monitoring."
        />
      )}

      {/* ─── Active Content ─── */}
      {!isLoading && !error && overview?.expeditions && overview.expeditions.length > 0 && activeExpeditionId && (
        <>
          {/* Expedition Context & Posture Header */}
          <ExpeditionContextBar
            selectedExpeditionId={activeExpeditionId}
            onSelectExpedition={setSelectedExpeditionId}
            expeditions={overview.expeditions}
            isLoadingExpeditions={isLoading}
          />

          {/* Mission Readiness Grid & Operations */}
          <MissionReadinessGrid expeditionId={activeExpeditionId} />

          {/* Decision Queue & Human Governance Boundary */}
          <DecisionQueuePanel expeditionId={activeExpeditionId} />

          {/* Active Constraints & Invariants */}
          <ActiveConstraintsFeed expeditionId={activeExpeditionId} />

          {/* Operational Events Chronological Ledger */}
          <OperationalEventsFeed expeditionId={activeExpeditionId} />

          {/* Consequential Audit Timeline */}
          <ConsequentialAuditTimeline expeditionId={activeExpeditionId} />
        </>
      )}
    </div>
  );
}

export default ControlTowerPage;
