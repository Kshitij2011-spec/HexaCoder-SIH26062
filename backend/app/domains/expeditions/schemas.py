"""Pydantic Schemas for Expeditions."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.app.shared.types.states import ExpeditionStatus
from backend.app.shared.types.provenance import DataProvenance
from backend.app.core.errors import DomainValidationError


class ExpeditionBase(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    season: str = Field(min_length=4, max_length=50, description="Operating season e.g. 2026-2027")
    objective: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    priority: int = Field(default=3, ge=1, le=5, description="Priority integer 1 (lowest) to 5 (highest)")
    notes: Optional[str] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @model_validator(mode="after")
    def validate_date_bounds(self) -> "ExpeditionBase":
        if self.planned_start_at and self.planned_end_at:
            if self.planned_end_at < self.planned_start_at:
                raise DomainValidationError(
                    "planned_end_at cannot precede planned_start_at",
                    field="planned_end_at"
                )
        return self


class ExpeditionCreate(ExpeditionBase):
    code: str = Field(min_length=3, max_length=50, description="Unique expedition code e.g. EXP-26-A")
    status: ExpeditionStatus = Field(default=ExpeditionStatus.DRAFT)


class ExpeditionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=255)
    objective: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    status: Optional[ExpeditionStatus] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_date_bounds(self) -> "ExpeditionUpdate":
        if self.planned_start_at and self.planned_end_at:
            if self.planned_end_at < self.planned_start_at:
                raise DomainValidationError(
                    "planned_end_at cannot precede planned_start_at",
                    field="planned_end_at"
                )
        return self


class ExpeditionRead(ExpeditionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: ExpeditionStatus
    created_at: datetime
    updated_at: datetime


class ExpeditionSummary(BaseModel):
    """Aggregate operational overview for an expedition."""
    expedition: ExpeditionRead
    mission_count: int = 0
    active_mission_count: int = 0
    team_count: int = 0
    personnel_count: int = 0
    active_events_count: int = 0
    time_windows_count: int = 0
    exception_states: Dict[str, Any] = Field(default_factory=dict)
