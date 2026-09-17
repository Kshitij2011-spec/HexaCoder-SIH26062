"""Pydantic Schemas for Time Windows."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.app.shared.types.states import HardSoftConstraint
from backend.app.shared.types.provenance import DataProvenance
from backend.app.core.errors import DomainValidationError


class TimeWindowBase(BaseModel):
    type: str = Field(min_length=2, max_length=50, description="Window category e.g. WEATHER_WINDOW, FLIGHT_WINDOW")
    open_at: datetime
    close_at: datetime
    hard_or_soft: HardSoftConstraint = Field(default=HardSoftConstraint.HARD)
    subject_type: str = Field(min_length=2, max_length=50, description="Subject entity type e.g. MISSION, EXPEDITION")
    subject_id: uuid.UUID
    status: str = Field(default="OPEN", max_length=50)
    description: Optional[str] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @model_validator(mode="after")
    def validate_bounds(self) -> "TimeWindowBase":
        if self.close_at <= self.open_at:
            raise DomainValidationError(
                f"Time window close_at ({self.close_at.isoformat()}) must be strictly after open_at ({self.open_at.isoformat()})",
                field="close_at"
            )
        return self


class TimeWindowCreate(TimeWindowBase):
    pass


class TimeWindowUpdate(BaseModel):
    type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    open_at: Optional[datetime] = None
    close_at: Optional[datetime] = None
    hard_or_soft: Optional[HardSoftConstraint] = None
    status: Optional[str] = None
    description: Optional[str] = None


class TimeWindowRead(TimeWindowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
