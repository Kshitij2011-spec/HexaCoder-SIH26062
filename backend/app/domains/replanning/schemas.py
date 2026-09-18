"""Pydantic Schemas for Replanning, Candidate Options, Recommendations, and Approvals."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.domains.replanning.states import (
    ReplanStatus,
    RecommendationStatus,
    ApprovalDecision,
    ApprovalStatus,
    OptionFeasibility,
    ReplanActionType,
)
from backend.app.shared.types.provenance import DataProvenance


class ReplanTriggerRequest(BaseModel):
    """Request payload for triggering an operational replan cycle."""
    trigger_mode: str = Field(
        default="OPERATOR_REQUESTED",
        description="Mode of trigger: 'OPERATOR_REQUESTED' or 'EVENT_TRIGGERED'"
    )
    expedition_id: Optional[uuid.UUID] = None
    mission_id: Optional[uuid.UUID] = None
    trigger_event_id: Optional[uuid.UUID] = None
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[uuid.UUID] = None
    reason: str = Field(..., min_length=3, description="Operational justification or trigger reason")
    requested_by: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    depth: int = Field(default=3, ge=1, le=5, description="Graph traversal depth for impact calculation")


class ReplanCreate(BaseModel):
    """Internal schema for creating a replan entity."""
    expedition_id: Optional[uuid.UUID] = None
    mission_id: Optional[uuid.UUID] = None
    replan_code: Optional[str] = None
    trigger_event_id: Optional[uuid.UUID] = None
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[uuid.UUID] = None
    trigger_reason: str
    current_state_evidence: Dict[str, Any] = Field(default_factory=dict)
    violated_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    affected_entities: List[Dict[str, Any]] = Field(default_factory=list)
    requested_by: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    data_provenance: DataProvenance = DataProvenance.SYNTHETIC_DEMO


class ReplanOptionRead(BaseModel):
    """Read schema for a deterministic candidate mitigation option."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    replan_id: Optional[uuid.UUID] = None
    recommendation_id: Optional[uuid.UUID] = None
    option_code: str
    title: str
    description: Optional[str] = None
    action_type: str
    affected_entity_type: Optional[str] = None
    affected_entity_id: Optional[uuid.UUID] = None
    proposed_state_change: Dict[str, Any] = Field(default_factory=dict)
    prerequisite_conditions: List[Any] = Field(default_factory=list)
    expected_impact: Dict[str, Any] = Field(default_factory=dict)
    constraints_checked: List[Any] = Field(default_factory=list)
    constraints_violated: List[Any] = Field(default_factory=list)
    unknown_requirements: List[Any] = Field(default_factory=list)
    feasibility_state: str
    operational_rationale: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    is_selected: bool = False
    data_provenance: str = "ADVISORY"
    created_at: datetime


class RecommendationRead(BaseModel):
    """Read schema for an explainable operational recommendation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    replan_id: uuid.UUID
    option_id: Optional[uuid.UUID] = None
    trigger_event_id: Optional[uuid.UUID] = None
    title: str
    summary: Optional[str] = None
    rationale: List[str] = Field(default_factory=list)
    supporting_evidence: Dict[str, Any] = Field(default_factory=dict)
    constraint_evaluation_summary: Dict[str, Any] = Field(default_factory=dict)
    affected_entities: List[Any] = Field(default_factory=list)
    violated_constraints: List[Any] = Field(default_factory=list)
    proposed_changes: List[Any] = Field(default_factory=list)
    expected_impact: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    status: str
    approval_state: str = "PROPOSED"
    data_provenance: str = "ADVISORY"
    generated_at: datetime
    created_at: datetime


class ReplanRead(BaseModel):
    """Read schema for an operational replan entity."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    replan_code: str
    expedition_id: uuid.UUID
    mission_id: Optional[uuid.UUID] = None
    trigger_event_id: Optional[uuid.UUID] = None
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[uuid.UUID] = None
    trigger_reason: Optional[str] = None
    status: str
    current_state_evidence: Dict[str, Any] = Field(default_factory=dict)
    violated_constraints: List[Any] = Field(default_factory=list)
    affected_entities: List[Any] = Field(default_factory=list)
    requested_by: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    generated_at: datetime
    completed_at: Optional[datetime] = None
    data_provenance: str
    options: List[ReplanOptionRead] = Field(default_factory=list)
    recommendations: List[RecommendationRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApprovalDecisionRequest(BaseModel):
    """Payload for submitting a human operator approval decision."""
    model_config = ConfigDict(extra="forbid")

    approver_person_id: uuid.UUID
    approver_role: Optional[str] = "EXPEDITION_OPERATOR"
    decision: ApprovalDecision
    comment: Optional[str] = Field(None, description="Operational justification for approval/rejection")
    correlation_id: Optional[uuid.UUID] = None


class ApprovalRead(BaseModel):
    """Read schema for an approval decision record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommendation_id: uuid.UUID
    approver_user_id: Optional[uuid.UUID] = None
    approver_person_id: uuid.UUID
    approver_role: Optional[str] = None
    decision: Optional[str] = None
    comment: Optional[str] = None
    status: str
    decided_at: Optional[datetime] = None
    resulting_event_id: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None
    created_at: datetime


class ReplanApplyRequest(BaseModel):
    """Payload for executing an approved operational recommendation."""
    model_config = ConfigDict(extra="forbid")

    actor_person_id: uuid.UUID
    comment: Optional[str] = Field(None, description="Operator comment accompanying application")
    correlation_id: Optional[uuid.UUID] = None



class ReplanApplyResult(BaseModel):
    """Result of applying an approved recommendation through domain services."""
    recommendation_id: uuid.UUID
    status: str
    applied_changes: List[Dict[str, Any]] = Field(default_factory=list)
    resulting_event_id: Optional[uuid.UUID] = None
    applied_at: datetime
    message: str
