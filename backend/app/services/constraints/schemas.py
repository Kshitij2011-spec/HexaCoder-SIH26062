"""Pydantic Schemas for Operational Constraints and Evaluations."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.reasoning import (
    ConstraintSeverity,
    ConstraintState,
)
from backend.app.shared.types.states import HardSoftConstraint
from backend.app.shared.types.provenance import DataProvenance


class ConstraintBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    type: str = Field(..., max_length=100)
    severity: ConstraintSeverity = ConstraintSeverity.CRITICAL
    hard_or_soft: HardSoftConstraint = HardSoftConstraint.HARD
    subject_type: Optional[str] = Field(None, max_length=50)
    subject_id: Optional[uuid.UUID] = None
    rule_code: str = Field(..., max_length=100)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    active: bool = True
    data_provenance: DataProvenance = DataProvenance.SYNTHETIC_DEMO


class ConstraintCreate(ConstraintBase):
    pass


class ConstraintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    type: str
    severity: str
    hard_or_soft: str
    subject_type: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    rule_code: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    active: bool
    data_provenance: str
    created_at: datetime
    updated_at: datetime


class ConstraintEvaluationResult(BaseModel):
    """Deterministic evaluation outcome of an operational constraint."""
    constraint_id: Optional[uuid.UUID] = None
    code: str
    name: str
    severity: ConstraintSeverity
    hard_or_soft: HardSoftConstraint
    state: ConstraintState
    subject_type: str
    subject_id: uuid.UUID
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class EntityConstraintsSummary(BaseModel):
    """Aggregated constraints status for an operational entity."""
    entity_type: str
    entity_id: uuid.UUID
    total_evaluated: int
    satisfied_count: int
    violated_count: int
    not_evaluable_count: int
    results: List[ConstraintEvaluationResult]
