import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '../../components/shared/PageHeader';
import { ProvenanceTag } from '../../components/shared/ProvenanceTag';
import { LoadingSkeleton } from '../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../components/shared/ErrorDisplay';
import { EmptyState } from '../../components/shared/EmptyState';
import { useControlTowerOverview } from './hooks/useControlTower';
import { ExpeditionContextBar } from './components/ExpeditionContextBar';
import { ScenarioCockpitBanner } from './components/ScenarioCockpitBanner';
import { IncidentEscalationBanner } from './components/IncidentEscalationBanner';
import { MissionReadinessGrid } from './components/MissionReadinessGrid';
import { ActiveConstraintsFeed } from './components/ActiveConstraintsFeed';
import { DecisionQueuePanel } from './components/DecisionQueuePanel';
import { OperationalEventsFeed } from './components/OperationalEventsFeed';
import { ConsequentialAuditTimeline } from './components/ConsequentialAuditTimeline';
import { InitiateReplanModal } from './components/InitiateReplanModal';
import { MitigationOptionsExplorer } from './components/MitigationOptionsExplorer';
import { ApprovalModal } from './components/ApprovalModal';
import { OfflineSyncIndicator } from './components/OfflineSyncIndicator';
import { OfflineSyncDrawer } from './components/OfflineSyncDrawer';
import { OfflineSyncSection } from './components/OfflineSyncSection';
import { ResourceRunwayPanel } from './components/ResourceRunwayPanel';
import { PersonnelSafetyPanel } from './components/PersonnelSafetyPanel';
import type {
  MissionOperationsItem,
  ControlTowerConstraintItem,
  ResourceRunwayItem,
} from '../../lib/types/api';

interface InitiateModalState {
  isOpen: boolean;
  missionId?: string | null;
  missionCode?: string | null;
  missionTitle?: string | null;
  constraintCode?: string | null;
  reason?: string;
}

