import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, buildQuery } from '../../../lib/api/client';
import type {
  ControlTowerOverview,
  ExpeditionControlSummary,
  MissionOperationsItem,
  ControlTowerConstraintItem,
  OperationalEventFeedItem,
  DecisionQueueSummary,
  ConsequentialActionItem,
  ApprovalDecisionRequest,
  ApprovalRead,
  ReplanApplyRequest,
  ReplanApplyResult,
  ReadinessState,
  ConstraintState,
  RecommendationRead,
  ReplanTriggerRequest,
  ReplanRead,
  ReplanOptionRead,
  ReplanGenerationResult,
  ScenarioInjectRequest,
  ScenarioInjectResult,
} from '../../../lib/types/api';

// ─── Filter Contracts ────────────────────────────────────────────────────────

export interface MissionOperationsFilters {
  status?: string;
  readiness?: ReadinessState | string;
  page?: number;
  page_size?: number;
}

export interface ControlTowerConstraintFilters {
  state?: ConstraintState | string;
  hard_or_soft?: 'HARD' | 'SOFT' | string;
  page?: number;
  page_size?: number;
}

export interface OperationalEventFilters {
  entity_type?: string;
  event_type?: string;
  from_time?: string;
  to_time?: string;
  page?: number;
  page_size?: number;
}

// ─── Stable Query Keys ───────────────────────────────────────────────────────

export const controlTowerKeys = {
  all: ['control-tower'] as const,
  overview: (expeditionId?: string) =>
    expeditionId
      ? (['control-tower', 'overview', { expeditionId }] as const)
      : (['control-tower', 'overview'] as const),
  expedition: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId] as const,
  summary: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'summary'] as const,
  missionsRoot: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'missions'] as const,
  missions: (expeditionId: string, filters?: MissionOperationsFilters) =>
    ['control-tower', 'expedition', expeditionId, 'missions', filters ?? {}] as const,
  constraintsRoot: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'constraints'] as const,
  constraints: (expeditionId: string, filters?: ControlTowerConstraintFilters) =>
    ['control-tower', 'expedition', expeditionId, 'constraints', filters ?? {}] as const,
  eventsRoot: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'events'] as const,
  events: (expeditionId: string, filters?: OperationalEventFilters) =>
    ['control-tower', 'expedition', expeditionId, 'events', filters ?? {}] as const,
  decisions: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'decisions'] as const,
  recommendation: (id?: string | null) =>
    ['recommendation', id] as const,
  auditRoot: (expeditionId: string) =>
    ['control-tower', 'expedition', expeditionId, 'audit'] as const,
  audit: (expeditionId: string, page: number = 1) =>
    ['control-tower', 'expedition', expeditionId, 'audit', { page }] as const,
};

// ─── Query Hooks ─────────────────────────────────────────────────────────────

export function useControlTowerOverview(expeditionId?: string) {
  return useQuery({
    queryKey: controlTowerKeys.overview(expeditionId),
    queryFn: async () => {
      const query = buildQuery({ expedition_id: expeditionId });
      return await apiClient.get<ControlTowerOverview>(`/control-tower/overview${query}`);
    },
  });
}

