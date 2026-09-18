"""Pydantic Schemas for Operational Events."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.provenance import DataProvenance


class OperationalEventRead(BaseModel):
    """Event representation returned in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    occurred_at: datetime
    source: str
    actor_type: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[uuid.UUID] = None
    data_provenance: DataProvenance
    created_at: datetime


class OperationalEventCreate(BaseModel):
    """Internal model for appending events."""
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    occurred_at: Optional[datetime] = None
    source: str = "API"
    actor_type: Optional[str] = "SYSTEM"
    actor_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[uuid.UUID] = None
    data_provenance: DataProvenance = DataProvenance.SYNTHETIC_DEMO


class OperationalEventFilter(BaseModel):
    """Query parameters for filtering operational events."""
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    event_type: Optional[str] = None
    correlation_id: Optional[uuid.UUID] = None
    occurred_from: Optional[datetime] = None
    occurred_to: Optional[datetime] = None
