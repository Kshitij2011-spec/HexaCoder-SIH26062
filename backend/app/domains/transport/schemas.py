"""Pydantic Schemas for Transport Legs and Cargo Assignments."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.app.shared.types.states import TransportStatus, AssignmentStatus
from backend.app.shared.types.provenance import DataProvenance
from backend.app.domains.cargo.schemas import CargoConsignmentRead
from backend.app.core.errors import DomainValidationError


class TransportLegBase(BaseModel):
    expedition_id: uuid.UUID
    mode: str = Field(min_length=2, max_length=50, description="Transport mode e.g. VESSEL, AIR, OVERLAND_TRAVERSE")
    origin_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    departure_window_open: Optional[datetime] = None
    departure_window_close: Optional[datetime] = None
    arrival_window_open: Optional[datetime] = None
    arrival_window_close: Optional[datetime] = None
    planned_departure_at: Optional[datetime] = None
    planned_arrival_at: Optional[datetime] = None
    estimated_departure_at: Optional[datetime] = None
    estimated_arrival_at: Optional[datetime] = None
    actual_departure_at: Optional[datetime] = None
    actual_arrival_at: Optional[datetime] = None
    capacity: Optional[Decimal] = Field(default=None, ge=0)
    capacity_unit: Optional[str] = Field(default=None, max_length=50)
    delay_reason: Optional[str] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @model_validator(mode="after")
    def validate_endpoints_and_dates(self) -> "TransportLegBase":
        if self.origin_location_id == self.destination_location_id:
            raise DomainValidationError(
                "Origin and destination locations cannot be identical for a transport leg.",
                field="destination_location_id"
            )
        if self.planned_departure_at and self.planned_arrival_at:
            if self.planned_arrival_at < self.planned_departure_at:
                raise DomainValidationError(
                    "planned_arrival_at cannot precede planned_departure_at",
                    field="planned_arrival_at"
                )
        return self


class TransportLegCreate(TransportLegBase):
    code: str = Field(min_length=2, max_length=50, description="Unique leg code e.g. T-08")
    status: TransportStatus = Field(default=TransportStatus.PLANNED)


class TransportLegUpdate(BaseModel):
    mode: Optional[str] = Field(default=None, min_length=2, max_length=50)
    origin_location_id: Optional[uuid.UUID] = None
    destination_location_id: Optional[uuid.UUID] = None
    departure_window_open: Optional[datetime] = None
    departure_window_close: Optional[datetime] = None
    arrival_window_open: Optional[datetime] = None
    arrival_window_close: Optional[datetime] = None
    planned_departure_at: Optional[datetime] = None
    planned_arrival_at: Optional[datetime] = None
    estimated_departure_at: Optional[datetime] = None
    estimated_arrival_at: Optional[datetime] = None
    actual_departure_at: Optional[datetime] = None
    actual_arrival_at: Optional[datetime] = None
    capacity: Optional[Decimal] = Field(default=None, ge=0)
    capacity_unit: Optional[str] = None
    status: Optional[TransportStatus] = None
    delay_reason: Optional[str] = None
    operational_metadata: Optional[Dict[str, Any]] = None


class TransportLegDelayRequest(BaseModel):
    new_estimated_arrival_at: datetime = Field(description="Updated delayed estimated arrival timestamp")
    delay_reason: str = Field(min_length=3, description="Operational justification e.g. Sea-ice pack thickening")
    operational_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TransportLegRead(TransportLegBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: TransportStatus
    created_at: datetime
    updated_at: datetime


class TransportCargoAssignmentCreate(BaseModel):
    cargo_consignment_id: uuid.UUID
    status: AssignmentStatus = Field(default=AssignmentStatus.APPROVED)


class TransportCargoAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transport_leg_id: uuid.UUID
    cargo_consignment_id: uuid.UUID
    assigned_at: datetime
    released_at: Optional[datetime] = None
    status: AssignmentStatus
    created_at: datetime


class TransportDelayImpactResponse(BaseModel):
    transport_leg: TransportLegRead
    affected_cargo_consignments: List[CargoConsignmentRead]
    summary: str
