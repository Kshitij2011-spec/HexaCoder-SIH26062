"""Pydantic Schemas for People."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.states import PersonReadiness, PersonMovement
from backend.app.shared.types.provenance import DataProvenance


class PersonBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    role: str = Field(min_length=2, max_length=100, description="Expedition role e.g. Chief Glaciologist, Field Medic")
    organization: Optional[str] = Field(default=None, max_length=150)
    expedition_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    current_location_id: Optional[uuid.UUID] = None
    last_confirmed_location_id: Optional[uuid.UUID] = None
    emergency_status: Optional[str] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class PersonCreate(PersonBase):
    person_code: str = Field(min_length=2, max_length=50, description="Unique personnel code e.g. P-01")
    readiness_state: PersonReadiness = Field(default=PersonReadiness.NOMINATED)
    movement_state: PersonMovement = Field(default=PersonMovement.NOT_DEPLOYED)


class PersonUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    role: Optional[str] = Field(default=None, min_length=2, max_length=100)
    organization: Optional[str] = None
    team_id: Optional[uuid.UUID] = None
    current_location_id: Optional[uuid.UUID] = None
    last_confirmed_location_id: Optional[uuid.UUID] = None
    emergency_status: Optional[str] = None
    readiness_state: Optional[PersonReadiness] = None
    movement_state: Optional[PersonMovement] = None


class PersonReadinessUpdate(BaseModel):
    readiness_state: PersonReadiness


class PersonMovementUpdate(BaseModel):
    movement_state: PersonMovement
    current_location_id: Optional[uuid.UUID] = None


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_code: str
    readiness_state: PersonReadiness
    movement_state: PersonMovement
    created_at: datetime
    updated_at: datetime
