import React, { useState } from 'react';
import {
  Users,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  UserCheck,
  UserX,
  Compass,
  Building2,
  ArrowRightLeft,
  ChevronRight,
  CheckCircle2,
  RotateCcw,
} from 'lucide-react';
import { ProvenanceTag } from '../../../components/shared/ProvenanceTag';
import { EntityCode } from '../../../components/shared/EntityCode';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorDisplay } from '../../../components/shared/ErrorDisplay';
import { usePersonnelSafety } from '../hooks/useControlTower';
import type { PersonnelSafetyStatus } from '../../../lib/types/api';

export interface PersonnelSafetyPanelProps {
  expeditionId: string;
  onInitiateReplan?: (context: {
    personId?: string;
    personCode?: string;
    teamId?: string;
    teamCode?: string;
    missionId?: string;
    missionCode?: string;
    reason: string;
  }) => void;
}

const STATUS_CONFIG: Record<
  PersonnelSafetyStatus,
  {
    label: string;
    badgeClass: string;
    borderClass: string;
    bgClass: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  CLEAR: {
    label: 'CLEAR',
    badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-600/80',
    borderClass: 'border-emerald-800/40',
    bgClass: 'bg-emerald-950/10',
    icon: ShieldCheck,
  },
  WARNING: {
    label: 'WARNING',
    badgeClass: 'bg-amber-950/80 text-amber-300 border-amber-600/80',
    borderClass: 'border-amber-800/40',
    bgClass: 'bg-amber-950/10',
    icon: AlertTriangle,
  },
  BLOCKED: {
    label: 'BLOCKED',
    badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-600/80',
    borderClass: 'border-rose-800/40',
    bgClass: 'bg-rose-950/10',
    icon: ShieldAlert,
  },
};

