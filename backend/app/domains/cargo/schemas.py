"""Pydantic Schemas for Cargo Consignments and Packages."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.shared.types.states import CargoStatus, CargoPackageStatus, CargoRiskLevel
from backend.app.shared.types.provenance import DataProvenance


# ------------------------------------------------------------
# Cargo Package Schemas
# ------------------------------------------------------------

class CargoPackageBase(BaseModel):
    contents_summary: Optional[str] = Field(default=None, description="Detailed contents description")
    quantity: Decimal = Field(default=Decimal("1.0"), ge=0, description="Manifested item count")
    weight_kg: Optional[Decimal] = Field(default=None, ge=0, description="Gross package weight in kg")
    length_cm: Optional[Decimal] = Field(default=None, ge=0)
    width_cm: Optional[Decimal] = Field(default=None, ge=0)
    height_cm: Optional[Decimal] = Field(default=None, ge=0)
    handling_classification: Optional[str] = Field(default=None, description="e.g. FRAGILE, COLD_CHAIN, HAZMAT")
    current_location_id: Optional[uuid.UUID] = None
    current_transport_leg_id: Optional[uuid.UUID] = None
    condition: str = Field(default="GOOD", description="Physical packaging integrity")
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class CargoPackageCreate(CargoPackageBase):
    code: str = Field(min_length=2, max_length=50, description="Unique package barcode/manifest code e.g. PKG-117-01")
    status: CargoPackageStatus = Field(default=CargoPackageStatus.PACKED)


class CargoPackageUpdate(BaseModel):
    contents_summary: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, ge=0)
    weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    length_cm: Optional[Decimal] = Field(default=None, ge=0)
    width_cm: Optional[Decimal] = Field(default=None, ge=0)
    height_cm: Optional[Decimal] = Field(default=None, ge=0)
    handling_classification: Optional[str] = None
    current_location_id: Optional[uuid.UUID] = None
    current_transport_leg_id: Optional[uuid.UUID] = None
    condition: Optional[str] = None
    status: Optional[CargoPackageStatus] = None


class CargoPackageRead(CargoPackageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    consignment_id: uuid.UUID
    status: CargoPackageStatus
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------
# Cargo Consignment Schemas
# ------------------------------------------------------------

class CargoConsignmentBase(BaseModel):
    expedition_id: uuid.UUID
    origin_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    priority: int = Field(default=3, ge=1, le=5, description="Priority integer 1 (lowest) to 5 (highest)")
    required_by_at: datetime = Field(description="Operational delivery deadline")
    planned_arrival_at: Optional[datetime] = Field(default=None, description="Initial planned delivery ETA")
    estimated_arrival_at: Optional[datetime] = Field(default=None, description="Dynamic current estimated delivery ETA")
    transport_plan_summary: Optional[str] = None
    compliance_status: str = Field(default="REQUIRED", description="Customs/documentation clearance status")
    handling_classification: Optional[str] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class CargoConsignmentCreate(CargoConsignmentBase):
    code: str = Field(min_length=2, max_length=50, description="Unique consignment code e.g. C-117")
    status: CargoStatus = Field(default=CargoStatus.REQUESTED)


class CargoConsignmentUpdate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    origin_location_id: Optional[uuid.UUID] = None
    destination_location_id: Optional[uuid.UUID] = None
    required_by_at: Optional[datetime] = None
    planned_arrival_at: Optional[datetime] = None
    estimated_arrival_at: Optional[datetime] = None
    transport_plan_summary: Optional[str] = None
    compliance_status: Optional[str] = None
    handling_classification: Optional[str] = None
    status: Optional[CargoStatus] = None
    exception_reason: Optional[str] = None


class CargoConsignmentRead(CargoConsignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: CargoStatus
    risk_level: CargoRiskLevel
    exception_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CargoConsignmentDetailRead(CargoConsignmentRead):
    packages: List[CargoPackageRead] = Field(default_factory=list)


class CargoTimelineRead(BaseModel):
    consignment_id: uuid.UUID
    code: str
    required_by_at: datetime
    planned_arrival_at: Optional[datetime] = None
    estimated_arrival_at: Optional[datetime] = None
    buffer_hours: Optional[float] = Field(default=None, description="Hours between ETA and hard deadline")
    status: CargoStatus
    risk_level: CargoRiskLevel
    is_delayed: bool
    exception_reason: Optional[str] = None
