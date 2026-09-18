"""Pydantic Schemas for Teams."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.states import TeamStatus
from backend.app.shared.types.provenance import DataProvenance


class TeamBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    expedition_id: uuid.UUID
    leader_person_id: Optional[uuid.UUID] = None
    mission_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class TeamCreate(TeamBase):
    code: str = Field(min_length=2, max_length=50, description="Unique team identifier e.g. T-01")
    status: TeamStatus = Field(default=TeamStatus.FORMING)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    leader_person_id: Optional[uuid.UUID] = None
    mission_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    status: Optional[TeamStatus] = None


class TeamRead(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: TeamStatus
    created_at: datetime
    updated_at: datetime
