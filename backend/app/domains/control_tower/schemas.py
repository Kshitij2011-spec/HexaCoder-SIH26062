"""Pydantic Schemas for Operational Control Tower Read Models."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 1. Operational Event Feed
# ---------------------------------------------------------------------------

class OperationalEventFeedItem(BaseModel):
    """Read-only operational event feed entry with full context."""
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    occurred_at: datetime
    source: str = "API"
    actor_type: Optional[str] = "SYSTEM"
    actor_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: str = "DERIVED"


# ---------------------------------------------------------------------------
# 2. Control Tower Constraints View
# ---------------------------------------------------------------------------

class ControlTowerConstraintItem(BaseModel):
    """Active constraint evaluation result with subject and evidence."""
    model_config = ConfigDict(from_attributes=True)

    constraint_id: uuid.UUID
    code: str
    name: str
    type: str
    rule_code: str
    subject_type: str
    subject_id: uuid.UUID
    subject_code: Optional[str] = None
    hard_or_soft: str
    severity: str
    state: str  # SATISFIED, VIOLATED, NOT_EVALUABLE
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: str = "DERIVED"


# ---------------------------------------------------------------------------
# 3. Mission Operations View
# ---------------------------------------------------------------------------

class MissionOperationsItem(BaseModel):
    """Rich operational view of a mission including derived readiness and constraints."""
    model_config = ConfigDict(from_attributes=True)

    mission_id: uuid.UUID
    code: str
    title: str
    status: str
    priority: int
    type: str
    required_by_at: Optional[datetime] = None
    location_id: Optional[uuid.UUID] = None
    readiness_state: str  # READY, AT_RISK, BLOCKED, UNKNOWN
    readiness_blockers: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    unknown_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    violated_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    pending_replans: List[Dict[str, Any]] = Field(default_factory=list)
    latest_event: Optional[OperationalEventFeedItem] = None
    data_provenance: str = "DERIVED"


# ---------------------------------------------------------------------------
# 4. Expedition Control Summary
# ---------------------------------------------------------------------------

class ExpeditionControlSummary(BaseModel):
    """Operational summary of a single polar expedition campaign."""
    model_config = ConfigDict(from_attributes=True)

    expedition_id: uuid.UUID
    code: str
    name: str
    season: str
    lifecycle_status: str
    readiness_state: str  # READY, AT_RISK, BLOCKED, UNKNOWN
    total_missions: int = 0
    ready_missions_count: int = 0
    at_risk_missions_count: int = 0
    blocked_missions_count: int = 0
    active_incidents_count: int = 0
    active_hard_constraint_violations_count: int = 0
    pending_replans_count: int = 0
    pending_approvals_count: int = 0
    latest_events: List[OperationalEventFeedItem] = Field(default_factory=list)
    blockers: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    unknown_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    data_provenance: str = "DERIVED"
    generated_at: datetime


# ---------------------------------------------------------------------------
# 5. High-Level Control Tower Overview
# ---------------------------------------------------------------------------

class ControlTowerOverview(BaseModel):
    """Global Control Tower Overview across all active polar campaigns."""
    total_expeditions: int = 0
    expeditions: List[ExpeditionControlSummary] = Field(default_factory=list)
    total_missions: int = 0
    missions_by_readiness: Dict[str, int] = Field(default_factory=dict)
    missions_by_status: Dict[str, int] = Field(default_factory=dict)
    active_incidents_count: int = 0
    critical_constraints_violated_count: int = 0
    pending_replans_count: int = 0
    pending_recommendations_count: int = 0
    pending_approvals_count: int = 0
    offline_sync_summary: Dict[str, Any] = Field(default_factory=dict)
    recent_operational_events: List[OperationalEventFeedItem] = Field(default_factory=list)
    data_provenance: str = "DERIVED"
    generated_at: datetime


# ---------------------------------------------------------------------------
# 6. Decision Queue
# ---------------------------------------------------------------------------

class DecisionReplanItem(BaseModel):
    """Pending replan awaiting options or resolution."""
    replan_id: uuid.UUID
    replan_code: str
    expedition_id: uuid.UUID
    mission_id: Optional[uuid.UUID] = None
    status: str
    trigger_mode: str
    trigger_reason: Optional[str] = None
    what_changed: str
    affected_entities_count: int = 0
    violated_constraints_count: int = 0
    created_at: datetime


class DecisionRecommendationItem(BaseModel):
    """Pending recommendation awaiting operator decision."""
    recommendation_id: uuid.UUID
    replan_id: uuid.UUID
    option_id: Optional[uuid.UUID] = None
    title: str
    summary: Optional[str] = None
    status: str
    approval_state: str
    what_is_affected: List[Dict[str, Any]] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)
    proposed_changes: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class DecisionApprovalItem(BaseModel):
    """Approval item in the operator's inbox."""
    approval_id: uuid.UUID
    recommendation_id: uuid.UUID
    replan_id: Optional[uuid.UUID] = None
    recommendation_title: str
    status: str
    required_approver_role: str
    what_changed: str
    why_it_matters: str
    what_constraint_is_involved: str
    available_options_count: int = 0
    created_at: datetime