export const PersonnelSafetyPanel: React.FC<PersonnelSafetyPanelProps> = ({
  expeditionId,
  onInitiateReplan,
}) => {
  const { data: summary, isLoading, error, refetch } = usePersonnelSafety(expeditionId);
  const [activeTab, setActiveTab] = useState<'ALL' | 'BLOCKED' | 'WARNINGS' | 'TEAMS' | 'OPPORTUNITIES'>('ALL');

  if (isLoading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <LoadingSkeleton className="h-6 w-48" />
          <LoadingSkeleton className="h-6 w-24" />
        </div>
        <div className="grid grid-cols-5 gap-3 mb-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <LoadingSkeleton key={i} className="h-16 w-full" />
          ))}
        </div>
        <LoadingSkeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <ErrorDisplay
          error={error || new Error('Failed to load expedition personnel deployment safety evaluation.')}
          title="Personnel Safety Evaluation Unavailable"
        />
      </div>
    );
  }

  const overallStatus = summary?.overall_status ?? 'CLEAR';
  const statusCfg = STATUS_CONFIG[overallStatus] || STATUS_CONFIG.CLEAR;
  const StatusIcon = statusCfg.icon;

  const findings = Array.isArray(summary?.findings) ? summary.findings : [];
  const teams = Array.isArray(summary?.teams) ? summary.teams : [];
  const opportunities = Array.isArray(summary?.reassignment_opportunities) ? summary.reassignment_opportunities : [];

  const blockedFindings = findings.filter((f) => f.status === 'BLOCKED');
  const warningFindings = findings.filter((f) => f.status === 'WARNING');

  const filteredFindings =
    activeTab === 'BLOCKED'
      ? blockedFindings
      : activeTab === 'WARNINGS'
      ? warningFindings
      : findings;

  return (
    <section
      data-testid="personnel-safety-panel"
      className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 shadow-sm"
    >
      {/* ─── Header ─── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg border ${statusCfg.borderClass} ${statusCfg.bgClass}`}>
            <StatusIcon className="w-5 h-5 text-slate-200" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-100 uppercase tracking-wide">
                Personnel & Field Team Safety
              </h3>
              <ProvenanceTag provenance={summary.data_provenance || 'DERIVED'} />
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic deployment safety compliance, medical clearance verification, and polar buddy pairing
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            data-testid="overall-posture-badge"
            className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full border ${statusCfg.badgeClass}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            {statusCfg.label}
          </span>
          <button
            onClick={() => refetch()}
            title="Refresh personnel safety evaluation"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ─── Metrics Grid ─── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Users className="w-3.5 h-3.5 text-sky-400" />
            <span>Total Force</span>
          </div>
          <div className="text-xl font-bold text-slate-100">{summary?.total_personnel ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Assigned campaign crew</div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Medically Cleared</span>
          </div>
          <div className="text-xl font-bold text-emerald-400">{summary?.cleared_count ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Fit for polar deployment</div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <UserX className="w-3.5 h-3.5 text-rose-400" />
            <span>Medical Hold</span>
          </div>
          <div className={`text-xl font-bold ${(summary?.medical_hold_count ?? 0) > 0 ? 'text-rose-400' : 'text-slate-100'}`}>
            {summary?.medical_hold_count ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Unready / clearance pending</div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Building2 className="w-3.5 h-3.5 text-blue-400" />
            <span>Station Base</span>
          </div>
          <div className="text-xl font-bold text-slate-100">{summary?.at_station_count ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Available for reassignment</div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Compass className="w-3.5 h-3.5 text-amber-400" />
            <span>Field Deployed</span>
          </div>
          <div className="text-xl font-bold text-slate-100">{summary?.field_deployed_count ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Traverse & survey teams</div>
        </div>
      </div>

      {/* ─── Navigation Tabs ─── */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2 text-xs">
        <button
          onClick={() => setActiveTab('ALL')}
          className={`px-3 py-1 rounded transition font-medium ${
            activeTab === 'ALL'
              ? 'bg-sky-600/30 text-sky-300 border border-sky-500/50'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          All Findings ({findings.length})
        </button>
        <button
          onClick={() => setActiveTab('BLOCKED')}
          className={`px-3 py-1 rounded transition font-medium ${
            activeTab === 'BLOCKED'
              ? 'bg-rose-950/80 text-rose-300 border border-rose-600/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          Blocked ({blockedFindings.length})
        </button>
        <button
          onClick={() => setActiveTab('WARNINGS')}
          className={`px-3 py-1 rounded transition font-medium ${
            activeTab === 'WARNINGS'
              ? 'bg-amber-950/80 text-amber-300 border border-amber-600/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          Warnings ({warningFindings.length})
        </button>
        <button
          onClick={() => setActiveTab('TEAMS')}
          className={`px-3 py-1 rounded transition font-medium ${
            activeTab === 'TEAMS'
              ? 'bg-slate-800 text-slate-200 border border-slate-700'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          Teams & Crews ({teams.length})
        </button>
        {opportunities.length > 0 && (
          <button
            onClick={() => setActiveTab('OPPORTUNITIES')}
            className={`px-3 py-1 rounded transition font-medium ${
              activeTab === 'OPPORTUNITIES'
                ? 'bg-purple-950/80 text-purple-300 border border-purple-600/80'
                : 'text-purple-400 hover:text-purple-300 hover:bg-slate-800'
            }`}
          >
            Reassignment Candidates ({opportunities.length})
          </button>
        )}
      </div>

      {/* ─── Content: Findings View ─── */}
      {activeTab !== 'TEAMS' && activeTab !== 'OPPORTUNITIES' && (
        <div className="space-y-3">
          {filteredFindings.length === 0 ? (
            <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
              <div className="text-sm font-medium text-slate-200">No Deployment Safety Issues Detected</div>
              <p className="text-xs text-slate-500 mt-1">
                All field teams satisfy medical readiness, leader designation, and polar 2-person buddy invariants.
              </p>
            </div>
          ) : (
            filteredFindings.map((finding) => {
              const isBlocked = finding.status === 'BLOCKED';
              const border = isBlocked ? 'border-rose-800/60 bg-rose-950/15' : 'border-amber-800/60 bg-amber-950/15';

              return (
                <div
                  key={finding.finding_id}
                  data-testid={`finding-card-${finding.rule_id}`}
                  className={`border rounded-lg p-3.5 ${border} space-y-2.5 transition`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                          isBlocked
                            ? 'bg-rose-900/60 text-rose-300 border-rose-700'
                            : 'bg-amber-900/60 text-amber-300 border-amber-700'
                        }`}
                      >
                        {finding.status}
                      </span>
                      <span className="font-mono text-xs text-slate-300">{finding.rule_id}</span>
                      <span className="text-slate-600">•</span>
                      <EntityCode code={finding.subject_code} />
                      <span className="text-xs font-medium text-slate-200">{finding.subject_name}</span>
                    </div>

                    {onInitiateReplan && (
                      <button
                        onClick={() =>
                          onInitiateReplan({
                            personId: finding.subject_type === 'PERSON' ? finding.subject_id : undefined,
                            personCode: finding.subject_type === 'PERSON' ? finding.subject_code : undefined,
                            teamId: finding.team_id ?? undefined,
                            teamCode: finding.team_code ?? undefined,
                            missionId: finding.mission_id ?? undefined,
                            missionCode: finding.mission_code ?? undefined,
                            reason: `Safety finding: ${finding.reason}`,
                          })
                        }
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-sky-600 hover:bg-sky-500 text-white transition shadow-sm"
                      >
                        <span>Review Reassignment</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{finding.reason}</p>

                  {/* Evidence & Action */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400 bg-slate-950/40 p-2 rounded border border-slate-800/60">
                    {finding.mission_code && (
                      <div>
                        <span className="text-slate-500">Mission:</span>{' '}
                        <span className="text-slate-200 font-mono">{finding.mission_code}</span>
                      </div>
                    )}
                    {finding.team_code && (
                      <div>
                        <span className="text-slate-500">Team:</span>{' '}
                        <span className="text-slate-200 font-mono">{finding.team_code}</span>
                      </div>
                    )}
                    {finding.evidence && Object.entries(finding.evidence).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-slate-500">{k}:</span>{' '}
                        <span className="text-slate-300 font-mono">{String(v)}</span>
                      </div>
                    ))}
                    {finding.recommended_action && (
                      <div className="w-full mt-1 pt-1 border-t border-slate-800/40 text-sky-400">
                        <span className="font-semibold">Recommended:</span> {finding.recommended_action}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ─── Content: Teams View ─── */}
      {activeTab === 'TEAMS' && (
        <div className="space-y-3">
          {teams.length === 0 ? (
            <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg">
              <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <div className="text-sm font-medium text-slate-300">No Field Teams Found</div>
              <p className="text-xs text-slate-500 mt-1">No field teams are currently assigned to this expedition.</p>
            </div>
          ) : (
            teams.map((team) => {
              const teamBlocked = team.deployment_status === 'BLOCKED';
              const teamWarn = team.deployment_status === 'WARNING';
              const badgeClass = teamBlocked
                ? 'bg-rose-950/80 text-rose-300 border-rose-600/80'
                : teamWarn
                ? 'bg-amber-950/80 text-amber-300 border-amber-600/80'
                : 'bg-emerald-950/80 text-emerald-300 border-emerald-600/80';

              return (
                <div
                  key={team.team_id}
                  className="bg-slate-950/60 border border-slate-800 rounded-lg p-3.5 space-y-2.5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <EntityCode code={team.team_code} />
                      <span className="font-medium text-slate-100 text-sm">{team.team_name}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                        {team.status}
                      </span>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeClass}`}>
                      {team.deployment_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-slate-400">
                    <div>
                      <span className="text-slate-500">Leader:</span>{' '}
                      <span className="text-slate-200">
                        {team.leader_name || 'Unassigned'} ({team.leader_readiness || 'N/A'})
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Mission:</span>{' '}
                      <span className="text-slate-200 font-mono">{team.mission_code || 'None'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Headcount:</span>{' '}
                      <span className={`font-semibold ${team.headcount < 2 ? 'text-rose-400' : 'text-slate-200'}`}>
                        {team.headcount} {team.headcount < 2 ? '(Buddy Deficit)' : 'members'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Base Location:</span>{' '}
                      <span className="text-slate-200">{team.location_name || 'Expedition Staging'}</span>
                    </div>
                  </div>

                  {/* Team Members List */}
                  {team.members.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80">
                      <div className="text-[11px] text-slate-500 mb-1.5">Assigned Roster:</div>
                      <div className="flex flex-wrap gap-1.5">
                        {team.members.map((m) => {
                          const isMedHold = m.readiness_state !== 'READY';
                          return (
                            <span
                              key={m.person_id}
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] border ${
                                isMedHold
                                  ? 'bg-rose-950/60 text-rose-300 border-rose-700/60'
                                  : 'bg-slate-900 text-slate-300 border-slate-700/60'
                              }`}
                            >
                              <span className="font-mono">{m.person_code}</span>
                              <span>{m.full_name}</span>
                              {m.is_leader && <span className="text-[9px] text-amber-400 font-bold">[LDR]</span>}
                              {isMedHold && <span className="text-[9px] text-rose-400 font-bold">({m.readiness_state})</span>}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Unmet requirements */}
                  {team.unmet_requirements.length > 0 && (
                    <div className="pt-2 text-xs text-rose-400 flex items-start gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                      <span>{team.unmet_requirements.join(' • ')}</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ─── Content: Reassignment Candidates View ─── */}
      {activeTab === 'OPPORTUNITIES' && (
        <div className="space-y-3">
          <div className="text-xs text-slate-400">
            Authoritative replacement candidates identified from station complement with valid readiness clearance:
          </div>
          {opportunities.length === 0 ? (
            <div className="p-6 text-center border border-dashed border-slate-800 rounded-lg">
              <UserCheck className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <div className="text-sm font-medium text-slate-300">No Reassignment Opportunities</div>
              <p className="text-xs text-slate-500 mt-1">No candidate substitutions are currently required or available.</p>
            </div>
          ) : (
            opportunities.map((opp, idx) => (
              <div
                key={idx}
                className="bg-purple-950/20 border border-purple-800/50 rounded-lg p-3.5 space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ArrowRightLeft className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-semibold text-slate-200">
                      Substitute in Team <EntityCode code={opp.team_code} />
                    </span>
                    <ProvenanceTag provenance="ADVISORY" />
                  </div>
                  {onInitiateReplan && (
                    <button
                      onClick={() =>
                        onInitiateReplan({
                          personId: opp.displaced_person_id,
                          personCode: opp.displaced_person_code,
                          teamId: opp.team_id,
                          teamCode: opp.team_code,
                          missionId: opp.mission_id ?? undefined,
                          missionCode: opp.mission_code ?? undefined,
                          reason: opp.rationale,
                        })
                      }
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-purple-600 hover:bg-purple-500 text-white transition shadow-sm"
                    >
                      <span>Propose Reassignment</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-rose-950/30 border border-rose-800/40">
                    <div className="text-[10px] text-rose-400 font-bold uppercase">Displaced Member</div>
                    <div className="text-slate-100 font-medium mt-0.5">{opp.displaced_person_code}</div>
                    <div className="text-[11px] text-slate-400">{opp.displaced_role}</div>
                  </div>
                  <div className="p-2 rounded bg-emerald-950/30 border border-emerald-800/40">
                    <div className="text-[10px] text-emerald-400 font-bold uppercase">Available Specialist</div>
                    <div className="text-slate-100 font-medium mt-0.5">
                      {opp.candidate_person_code} — {opp.candidate_full_name}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {opp.candidate_role} ({opp.candidate_readiness})
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-300 italic">{opp.rationale}</p>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
};
