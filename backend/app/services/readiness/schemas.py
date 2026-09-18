"""Pydantic Schemas for Mission and Expedition Readiness."""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.shared.types.reasoning import ReadinessState
from backend.app.services.constraints.schemas import ConstraintEvaluationResult


class BlockerItem(BaseModel):
    """Hard blocker preventing operational mission execution."""
    type: str = Field(..., description="Category: PERSONNEL, ASSET, CARGO, CONSTRAINT, TIME_WINDOW")
    entity_type: str
    entity_id: uuid.UUID
    entity_code: Optional[str] = None
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class WarningItem(BaseModel):
    """Operational warning or soft risk requiring operator advisory."""
    type: str
    entity_type: str
    entity_id: uuid.UUID
    entity_code: Optional[str] = None
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class SatisfiedRequirement(BaseModel):
    """Verified prerequisite satisfied by domain state."""
    category: str
    description: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class UnknownRequirement(BaseModel):
    """Dependency category where domain provider module is pending integration."""
    category: str
    description: str
    reason: str
    status: str = "PENDING_TRACK_B"


class MissionReadinessResult(BaseModel):
    """
    Deterministic operational readiness assessment for a polar mission.
    Strictly evidence-backed; no arbitrary percentages or scores.
    """
    mission_id: uuid.UUID
    mission_code: str
    state: ReadinessState
    blockers: List[BlockerItem]
    warnings: List[WarningItem]
    satisfied_requirements: List[SatisfiedRequirement]
    unknown_requirements: List[UnknownRequirement]
    constraints_evaluated: int
    violated_constraints: List[ConstraintEvaluationResult]
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ExpeditionReadinessResult(BaseModel):
    """
    Aggregated operational readiness for an entire expedition campaign.
    Derived strictly from underlying mission readiness and expedition constraints.
    """
    expedition_id: uuid.UUID
    expedition_code: str
    state: ReadinessState
    total_missions: int
    ready_missions: int
    at_risk_missions: int
    blocked_missions: int
    mission_summaries: List[MissionReadinessResult]
    blockers: List[BlockerItem]
    warnings: List[WarningItem]
    unknown_requirements: List[UnknownRequirement]
    explanation: str