class DecisionQueueSummary(BaseModel):
    """Unified operator decision queue: replans, recommendations, approvals."""
    expedition_id: Optional[uuid.UUID] = None
    total_pending_replans: int = 0
    total_pending_recommendations: int = 0
    total_pending_approvals: int = 0
    pending_replans: List[DecisionReplanItem] = Field(default_factory=list)
    pending_recommendations: List[DecisionRecommendationItem] = Field(default_factory=list)
    pending_approvals: List[DecisionApprovalItem] = Field(default_factory=list)
    data_provenance: str = "DERIVED"
    generated_at: datetime


# ---------------------------------------------------------------------------
# 7. Consequential Action / Audit Summary
# ---------------------------------------------------------------------------

class ConsequentialActionItem(BaseModel):
    """Recent consequential human approval decision and operational application."""
    approval_id: uuid.UUID
    recommendation_id: uuid.UUID
    replan_id: Optional[uuid.UUID] = None
    decision: Optional[str] = None
    approver_person_id: uuid.UUID
    approver_role: Optional[str] = None
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None
    action_summary: str
    applied_changes: List[Dict[str, Any]] = Field(default_factory=list)
    resulting_event_id: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    created_at: datetime
    data_provenance: str = "DERIVED"


# ---------------------------------------------------------------------------
# 8. Scenario Injection (A6)
# ---------------------------------------------------------------------------

class ScenarioInjectRequest(BaseModel):
    """Payload for triggering a deterministic benchmark disruption scenario."""
    scenario_key: str = Field(..., description="Approved benchmark scenario key: FLIGHT_GROUNDING, GENERATOR_FAILURE, COLD_CHAIN_EXCURSION")
    expedition_id: uuid.UUID = Field(..., description="Target expedition ID. Strictly required for tenant isolation.")
    requested_by: Optional[uuid.UUID] = Field(None, description="Operator person ID triggering the disruption.")


class ScenarioInjectResult(BaseModel):
    """Outcome of a deterministic benchmark disruption injection."""
    scenario_key: str
    summary: str
    trigger_event_id: Optional[uuid.UUID] = None
    affected_entity_type: str
    affected_entity_id: uuid.UUID
    affected_entity_code: str
    data_provenance: str = "SYNTHETIC_DEMO"


# ---------------------------------------------------------------------------
# 9. Incident Escalation & Response Bridge (A7)
# ---------------------------------------------------------------------------

class IncidentEscalationRequest(BaseModel):
    """Payload for escalating an active operational incident to Control Tower replanning."""
    model_config = ConfigDict(extra="ignore")

    expedition_id: Optional[uuid.UUID] = Field(None, description="Optional target expedition UUID")
    requested_by: Optional[str] = Field(None, description="Operator or system identifier requesting escalation")
    reason: Optional[str] = Field(None, description="Operational justification or reason for escalation")
    depth: int = Field(default=3, ge=1, le=5, description="Graph traversal depth for blast-radius calculation")
    correlation_id: Optional[str] = Field(None, description="Explicit request correlation UUID or trace string")


class IncidentEscalationResult(BaseModel):
    """Result of escalating an operational incident into Control Tower replanning."""
    incident_id: uuid.UUID
    incident_code: str
    incident_title: str
    incident_severity: str
    incident_status: str
    expedition_id: uuid.UUID
    replan_id: uuid.UUID
    replan_code: str
    replan_status: str
    affected_entities: List[Dict[str, Any]] = Field(default_factory=list)
    violated_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    affected_missions_count: int = 0
    violated_constraints_count: int = 0
    is_existing: bool = False
    correlation_id: Optional[str] = None
    data_provenance: str = "DERIVED"


class IncidentContextView(BaseModel):
    """Contextual representation of an operational incident for Control Tower."""
    incident_id: uuid.UUID
    incident_code: str
    title: str
    severity: str
    status: str
    incident_type: str
    location_id: Optional[uuid.UUID] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    asset_id: Optional[uuid.UUID] = None
    asset_code: Optional[str] = None
    expedition_id: Optional[uuid.UUID] = None
    detected_at: datetime
    description: Optional[str] = None
    propagation_summary: str = ""
    propagations_count: int = 0
    affected_entities: List[Dict[str, Any]] = Field(default_factory=list)
    affected_missions: List[Dict[str, Any]] = Field(default_factory=list)
    affected_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    affected_entities_count: int = 0
    affected_missions_count: int = 0
    violated_constraints_count: int = 0
    replan_id: Optional[uuid.UUID] = None
    replan_code: Optional[str] = None
    correlation_id: Optional[Union[str, uuid.UUID]] = None
    data_provenance: str = "DERIVED"