export function useExpeditionSummary(expeditionId: string) {
  return useQuery({
    queryKey: controlTowerKeys.summary(expeditionId),
    queryFn: async () => {
      return await apiClient.get<ExpeditionControlSummary>(
        `/control-tower/expeditions/${expeditionId}`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

export function useMissionOperations(
  expeditionId: string,
  filters: MissionOperationsFilters = {},
) {
  return useQuery({
    queryKey: controlTowerKeys.missions(expeditionId, filters),
    queryFn: async () => {
      const query = buildQuery({
        status: filters.status,
        readiness: filters.readiness,
        page: filters.page,
        page_size: filters.page_size,
      });
      return await apiClient.get<MissionOperationsItem[]>(
        `/control-tower/expeditions/${expeditionId}/missions${query}`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

export function useControlTowerConstraints(
  expeditionId: string,
  filters: ControlTowerConstraintFilters = {},
) {
  return useQuery({
    queryKey: controlTowerKeys.constraints(expeditionId, filters),
    queryFn: async () => {
      const query = buildQuery({
        state: filters.state,
        hard_or_soft: filters.hard_or_soft,
        page: filters.page,
        page_size: filters.page_size,
      });
      return await apiClient.get<ControlTowerConstraintItem[]>(
        `/control-tower/expeditions/${expeditionId}/constraints${query}`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

export function useOperationalEventsFeed(
  expeditionId: string,
  filters: OperationalEventFilters = {},
) {
  return useQuery({
    queryKey: controlTowerKeys.events(expeditionId, filters),
    queryFn: async () => {
      const query = buildQuery({
        entity_type: filters.entity_type,
        event_type: filters.event_type,
        from_time: filters.from_time,
        to_time: filters.to_time,
        page: filters.page,
        page_size: filters.page_size,
      });
      return await apiClient.get<OperationalEventFeedItem[]>(
        `/control-tower/expeditions/${expeditionId}/events${query}`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

export function useDecisionQueue(expeditionId: string) {
  return useQuery({
    queryKey: controlTowerKeys.decisions(expeditionId),
    queryFn: async () => {
      return await apiClient.get<DecisionQueueSummary>(
        `/control-tower/expeditions/${expeditionId}/decisions`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

export function useRecommendation(recommendationId?: string | null) {
  return useQuery({
    queryKey: controlTowerKeys.recommendation(recommendationId),
    queryFn: async () => {
      return await apiClient.get<RecommendationRead>(`/recommendations/${recommendationId}`);
    },
    enabled: Boolean(recommendationId),
  });
}

export function useConsequentialAudit(expeditionId: string, page: number = 1) {
  return useQuery({
    queryKey: controlTowerKeys.audit(expeditionId, page),
    queryFn: async () => {
      const query = buildQuery({ page, page_size: 20 });
      return await apiClient.get<ConsequentialActionItem[]>(
        `/control-tower/expeditions/${expeditionId}/audit${query}`,
      );
    },
    enabled: Boolean(expeditionId),
  });
}

// ─── Mutation Hook ───────────────────────────────────────────────────────────

export interface ApproveMutationVariables {
  recommendationId: string;
  payload: ApprovalDecisionRequest;
  expeditionId?: string;
}

export interface RejectMutationVariables {
  recommendationId: string;
  payload: ApprovalDecisionRequest;
  expeditionId?: string;
}

export interface ApplyMutationVariables {
  recommendationId: string;
  payload: ReplanApplyRequest;
  expeditionId?: string;
}

export function useApprovalMutations(defaultExpeditionId?: string) {
  const queryClient = useQueryClient();

  const approveMutation = useMutation({
    mutationFn: async ({ recommendationId, payload }: ApproveMutationVariables) => {
      return await apiClient.post<ApprovalRead>(
        `/recommendations/${recommendationId}/approve`,
        payload,
      );
    },
    onSuccess: (_data, variables) => {
      const targetExpeditionId = variables.expeditionId ?? defaultExpeditionId;
      queryClient.invalidateQueries({
        queryKey: controlTowerKeys.recommendation(variables.recommendationId),
      });
      if (targetExpeditionId) {
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.decisions(targetExpeditionId),
        });
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.summary(targetExpeditionId),
        });
      } else {
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey[0] === 'control-tower' &&
            query.queryKey[1] === 'expedition' &&
            (query.queryKey[3] === 'decisions' || query.queryKey[3] === 'summary'),
        });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ recommendationId, payload }: RejectMutationVariables) => {
      return await apiClient.post<ApprovalRead>(
        `/recommendations/${recommendationId}/reject`,
        payload,
      );
    },
    onSuccess: (_data, variables) => {
      const targetExpeditionId = variables.expeditionId ?? defaultExpeditionId;
      queryClient.invalidateQueries({
        queryKey: controlTowerKeys.recommendation(variables.recommendationId),
      });
      if (targetExpeditionId) {
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.decisions(targetExpeditionId),
        });
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.summary(targetExpeditionId),
        });
      } else {
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey[0] === 'control-tower' &&
            query.queryKey[1] === 'expedition' &&
            (query.queryKey[3] === 'decisions' || query.queryKey[3] === 'summary'),
        });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });

  const applyMutation = useMutation({
    mutationFn: async ({ recommendationId, payload }: ApplyMutationVariables) => {
      return await apiClient.post<ReplanApplyResult>(
        `/recommendations/${recommendationId}/apply`,
        payload,
      );
    },
    onSuccess: (_data, variables) => {
      const targetExpeditionId = variables.expeditionId ?? defaultExpeditionId;
      queryClient.invalidateQueries({
        queryKey: controlTowerKeys.recommendation(variables.recommendationId),
      });
      if (targetExpeditionId) {
        // Invalidate decision queue
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.decisions(targetExpeditionId),
        });
        // Invalidate expedition summary
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.summary(targetExpeditionId),
        });
        // Invalidate mission operations
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.missionsRoot(targetExpeditionId),
        });
        // Invalidate active constraints
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.constraintsRoot(targetExpeditionId),
        });
        // Invalidate operational events
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.eventsRoot(targetExpeditionId),
        });
        // Invalidate consequential audit timeline
        queryClient.invalidateQueries({
          queryKey: controlTowerKeys.auditRoot(targetExpeditionId),
        });
      } else {
        // Invalidate all expedition queries without global cache wipe
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey[0] === 'control-tower' && query.queryKey[1] === 'expedition',
        });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });

  return {
    approveMutation,
    rejectMutation,
    applyMutation,
  };
}

// ─── A6 Closed-Loop Hooks ───────────────────────────────────────────────────

export function useReplan(replanId?: string | null) {
  return useQuery({
    queryKey: ['replans', replanId] as const,
    queryFn: async () => {
      if (!replanId) return null;
      return await apiClient.get<ReplanRead>(`/replans/${replanId}`);
    },
    enabled: Boolean(replanId),
  });
}

export function useInitiateReplan(defaultExpeditionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReplanTriggerRequest) => {
      return await apiClient.post<ReplanRead>('/replans', payload);
    },
    onSuccess: (_data, variables) => {
      const expId = variables.expedition_id || defaultExpeditionId;
      if (expId) {
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.decisions(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.summary(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.missionsRoot(expId) });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });
}

export function useGenerateOptions(defaultExpeditionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ replanId }: { replanId: string; expeditionId?: string }): Promise<ReplanGenerationResult> => {
      const res = await apiClient.post<any>(`/replans/${replanId}/generate-options`, {});
      let options: ReplanOptionRead[] = [];
      let recommendations: RecommendationRead[] = [];
      if (Array.isArray(res)) {
        options = res;
      } else if (res && Array.isArray((res as any).options)) {
        options = (res as any).options;
        if (Array.isArray((res as any).recommendations)) {
          recommendations = (res as any).recommendations;
        }
      }
      if (recommendations.length === 0) {
        try {
          const recs = await apiClient.get<RecommendationRead[]>(`/replans/${replanId}/recommendations`);
          if (Array.isArray(recs)) {
            recommendations = recs;
          }
        } catch {
          recommendations = [];
        }
      }
      return {
        replan_id: replanId,
        options,
        recommendations,
      };
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['replans', variables.replanId] });
      const expId = variables.expeditionId || defaultExpeditionId;
      if (expId) {
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.decisions(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.summary(expId) });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });
}

export function useInjectScenario(defaultExpeditionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ScenarioInjectRequest) => {
      return await apiClient.post<ScenarioInjectResult>('/control-tower/scenarios/inject', payload);
    },
    onSuccess: (_data, variables) => {
      const expId = variables.expedition_id || defaultExpeditionId;
      if (expId) {
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.expedition(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.summary(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.missionsRoot(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.constraintsRoot(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.eventsRoot(expId) });
        queryClient.invalidateQueries({ queryKey: controlTowerKeys.decisions(expId) });
      }
      queryClient.invalidateQueries({ queryKey: ['control-tower', 'overview'] });
    },
  });
}

