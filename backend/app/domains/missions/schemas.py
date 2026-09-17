"""Pydantic Schemas for Missions."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.states import MissionStatus
from backend.app.shared.types.provenance import DataProvenance


class MissionBase(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = None
    type: str = Field(min_length=2, max_length=50, description="Mission type e.g. FIELD_SCIENCE, LOGISTICS, RESUPPLY")
    priority: int = Field(default=3, ge=1, le=5, description="Priority integer 1 to 5")
    location_id: Optional[uuid.UUID] = None
    required_by_at: Optional[datetime] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class MissionCreate(MissionBase):
    expedition_id: uuid.UUID
    code: str = Field(min_length=2, max_length=50, description="Mission business code e.g. M-08")
    status: MissionStatus = Field(default=MissionStatus.PROPOSED)


class MissionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = None
    type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    location_id: Optional[uuid.UUID] = None
    required_by_at: Optional[datetime] = None
    status: Optional[MissionStatus] = None


class MissionRead(MissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    expedition_id: uuid.UUID
    code: str
    status: MissionStatus
    created_at: datetime
    updated_at: datetime


class MissionRelationshipRead(BaseModel):
    """Semantic dependency link involving this mission."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relationship_type: str
    source_entity_type: str
    source_entity_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    criticality: Optional[str] = "CRITICAL"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: str = "SYNTHETIC_DEMO"
