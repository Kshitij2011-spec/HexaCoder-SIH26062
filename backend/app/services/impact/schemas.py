"""Pydantic Schemas for Operational Impact Propagation."""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.services.dependencies.schemas import DependencyPath
from backend.app.services.constraints.schemas import ConstraintEvaluationResult


class AffectedEntity(BaseModel):
    """An operational entity affected by an upstream state mutation or disruption."""
    entity_type: str
    entity_id: uuid.UUID
    entity_code: Optional[str] = None
    relationship: str
    depth: int
    direction: str = "INCOMING"
    reason: str


class ImpactResult(BaseModel):
    """
    Deterministic impact analysis result showing affected entities,
    dependency traversal paths, and violated or at-risk operational constraints.
    """
    source_entity_type: str
    source_entity_id: uuid.UUID
    source_entity_code: Optional[str] = None
    change_summary: str
    depth_limit: int
    total_affected_entities: int
    affected_entities: List[AffectedEntity]
    dependency_paths: List[DependencyPath]
    reasons: List[str]
    constraint_candidates: List[ConstraintEvaluationResult]
    correlation_id: Optional[uuid.UUID] = None
