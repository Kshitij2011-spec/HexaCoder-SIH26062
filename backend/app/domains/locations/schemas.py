"""Pydantic Schemas for Locations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.shared.types.states import LocationStatus
from backend.app.shared.types.provenance import DataProvenance
from backend.app.core.errors import DomainValidationError


class LocationBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, description="Human readable location name")
    type: str = Field(min_length=2, max_length=50, description="Location category e.g. PORT, STATION, FIELD_CAMP")
    parent_location_id: Optional[uuid.UUID] = Field(default=None, description="Parent location ID in hierarchy")
    latitude: Optional[Decimal] = Field(default=None, description="Latitude in decimal degrees (-90 to 90)")
    longitude: Optional[Decimal] = Field(default=None, description="Longitude in decimal degrees (-180 to 180)")
    description: Optional[str] = Field(default=None, description="Operational notes and logistics profile")
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < Decimal("-90.0") or v > Decimal("90.0")):
            raise DomainValidationError("Latitude must be between -90.0 and 90.0 degrees", field="latitude")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < Decimal("-180.0") or v > Decimal("180.0")):
            raise DomainValidationError("Longitude must be between -180.0 and 180.0 degrees", field="longitude")
        return v


class LocationCreate(LocationBase):
    code: str = Field(min_length=2, max_length=50, description="Unique location code e.g. LOC-IND-GOA")
    status: LocationStatus = Field(default=LocationStatus.AVAILABLE)


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    parent_location_id: Optional[uuid.UUID] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    status: Optional[LocationStatus] = None
    description: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < Decimal("-90.0") or v > Decimal("90.0")):
            raise DomainValidationError("Latitude must be between -90.0 and 90.0 degrees", field="latitude")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v < Decimal("-180.0") or v > Decimal("180.0")):
            raise DomainValidationError("Longitude must be between -180.0 and 180.0 degrees", field="longitude")
        return v


class LocationStatusUpdate(BaseModel):
    status: LocationStatus
    reason: Optional[str] = Field(default=None, description="Operational justification for state change")


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: LocationStatus
    created_at: datetime
    updated_at: datetime


class LocationHierarchyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location: LocationRead
    ancestors: List[LocationRead] = Field(default_factory=list, description="Ordered lineage from root down to parent")
    children: List[LocationRead] = Field(default_factory=list, description="Direct child sub-locations")
