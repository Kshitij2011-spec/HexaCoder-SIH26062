"""Pydantic Schemas for Semantic Dependencies and Graph Traversal."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.reasoning import (
    DependencyRelationship,
    ConstraintSeverity,
    TraversalDirection,
)
from backend.app.shared.types.provenance import DataProvenance


class DependencyBase(BaseModel):
    expedition_id: Optional[uuid.UUID] = None
    relationship_type: DependencyRelationship
    source_entity_type: str = Field(..., max_length=50)
    source_entity_id: uuid.UUID
    target_entity_type: str = Field(..., max_length=50)
    target_entity_id: uuid.UUID
    criticality: Optional[ConstraintSeverity] = ConstraintSeverity.CRITICAL
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: DataProvenance = DataProvenance.SYNTHETIC_DEMO


class DependencyCreate(DependencyBase):
    pass


class DependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    expedition_id: Optional[uuid.UUID] = None
    relationship_type: DependencyRelationship
    source_entity_type: str
    source_entity_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    criticality: Optional[str] = "CRITICAL"
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    data_provenance: str
    created_at: datetime


class DependencyFilter(BaseModel):
    relationship_type: Optional[DependencyRelationship] = None
    criticality: Optional[ConstraintSeverity] = None
    direction: TraversalDirection = TraversalDirection.OUTGOING
    depth: int = Field(default=3, ge=1, le=5)


class DependencyEdge(BaseModel):
    """Normalized directional edge in the dependency graph."""
    source_entity_type: str
    source_entity_id: uuid.UUID
    relationship: DependencyRelationship
    target_entity_type: str
    target_entity_id: uuid.UUID
    direction: str = Field(..., description="'OUTGOING' or 'INCOMING' relative to query node")
    criticality: str = "CRITICAL"
    provenance: str = "SYNTHETIC_DEMO"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DependencyPath(BaseModel):
    """An ordered path of dependency hops from source to destination."""
    depth: int
    edges: List[DependencyEdge]
    terminal_entity_type: str
    terminal_entity_id: uuid.UUID


class DependencyGraphResult(BaseModel):
    """Result of a bounded graph traversal starting from an anchor entity."""
    entity_type: str
    entity_id: uuid.UUID
    direction: TraversalDirection
    depth_limit: int
    total_nodes_visited: int
    direct_dependencies: List[DependencyEdge]
    paths: List[DependencyPath]
