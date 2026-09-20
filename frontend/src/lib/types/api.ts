/**
 * Shared TypeScript types mirroring the CRYOS backend Pydantic schemas.
 * Source of truth: backend/app/shared/types/states.py and domain schemas.
 * DO NOT invent fields not present in the backend response.
 */

// ─── API Envelope ────────────────────────────────────────────────────────────

export interface ApiErrorItem {
  code: string;
  message: string;
  field?: string | null;
  details?: Record<string, unknown> | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface ApiMeta {
  timestamp: string;
  correlation_id?: string | null;
  version: string;
  pagination?: PaginationMeta | null;
}

export interface ApiResponse<T> {
  data: T | null;
  meta: ApiMeta;
  errors: ApiErrorItem[] | null;
}

// ─── Location Domain ──────────────────────────────────────────────────────────

export type LocationStatus = 'AVAILABLE' | 'RESTRICTED' | 'INACCESSIBLE' | 'CLOSED';

export interface Location {
  id: string;
  code: string;
  name: string;
  type: string;
  status: LocationStatus;
  parent_location_id: string | null;
  latitude: string | null;    // Decimal serialized as string
  longitude: string | null;
  description: string | null;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface LocationHierarchy {
  location: Location;
  ancestors: Location[];
  children: Location[];
}

export interface LocationStatusUpdate {
  status: LocationStatus;
  reason?: string;
}

// Valid location state transitions from backend service
// (mirrored from backend/app/domains/locations/service.py)
export const LOCATION_TRANSITIONS: Record<LocationStatus, LocationStatus[]> = {
  AVAILABLE:    ['RESTRICTED', 'INACCESSIBLE', 'CLOSED'],
  RESTRICTED:   ['AVAILABLE', 'INACCESSIBLE', 'CLOSED'],
  INACCESSIBLE: ['RESTRICTED', 'AVAILABLE'],
  CLOSED:       [],
};

// ─── Cargo Domain ─────────────────────────────────────────────────────────────

export type CargoStatus =
  | 'REQUESTED' | 'DECLARED' | 'APPROVED' | 'PACKED' | 'READY'
  | 'DISPATCHED' | 'IN_TRANSIT' | 'ARRIVED' | 'RECEIVED'
  | 'HELD' | 'DELAYED' | 'DAMAGED' | 'LOST' | 'REJECTED';

export type CargoRiskLevel = 'NOMINAL' | 'MODERATE' | 'ELEVATED' | 'CRITICAL';

export type CargoPackageStatus =
  | 'PACKED' | 'LOADED' | 'IN_TRANSIT' | 'RECEIVED'
  | 'ISSUED' | 'RETURNED' | 'HELD' | 'DAMAGED' | 'LOST';

export interface CargoPackage {
  id: string;
  code: string;
  consignment_id: string;
  status: CargoPackageStatus;
  contents_summary: string | null;
  quantity: string;
  weight_kg: string | null;
  length_cm: string | null;
  width_cm: string | null;
  height_cm: string | null;
  handling_classification: string | null;
  current_location_id: string | null;
  current_transport_leg_id: string | null;
  condition: string;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface CargoConsignment {
  id: string;
  code: string;
  expedition_id: string;
  status: CargoStatus;
  risk_level: CargoRiskLevel;
  priority: number;
  origin_location_id: string;
  destination_location_id: string;
  required_by_at: string;
  planned_arrival_at: string | null;
  estimated_arrival_at: string | null;
  transport_plan_summary: string | null;
  compliance_status: string;
  handling_classification: string | null;
  exception_reason: string | null;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface CargoConsignmentDetail extends CargoConsignment {
  packages: CargoPackage[];
}

export interface CargoTimeline {
  consignment_id: string;
  code: string;
  required_by_at: string;
  planned_arrival_at: string | null;
  estimated_arrival_at: string | null;
  buffer_hours: number | null;
  status: CargoStatus;
  risk_level: CargoRiskLevel;
  is_delayed: boolean;
  exception_reason: string | null;
}

// ─── Transport Domain ─────────────────────────────────────────────────────────

export type TransportStatus =
  | 'PLANNED' | 'BOOKED' | 'READY' | 'DEPARTED' | 'IN_TRANSIT'
  | 'ARRIVED' | 'CLOSED' | 'DELAYED' | 'DIVERTED' | 'CANCELLED';

export type AssignmentStatus = 'PROPOSED' | 'APPROVED' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED';

export interface TransportLeg {
  id: string;
  code: string;
  expedition_id: string;
  mode: string;
  status: TransportStatus;
  origin_location_id: string;
  destination_location_id: string;
  departure_window_open: string | null;
  departure_window_close: string | null;
  arrival_window_open: string | null;
  arrival_window_close: string | null;
  planned_departure_at: string | null;
  planned_arrival_at: string | null;
  estimated_departure_at: string | null;
  estimated_arrival_at: string | null;
  actual_departure_at: string | null;
  actual_arrival_at: string | null;
  capacity: string | null;
  capacity_unit: string | null;
  delay_reason: string | null;
  operational_metadata: Record<string, unknown>;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface TransportCargoAssignment {
  id: string;
  transport_leg_id: string;
  cargo_consignment_id: string;
  assigned_at: string;
  released_at: string | null;
  status: AssignmentStatus;
  created_at: string;
}

export interface TransportDelayImpact {
  transport_leg: TransportLeg;
  affected_cargo_consignments: CargoConsignment[];
  summary: string;
}

export interface DelayRequest {
  new_estimated_arrival_at: string;
  delay_reason: string;
  operational_metadata?: Record<string, unknown>;
}

export interface AssignCargoRequest {
  cargo_consignment_id: string;
  status?: AssignmentStatus;
}

// ─── Inventory Domain ─────────────────────────────────────────────────────────

export type InventoryStatus =
  | 'ON_ORDER'
  | 'INBOUND'
  | 'AVAILABLE'
  | 'RESERVED'
  | 'ISSUED'
  | 'CONSUMED'
  | 'TRANSFERRED'
  | 'QUARANTINED'
  | 'DISPOSED';

export type InventoryTransactionType =
  | 'RECEIPT'
  | 'RESERVATION'
  | 'RELEASE'
  | 'ISSUE'
  | 'TRANSFER_OUT'
  | 'TRANSFER_IN'
  | 'DAMAGE'
  | 'QUARANTINE'
  | 'DISPOSE'
  | 'RETURN';

export type ItemCriticality = 'STANDARD' | 'MISSION_CRITICAL' | 'LIFE_SUPPORT' | 'SAFETY';

export interface InventoryItem {
  id: string;
  code: string;
  name: string;
  category: string;
  description: string | null;
  criticality: ItemCriticality;
  unit_of_measure: string;
  minimum_temperature_c: string | null;
  maximum_temperature_c: string | null;
  hazmat_class: string | null;
  is_shelf_life_controlled: boolean;
  default_shelf_life_days: number | null;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface InventoryStockLot {
  id: string;
  lot_number: string;
  inventory_item_id: string;
  location_id: string;
  status: InventoryStatus;
  on_hand_quantity: string;
  reserved_quantity: string;
  quarantined_quantity: string;
  damaged_quantity: string;
  available_quantity: string;
  reorder_point: string | null;
  is_deficit: boolean;
  received_at: string;
  expiry_date: string | null;
  notes: string | null;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface StockAvailability {
  stock_lot_id: string;
  on_hand_quantity: string;
  reserved_quantity: string;
  quarantined_quantity: string;
  damaged_quantity: string;
  available_quantity: string;
  reorder_point: string | null;
  is_deficit: boolean;
  status: InventoryStatus;
}

export interface InventoryTransaction {
  id: string;
  stock_lot_id: string;
  transaction_type: InventoryTransactionType;
  quantity: string;
  balance_after: string;
  reference_id: string | null;
  notes: string | null;
  data_provenance: string;
  created_at: string;
}

export interface StockReceiptRequest {
  quantity: number;
  unit_cost?: number;
  supplier?: string;
  receipt_reference?: string;
  notes?: string;
}

export interface StockReservationRequest {
  quantity: number;
  reservation_reference?: string;
  notes?: string;
}

export interface StockReleaseRequest {
  quantity: number;
  release_reference?: string;
  notes?: string;
}

export interface StockIssueRequest {
  quantity: number;
  issued_to: string;
  issue_reference?: string;
  destination_location_id?: string;
  notes?: string;
}

export interface StockQuarantineRequest {
  quantity: number;
  quarantine_reason: string;
  notes?: string;
}

export interface StockStatusTransitionRequest {
  status: InventoryStatus;
  reason?: string;
}

export const INVENTORY_TRANSITIONS: Record<InventoryStatus, InventoryStatus[]> = {
  ON_ORDER: ['INBOUND', 'QUARANTINED', 'DISPOSED'],
  INBOUND: ['AVAILABLE', 'QUARANTINED', 'DISPOSED'],
  AVAILABLE: ['RESERVED', 'ISSUED', 'CONSUMED', 'TRANSFERRED', 'QUARANTINED', 'DISPOSED'],
  RESERVED: ['AVAILABLE', 'ISSUED', 'CONSUMED', 'TRANSFERRED', 'QUARANTINED'],
  ISSUED: ['CONSUMED', 'AVAILABLE', 'QUARANTINED', 'DISPOSED'],
  TRANSFERRED: ['INBOUND', 'AVAILABLE', 'DISPOSED'],
  QUARANTINED: ['AVAILABLE', 'DISPOSED'],
  CONSUMED: [],
  DISPOSED: [],
};

// ─── Assets & Maintenance Domain ──────────────────────────────────────────────

export type AssetStatus =
  | 'AVAILABLE'
  | 'RESERVED'
  | 'IN_USE'
  | 'MAINTENANCE'
  | 'QUARANTINED'
  | 'RETIRED';

export type MaintenanceStatus =
  | 'SCHEDULED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'OVERDUE';

export type AssetCriticality = 'STANDARD' | 'MISSION_CRITICAL' | 'LIFE_SUPPORT' | 'SAFETY';

export type AssetCondition = 'OPERATIONAL' | 'DEGRADED' | 'DAMAGED' | 'INOPERABLE';

export interface Asset {
  id: string;
  code: string;
  serial_number: string | null;
  type: string;
  status: AssetStatus;
  criticality: AssetCriticality;
  condition: AssetCondition;
  location_id: string;
  description: string | null;
  commissioned_at: string | null;
  retired_at: string | null;
  operational_metadata: Record<string, unknown>;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface AssetMoveRequest {
  destination_location_id: string;
  move_reason?: string;
}

export interface AssetStatusTransitionRequest {
  status: AssetStatus;
  reason?: string;
}

export interface MaintenanceRecord {
  id: string;
  asset_id: string;
  maintenance_type: string;
  status: MaintenanceStatus;
  priority: number;
  description: string;
  scheduled_start_at: string;
  estimated_duration_hours: number;
  technician_name: string | null;
  actual_start_at: string | null;
  actual_completed_at: string | null;
  findings: string | null;
  corrective_action: string | null;
  operational_metadata: Record<string, unknown>;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface MaintenanceScheduleRequest {
  maintenance_type: string;
  priority: number;
  description: string;
  scheduled_start_at: string;
  estimated_duration_hours: number;
  technician_name?: string;
}

export interface MaintenanceStartRequest {
  actual_start_at?: string;
  notes?: string;
}

export interface MaintenanceCompleteRequest {
  actual_completed_at?: string;
  findings: string;
  corrective_action: string;
  target_asset_status?: AssetStatus;
}

export interface MaintenanceCancelRequest {
  cancel_reason: string;
}

export interface AssetTimelineEntry {
  id: string;
  timestamp: string;
  event_type: string;
  description: string;
  actor?: string | null;
  data_provenance: string;
  details?: Record<string, unknown>;
}

export interface AssetTimeline {
  asset_id: string;
  code: string;
  status: AssetStatus;
  condition: AssetCondition;
  location_id: string;
  history: AssetTimelineEntry[];
}

export const ASSET_TRANSITIONS: Record<AssetStatus, AssetStatus[]> = {
  AVAILABLE: ['RESERVED', 'IN_USE', 'MAINTENANCE', 'QUARANTINED', 'RETIRED'],
  RESERVED: ['AVAILABLE', 'IN_USE', 'QUARANTINED', 'RETIRED'],
  IN_USE: ['AVAILABLE', 'MAINTENANCE', 'QUARANTINED', 'RETIRED'],
  MAINTENANCE: ['AVAILABLE', 'QUARANTINED', 'RETIRED'],
  QUARANTINED: ['AVAILABLE', 'MAINTENANCE', 'RETIRED'],
  RETIRED: [],
};

export const MAINTENANCE_TRANSITIONS: Record<MaintenanceStatus, MaintenanceStatus[]> = {
  SCHEDULED: ['IN_PROGRESS', 'CANCELLED', 'OVERDUE'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  OVERDUE: ['IN_PROGRESS', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
};

// ─── Incident Response Domain ─────────────────────────────────────────────────

export type IncidentStatus = 'OPEN' | 'ACKNOWLEDGED' | 'MITIGATING' | 'RESOLVED' | 'CLOSED';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type IncidentReferenceType =
  | 'LOCATION'
  | 'ASSET'
  | 'INVENTORY_STOCK_LOT'
  | 'CARGO_CONSIGNMENT'
  | 'TRANSPORT_LEG';

export interface Incident {
  id: string;
  code: string;
  title: string;
  description: string;
  incident_type: string;
  severity: IncidentSeverity;
  priority: number;
  status: IncidentStatus;
  location_id: string | null;
  asset_id: string | null;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  operational_metadata: Record<string, unknown>;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export interface IncidentCreateRequest {
  code: string;
  title: string;
  description: string;
  incident_type: string;
  severity: IncidentSeverity;
  priority: number;
  location_id?: string | null;
  asset_id?: string | null;
}

export interface IncidentUpdateRequest {
  title?: string;
  description?: string;
  severity?: IncidentSeverity;
  priority?: number;
  location_id?: string | null;
  asset_id?: string | null;
}

export interface IncidentStatusTransitionRequest {
  status: IncidentStatus;
  reason?: string;
  operational_metadata?: Record<string, unknown>;
}

export interface IncidentReference {
  id: string;
  incident_id: string;
  reference_type: IncidentReferenceType;
  reference_id: string;
  notes: string | null;
  created_at: string;
}

export interface IncidentReferenceCreateRequest {
  reference_type: IncidentReferenceType;
  reference_id: string;
  notes?: string;
}

export interface IncidentTimelineEntry {
  id: string;
  timestamp: string;
  event_type: string;
  summary: string;
  actor?: string | null;
  provenance: string;
  details?: Record<string, unknown>;
}

export interface IncidentTimeline {
  incident_id: string;
  code: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  priority: number;
  history: IncidentTimelineEntry[];
}

export const INCIDENT_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  OPEN: ['ACKNOWLEDGED', 'RESOLVED', 'CLOSED'],
  ACKNOWLEDGED: ['MITIGATING', 'RESOLVED', 'CLOSED'],
  MITIGATING: ['RESOLVED'],
  RESOLVED: ['CLOSED'],
  CLOSED: [],
};

// ─── Operational Timeline Domain (B9) ────────────────────────────────────────

export type TimelineEntryType =
  | 'OPERATIONAL_EVENT'
  | 'AUDIT_RECORD'
  | 'PROPAGATION_RECORD'
  | 'OFFLINE_SYNC';

export interface TimelineEntry {
  id: string;
  entry_type: TimelineEntryType;
  timestamp: string;
  event_or_action: string;
  audit_action?: string | null;
  entity_type: string;
  entity_id: string;
  entity_name?: string | null;
  source: string;
  previous_state?: string | null;
  new_state?: string | null;
  status?: string | null;
  actor_type?: string | null;
  actor_id?: string | null;
  correlation_id?: string | null;
  data_provenance: string;
  description?: string | null;
  details: Record<string, unknown>;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  audit_id?: string | null;
  event_id?: string | null;
}

export interface TimelineResponse {
  entity_type: string;
  entity_id: string;
  entity_name?: string | null;
  total_entries: number;
  page: number;
  page_size: number;
  total_pages: number;
  entries: TimelineEntry[];
  related_entities_included: boolean;
}

// ─── Operational Control Tower Domain (A4) ──────────────────────────────────

export type ReadinessState = 'READY' | 'AT_RISK' | 'BLOCKED' | 'UNKNOWN';

export type ConstraintState = 'SATISFIED' | 'VIOLATED' | 'NOT_EVALUABLE';

export interface OperationalEventFeedItem {
  event_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  previous_state?: string | null;
  new_state?: string | null;
  occurred_at: string;
  source: string;
  actor_type?: string | null;
  actor_id?: string | null;
  location_id?: string | null;
  correlation_id?: string | null;
  evidence: Record<string, unknown>;
  data_provenance: string;
}

export interface ControlTowerConstraintItem {
  constraint_id: string;
  code: string;
  name: string;
  type: string;
  rule_code: string;
  subject_type: string;
  subject_id: string;
  subject_code?: string | null;
  hard_or_soft: 'HARD' | 'SOFT' | string;
  severity: string;
  state: ConstraintState;
  reason: string;
  evidence: Record<string, unknown>;
  data_provenance: string;
}

export interface MissionOperationsItem {
  mission_id: string;
  code: string;
  title: string;
  status: string;
  priority: number;
  type: string;
  required_by_at?: string | null;
  location_id?: string | null;
  readiness_state: ReadinessState;
  readiness_blockers: Record<string, unknown>[];
  warnings: Record<string, unknown>[];
  unknown_requirements: Record<string, unknown>[];
  violated_constraints: Record<string, unknown>[];
  pending_replans: Record<string, unknown>[];
  latest_event?: OperationalEventFeedItem | null;
  data_provenance: string;
}

export interface ExpeditionControlSummary {
  expedition_id: string;
  code: string;
  name: string;
  season: string;
  lifecycle_status: string;
  readiness_state: ReadinessState;
  total_missions: number;
  ready_missions_count: number;
  at_risk_missions_count: number;
  blocked_missions_count: number;
  active_incidents_count: number;
  active_hard_constraint_violations_count: number;
  pending_replans_count: number;
  pending_approvals_count: number;
  latest_events: OperationalEventFeedItem[];
  blockers: Record<string, unknown>[];
  warnings: Record<string, unknown>[];
  unknown_requirements: Record<string, unknown>[];
  data_provenance: string;
  generated_at: string;
}

export interface ControlTowerOverview {
  total_expeditions: number;
  expeditions: ExpeditionControlSummary[];
  total_missions: number;
  missions_by_readiness: Record<string, number>;
  missions_by_status: Record<string, number>;
  active_incidents_count: number;
  critical_constraints_violated_count: number;
  pending_replans_count: number;
  pending_recommendations_count: number;
  pending_approvals_count: number;
  offline_sync_summary: Record<string, unknown>;
  resource_runway_summary?: ResourceRunwaySummary | null;
  recent_operational_events: OperationalEventFeedItem[];
  data_provenance: string;
  generated_at: string;
}

export interface DecisionReplanItem {
  replan_id: string;
  replan_code: string;
  expedition_id: string;
  mission_id?: string | null;
  status: string;
  trigger_mode: string;
  trigger_reason?: string | null;
  what_changed: string;
  affected_entities_count: number;
  violated_constraints_count: number;
  created_at: string;
}

export interface DecisionRecommendationItem {
  recommendation_id: string;
  replan_id: string;
  option_id?: string | null;
  title: string;
  summary?: string | null;
  status: string;
  approval_state: string;
  what_is_affected: Record<string, unknown>[];
  rationale: string[];
  proposed_changes: Record<string, unknown>[];
  created_at: string;
}

export interface DecisionApprovalItem {
  approval_id: string;
  recommendation_id: string;
  replan_id?: string | null;
  recommendation_title: string;
  status: string;
  required_approver_role: string;
  what_changed: string;
  why_it_matters: string;
  what_constraint_is_involved: string;
  available_options_count: number;
  created_at: string;
}

export interface DecisionQueueSummary {
  expedition_id?: string | null;
  total_pending_replans: number;
  total_pending_recommendations: number;
  total_pending_approvals: number;
  pending_replans: DecisionReplanItem[];
  pending_recommendations: DecisionRecommendationItem[];
  pending_approvals: DecisionApprovalItem[];
  data_provenance: string;
  generated_at: string;
}

export interface ConsequentialActionItem {
  approval_id: string;
  recommendation_id: string;
  replan_id?: string | null;
  decision?: string | null;
  approver_person_id: string;
  approver_role?: string | null;
  comment?: string | null;
  decided_at?: string | null;
  action_summary: string;
  applied_changes: Record<string, unknown>[];
  resulting_event_id?: string | null;
  correlation_id?: string | null;
  created_at: string;
  data_provenance: string;
}

// ─── Replanning & Human Governance Domain (A3) ──────────────────────────────

export type RecommendationStatus =
  | 'PROPOSED'
  | 'SELECTED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'APPLIED'
  | 'FAILED';

export interface RecommendationRead {
  id: string;
  replan_id: string;
  option_id?: string | null;
  trigger_event_id?: string | null;
  title: string;
  summary?: string | null;
  rationale: string[];
  supporting_evidence: Record<string, unknown>;
  constraint_evaluation_summary: Record<string, unknown>;
  affected_entities: unknown[];
  violated_constraints: unknown[];
  proposed_changes: unknown[];
  expected_impact: Record<string, unknown>;
  assumptions: string[];
  status: RecommendationStatus | string;
  approval_state: ApprovalState | string;
  data_provenance: string;
  generated_at: string;
  created_at: string;
}

export type ApprovalState = 'PENDING' | 'APPROVED' | 'REJECTED' | 'REVOKED';

export type ApprovalStatus = ApprovalState;

export type ApprovalDecision = 'APPROVED' | 'REJECTED';

export interface ApprovalDecisionRequest {
  approver_person_id: string;
  approver_role?: string | null;
  decision: ApprovalDecision;
  comment?: string | null;
  correlation_id?: string | null;
}

export interface ApprovalRead {
  id: string;
  recommendation_id: string;
  approver_user_id?: string | null;
  approver_person_id: string;
  approver_role?: string | null;
  decision?: string | null;
  comment?: string | null;
  status: string;
  decided_at?: string | null;
  resulting_event_id?: string | null;
  correlation_id?: string | null;
  created_at: string;
}

export interface ReplanApplyRequest {
  actor_person_id: string;
  comment?: string | null;
  correlation_id?: string | null;
}

export interface ReplanApplyResult {
  recommendation_id: string;
  status: string;
  applied_changes: Record<string, unknown>[];
  resulting_event_id?: string | null;
  applied_at: string;
  message: string;
}

export interface ReplanTriggerRequest {
  trigger_mode: 'EVENT_DRIVEN' | 'OPERATOR_REQUESTED';
  expedition_id: string;
  mission_id?: string | null;
  trigger_event_id?: string | null;
  trigger_entity_type?: string | null;
  trigger_entity_id?: string | null;
  reason?: string | null;
  current_state_evidence?: Record<string, unknown>;
  violated_constraints?: unknown[];
  affected_entities?: unknown[];
  requested_by?: string | null;
  correlation_id?: string | null;
}

export interface ReplanRead {
  id: string;
  replan_code: string;
  expedition_id: string;
  mission_id?: string | null;
  trigger_event_id?: string | null;
  trigger_entity_type?: string | null;
  trigger_entity_id?: string | null;
  trigger_reason?: string | null;
  status: string;
  current_state_evidence: Record<string, unknown>;
  violated_constraints: unknown[];
  affected_entities: unknown[];
  requested_by?: string | null;
  correlation_id?: string | null;
  generated_at: string;
  completed_at?: string | null;
  data_provenance: string;
  created_at: string;
  updated_at: string;
}

export type OptionFeasibility = 'FEASIBLE' | 'CONSTRAINED' | 'NOT_EVALUABLE' | 'INFEASIBLE';

export interface ReplanOptionRead {
  id: string;
  replan_id?: string | null;
  recommendation_id?: string | null;
  option_code: string;
  title: string;
  description: string;
  action_type: string;
  feasibility: OptionFeasibility;
  estimated_delay_hours: number;
  estimated_cost_delta: number;
  risk_score: number;
  affected_entities: unknown[];
  violated_constraints: unknown[];
  proposed_changes: unknown[];
  assumptions: string[];
  operational_tradeoffs: Record<string, unknown>;
  data_provenance: string;
  created_at: string;
}

export interface ReplanGenerationResult {
  replan_id: string;
  options: ReplanOptionRead[];
  recommendations: RecommendationRead[];
}

// ─── Control Tower Disruption Scenarios (A6) ────────────────────────────────

export type BenchmarkScenarioKey =
  | 'FLIGHT_GROUNDING'
  | 'GENERATOR_FAILURE'
  | 'COLD_CHAIN_EXCURSION';

export interface ScenarioInjectRequest {
  scenario_key: BenchmarkScenarioKey;
  expedition_id: string;
  requested_by?: string | null;
}

export interface ScenarioInjectResult {
  scenario_key: string;
  summary: string;
  trigger_event_id?: string | null;
  affected_entity_type: string;
  affected_entity_id: string;
  affected_entity_code: string;
  data_provenance: string;
  timestamp: string;
}

// ─── Control Tower Incident Escalation (A7) ────────────────────────────────

export interface IncidentEscalationRequest {
  requested_by?: string | null;
  reason?: string | null;
}

export interface IncidentEscalationResult {
  incident_id: string;
  replan_id: string;
  expedition_id: string;
  correlation_id?: string | null;
  affected_entities: Record<string, unknown>[];
  violated_constraints: Record<string, unknown>[];
  is_existing: boolean;
  data_provenance: string;
  message: string;
}

export interface IncidentContextView {
  incident_id: string;
  incident_code: string;
  title: string;
  severity: string;
  status: string;
  location_id?: string | null;
  location_name?: string | null;
  propagation_summary: string;
  affected_entities: Record<string, unknown>[];
  affected_missions: Record<string, unknown>[];
  affected_constraints: Record<string, unknown>[];
  correlation_id?: string | null;
  data_provenance: string;
}

// ─── Polar Utility & Consumables Runway Engine (A9) ─────────────────────────

export type RunwayState =
  | 'RESUPPLY_GAP'
  | 'AT_RISK'
  | 'COVERED'
  | 'NO_INBOUND_SCHEDULED'
  | 'NO_CONSUMPTION_OBSERVED';

export interface BurnRateEvidence {
  observations: number;
  consumed_quantity: number;
  elapsed_days: number;
  window_days: number;
  baseline_daily_burn_rate?: number | null;
}

export interface ResourceRunwayItem {
  stock_lot_id: string;
  inventory_item_id: string;
  lot_code?: string | null;
  item_code: string;
  item_name: string;
  category: string;
  criticality: string;
  unit: string;
  location_id: string;
  location_name?: string | null;

  // Authoritative balances
  on_hand_quantity: string;
  reserved_quantity: string;
  quarantined_quantity: string;
  damaged_quantity: string;
  available_quantity: string;

  // Existing repository thresholds
  reorder_point?: string | null;
  replenishment_lead_days?: number | null;
  reorder_buffer_days?: number | null;

  // Burn rate & evidence
  daily_burn_rate: string;
  burn_rate_source: string;
  burn_rate_evidence: Record<string, unknown>;

  // Forecast projections
  runway_days?: number | null;
  exhaustion_at?: string | null;
  next_inbound_at?: string | null;
  resupply_gap_days: number;

  // Deterministic runway state
  runway_state: RunwayState;

  // Contextual linkages
  dependent_mission_id?: string | null;
  dependent_asset_id?: string | null;
  active_constraint_id?: string | null;

  // Provenance
  data_provenance: string;
}

export interface ResourceRunwaySummary {
  expedition_id: string;
  evaluated_at: string;
  total_candidates: number;
  items_with_resupply_gap: number;
  items_at_risk: number;
  minimum_runway_days?: number | null;
  runways: ResourceRunwayItem[];
  data_provenance: string;
}

// ─── Milestone A10: Personnel & Field Team Deployment Safety Engine ──────────

export type PersonnelSafetyStatus = 'CLEAR' | 'WARNING' | 'BLOCKED';

export interface PersonnelSafetyFinding {
  finding_id: string;
  rule_id: string;
  status: PersonnelSafetyStatus;
  subject_type: 'PERSON' | 'TEAM';
  subject_id: string;
  subject_code: string;
  subject_name: string;
  mission_id?: string | null;
  mission_code?: string | null;
  team_id?: string | null;
  team_code?: string | null;
  reason: string;
  evidence: Record<string, unknown>;
  recommended_action?: string | null;
  data_provenance: string;
}

export interface TeamMemberBrief {
  person_id: string;
  person_code: string;
  full_name: string;
  role: string;
  readiness_state: string;
  movement_state: string;
  is_leader: boolean;
}

export interface TeamDeploymentPosture {
  team_id: string;
  team_code: string;
  team_name: string;
  status: string;
  leader_person_id?: string | null;
  leader_name?: string | null;
  leader_readiness?: string | null;
  mission_id?: string | null;
  mission_code?: string | null;
  location_id?: string | null;
  location_name?: string | null;
  headcount: number;
  members: TeamMemberBrief[];
  deployment_status: PersonnelSafetyStatus;
  unmet_requirements: string[];
  data_provenance: string;
}

export interface ReassignmentOpportunity {
  team_id: string;
  team_code: string;
  mission_id?: string | null;
  mission_code?: string | null;
  displaced_person_id: string;
  displaced_person_code: string;
  displaced_role: string;
  candidate_person_id: string;
  candidate_person_code: string;
  candidate_full_name: string;
  candidate_role: string;
  candidate_readiness: string;
  rationale: string;
  data_provenance: string;
}

export interface PersonnelPostureSummary {
  expedition_id: string;
  overall_status: PersonnelSafetyStatus;
  total_personnel: number;
  cleared_count: number;
  medical_hold_count: number;
  unavailable_count: number;
  at_station_count: number;
  field_deployed_count: number;
  in_transit_count: number;
  teams: TeamDeploymentPosture[];
  findings: PersonnelSafetyFinding[];
  reassignment_opportunities: ReassignmentOpportunity[];
  evaluated_at: string;
  data_provenance: string;
}
