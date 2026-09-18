"""Pydantic Schemas for Assets and Maintenance."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.domains.assets.states import (
    AssetStatus,
    MaintenanceStatus,
    AssetCriticality,
    AssetCondition,
)
from backend.app.shared.types.provenance import DataProvenance


# ============================================================
# 1. ASSET SCHEMAS
# ============================================================

class AssetBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, description="Human readable asset name e.g. Hägglunds BV206 Tracked Vehicle")
    type: str = Field(min_length=2, max_length=100, description="Asset classification e.g. VEHICLE, POWER_GENERATION, SEISMIC_STATION")
    model: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    condition: AssetCondition = Field(default=AssetCondition.OPERATIONAL)
    criticality: AssetCriticality = Field(default=AssetCriticality.STANDARD)
    location_id: Optional[uuid.UUID] = Field(default=None, description="Station or hub where asset currently resides")
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)
    commissioned_at: Optional[datetime] = None
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class AssetCreate(AssetBase):
    asset_code: str = Field(min_length=2, max_length=50, description="Unique operational code e.g. AST-VEH-01")
    serial_number: Optional[str] = Field(default=None, max_length=100, description="Manufacturer serial number")
    status: AssetStatus = Field(default=AssetStatus.AVAILABLE)


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    type: Optional[str] = Field(default=None, min_length=2, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    condition: Optional[AssetCondition] = None
    criticality: Optional[AssetCriticality] = None
    operational_metadata: Optional[Dict[str, Any]] = None


class AssetStatusTransitionRequest(BaseModel):
    target_status: AssetStatus
    reason: Optional[str] = Field(default=None, description="Operational justification for state change")


class AssetMoveRequest(BaseModel):
    destination_location_id: uuid.UUID = Field(description="Target location for asset transfer")
    reason: Optional[str] = Field(default=None, description="Reason for relocation")


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_code: str
    serial_number: Optional[str] = None
    status: AssetStatus
    maintenance_state: Optional[str] = "SERVICEABLE"
    retired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# 2. MAINTENANCE SCHEMAS
# ============================================================

class MaintenanceScheduleRequest(BaseModel):
    maintenance_type: str = Field(min_length=2, max_length=100, description="e.g. PREVENTATIVE, CORRECTIVE, OVERHAUL")
    priority: int = Field(default=3, ge=1, le=5, description="Priority scale 1 (highest) to 5 (lowest)")
    scheduled_at: Optional[datetime] = Field(default=None, description="Planned execution timestamp")
    description: Optional[str] = None
    performed_by: Optional[str] = Field(default=None, max_length=150, description="Assigned personnel or team")
    technician_reference: Optional[str] = Field(default=None, max_length=150, description="Vendor or engineer reference")
    notes: Optional[str] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class MaintenanceStartRequest(BaseModel):
    started_at: Optional[datetime] = None
    technician_reference: Optional[str] = Field(default=None, max_length=150)
    notes: Optional[str] = None
    transition_asset_to_maintenance: bool = Field(
        default=False,
        description="Optionally update asset lifecycle status to MAINTENANCE if currently AVAILABLE or IN_USE"
    )


class MaintenanceCompleteRequest(BaseModel):
    completed_at: Optional[datetime] = None
    findings: Optional[str] = Field(default=None, description="Inspection diagnosis or issues identified")
    corrective_action: Optional[str] = Field(default=None, description="Remedial action taken, parts replaced")
    target_asset_status: Optional[AssetStatus] = Field(
        default=None,
        description="Explicitly transition asset status upon completion (does NOT change silently)"
    )
    notes: Optional[str] = None


class MaintenanceCancelRequest(BaseModel):
    reason: str = Field(min_length=2, description="Reason for cancelling maintenance order")


class MaintenanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    maintenance_type: str
    priority: int
    status: MaintenanceStatus
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    description: Optional[str] = None
    performed_by: Optional[str] = None
    technician_reference: Optional[str] = None
    findings: Optional[str] = None
    corrective_action: Optional[str] = None
    notes: Optional[str] = None
    operational_metadata: Dict[str, Any]
    data_provenance: DataProvenance
    created_at: datetime
    updated_at: datetime


# ============================================================
# 3. TIMELINE SCHEMAS
# ============================================================

class AssetTimelineEvent(BaseModel):
    timestamp: datetime
    event_type: str
    summary: str
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AssetTimelineRead(BaseModel):
    asset_id: uuid.UUID
    asset_code: str
    name: str
    status: AssetStatus
    current_location_id: Optional[uuid.UUID] = None
    active_maintenance: Optional[MaintenanceRecordRead] = None
    maintenance_history_count: int
    timeline: List[AssetTimelineEvent]