export function ControlTowerPage() {
  const { data: overview, isLoading, error } = useControlTowerOverview();
  const [selectedExpeditionId, setSelectedExpeditionId] = useState<string | null>(null);

  // Modal states for closed-loop operational workflows
  const [initiateModalState, setInitiateModalState] = useState<InitiateModalState>({
    isOpen: false,
  });
  const [optionsExplorerState, setOptionsExplorerState] = useState<{
    isOpen: boolean;
    replanId: string | null;
  }>({
    isOpen: false,
    replanId: null,
  });
  const [approvalModalState, setApprovalModalState] = useState<{
    isOpen: boolean;
    recommendationId: string | null;
  }>({
    isOpen: false,
    recommendationId: null,
  });
  const [isSyncDrawerOpen, setIsSyncDrawerOpen] = useState(false);

  // Synchronize initial expedition selection with the overview response
  useEffect(() => {
    if (!selectedExpeditionId && overview?.expeditions && overview.expeditions.length > 0) {
      setSelectedExpeditionId(overview.expeditions[0].expedition_id);
    }
  }, [overview, selectedExpeditionId]);

  const [searchParams, setSearchParams] = useSearchParams();
  const urlIncidentId = searchParams.get('incidentId');
  const urlReplanId = searchParams.get('replanId');

  const handleDismissIncidentContext = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('incidentId');
    nextParams.delete('replanId');
    setSearchParams(nextParams, { replace: true });
  };

  const handleExploreIncidentOptions = (targetReplanId: string) => {
    setOptionsExplorerState({
      isOpen: true,
      replanId: targetReplanId,
    });
  };

  const activeExpeditionId =
    selectedExpeditionId ??
    (overview?.expeditions && overview.expeditions.length > 0
      ? overview.expeditions[0].expedition_id
      : null);

  const handleInitiateMissionReplan = (mission: MissionOperationsItem) => {
    setInitiateModalState({
      isOpen: true,
      missionId: mission.mission_id,
      missionCode: mission.code,
      missionTitle: mission.title,
      reason: `Operational disruption affecting mission ${mission.code} (${mission.title}); operator initiated replanning required.`,
    });
  };

  const handleInitiateConstraintReplan = (constraint: ControlTowerConstraintItem) => {
    setInitiateModalState({
      isOpen: true,
      constraintCode: constraint.code,
      reason: `Hard constraint violation detected for ${constraint.code}: ${constraint.reason}`,
    });
  };

  const handleInitiateRunwayReplan = (item: ResourceRunwayItem) => {
    setInitiateModalState({
      isOpen: true,
      missionId: item.dependent_mission_id ?? undefined,
      constraintCode: item.active_constraint_id ? 'RESOURCE_RUNWAY_HORIZON' : undefined,
      reason: `Consumables depletion risk on ${item.item_code} (${item.item_name}) at ${item.location_name || 'station'}. Operational runway estimated at ${item.runway_days ?? 'critical'} days; resupply gap is ${item.resupply_gap_days} days.`,
    });
  };

  const handleInitiatePersonnelReplan = (context: {
    personId?: string;
    personCode?: string;
    teamId?: string;
    teamCode?: string;
    missionId?: string;
    missionCode?: string;
    reason: string;
  }) => {
    setInitiateModalState({
      isOpen: true,
      missionId: context.missionId,
      missionCode: context.missionCode,
      reason: context.reason,
    });
  };

  const handleReplanCreated = (newReplanId: string) => {
    setOptionsExplorerState({
      isOpen: true,
      replanId: newReplanId,
    });
  };

  const handleSelectRecommendation = (recId: string) => {
    setApprovalModalState({
      isOpen: true,
      recommendationId: recId,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Control Tower"
        subtitle="Operational command center & mission readiness posture"
        actions={
          <div className="flex items-center gap-3">
            <OfflineSyncIndicator onOpenDrawer={() => setIsSyncDrawerOpen(true)} />
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

          {/* Incident Escalation Context Banner (A7) */}
          {urlIncidentId && urlReplanId && (
            <IncidentEscalationBanner
              incidentId={urlIncidentId}
              replanId={urlReplanId}
              onExploreOptions={handleExploreIncidentOptions}
              onDismiss={handleDismissIncidentContext}
            />
          )}

          {/* Polar Disruption Scenario Injection Cockpit */}
          <ScenarioCockpitBanner expeditionId={activeExpeditionId} />

          {/* Store-and-Forward Offline Synchronization Posture (A8) */}
          <OfflineSyncSection
            expeditionId={activeExpeditionId}
            onOpenDrawer={() => setIsSyncDrawerOpen(true)}
          />

          {/* Polar Utility & Consumables Runway Engine (A9) */}
          <ResourceRunwayPanel
            expeditionId={activeExpeditionId}
            onInitiateReplan={handleInitiateRunwayReplan}
          />

          {/* Personnel & Field Team Deployment Safety Engine (A10) */}
          <PersonnelSafetyPanel
            expeditionId={activeExpeditionId}
            onInitiateReplan={handleInitiatePersonnelReplan}
          />

          {/* Mission Readiness Grid & Operations */}
          <MissionReadinessGrid
            expeditionId={activeExpeditionId}
            onInitiateReplan={handleInitiateMissionReplan}
          />

          {/* Decision Queue & Human Governance Boundary */}
          <DecisionQueuePanel
            expeditionId={activeExpeditionId}
            onSelectRecommendation={handleSelectRecommendation}
            onViewReplanOptions={(replanId) =>
              setOptionsExplorerState({ isOpen: true, replanId })
            }
          />

          {/* Active Constraints & Invariants */}
          <ActiveConstraintsFeed
            expeditionId={activeExpeditionId}
            onInitiateReplanForConstraint={handleInitiateConstraintReplan}
          />

          {/* Operational Events Chronological Ledger */}
          <OperationalEventsFeed expeditionId={activeExpeditionId} />

          {/* Consequential Audit Timeline */}
          <ConsequentialAuditTimeline expeditionId={activeExpeditionId} />

          {/* ─── Modal Workflows ─── */}

          {/* 1. Initiate Replan Modal */}
          <InitiateReplanModal
            isOpen={initiateModalState.isOpen}
            onClose={() => setInitiateModalState({ isOpen: false })}
            expeditionId={activeExpeditionId}
            missionId={initiateModalState.missionId}
            missionCode={initiateModalState.missionCode}
            missionTitle={initiateModalState.missionTitle}
            constraintCode={initiateModalState.constraintCode}
            initialReason={initiateModalState.reason}
            onReplanCreated={handleReplanCreated}
          />

          {/* 2. Candidate Mitigation Options Explorer Modal */}
          <MitigationOptionsExplorer
            isOpen={optionsExplorerState.isOpen}
            onClose={() => setOptionsExplorerState({ isOpen: false, replanId: null })}
            replanId={optionsExplorerState.replanId}
            expeditionId={activeExpeditionId}
            onSelectRecommendation={handleSelectRecommendation}
          />

          {/* 3. Canonical Approval & Governance Modal */}
          {approvalModalState.isOpen && approvalModalState.recommendationId && (
            <ApprovalModal
              recommendationId={approvalModalState.recommendationId}
              onClose={() => setApprovalModalState({ isOpen: false, recommendationId: null })}
              expeditionId={activeExpeditionId}
            />
          )}

          {/* 4. Offline Synchronization Outbox Drawer (A8) */}
          <OfflineSyncDrawer
            isOpen={isSyncDrawerOpen}
            onClose={() => setIsSyncDrawerOpen(false)}
          />
        </>
      )}
    </div>
  );
}

export default ControlTowerPage;
