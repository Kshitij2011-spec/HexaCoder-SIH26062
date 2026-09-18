"""Pydantic v2 Schemas for Incidents and Incident References."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
)
from backend.app.shared.types.provenance import DataProvenance


# ============================================================
# 1. INCIDENT SCHEMAS
# ============================================================

class IncidentBase(BaseModel):
    title: str = Field(default="Operational Incident", min_length=1, max_length=255, description="Brief summary of the incident")
    description: Optional[str] = Field(default=None, description="Detailed account of the operational anomaly or failure")
    incident_type: str = Field(default="OPERATIONAL", min_length=1, max_length=100, description="Classification of incident e.g. EQUIPMENT_FAILURE, WEATHER_HAZARD")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM, description="Incident severity level")
    priority: int = Field(default=3, ge=1, le=5, description="Priority integer 1 (lowest) to 5 (highest)")
    location_id: Optional[uuid.UUID] = Field(default=None, description="Location where the incident occurred")
    asset_id: Optional[uuid.UUID] = Field(default=None, description="Directly affected asset if applicable")
    expedition_id: Optional[uuid.UUID] = Field(default=None, description="Parent expedition if linked")
    operational_metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary operational context")
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @model_validator(mode="before")
    @classmethod
    def handle_type_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "type" in data and "incident_type" not in data:
                data["incident_type"] = data["type"]
        return data


class IncidentCreate(IncidentBase):
    incident_code: str = Field(min_length=2, max_length=50, description="Unique operational code e.g. INC-2026-001")
    detected_at: Optional[datetime] = Field(default=None, description="Timestamp when incident was detected (defaults to now)")


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    incident_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    severity: Optional[IncidentSeverity] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    location_id: Optional[uuid.UUID] = None
    asset_id: Optional[uuid.UUID] = None
    operational_metadata: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def handle_type_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "type" in data and "incident_type" not in data:
                data["incident_type"] = data["type"]
        return data


class IncidentStatusTransitionRequest(BaseModel):
    status: IncidentStatus = Field(description="Target lifecycle state")
    reason: Optional[str] = Field(default=None, description="Justification for state change")
    operational_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context to merge into metadata")


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_code: str
    status: IncidentStatus
    type: str
    detected_at: datetime
    declared_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# 2. INCIDENT REFERENCE SCHEMAS
# ============================================================

class IncidentReferenceCreate(BaseModel):
    reference_type: IncidentReferenceType = Field(description="Type of referenced operational resource")
    reference_id: uuid.UUID = Field(description="UUID of the referenced operational resource")
    notes: Optional[str] = Field(default=None, description="Contextual note describing the relationship or observed impact")
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class IncidentReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    reference_type: IncidentReferenceType
    reference_id: uuid.UUID
    notes: Optional[str] = None
    operational_metadata: Dict[str, Any]
    created_at: datetime


# ============================================================
# 3. INCIDENT TIMELINE SCHEMAS
# ============================================================

class IncidentTimelineEntry(BaseModel):
    timestamp: datetime
    entry_type: str = Field(description="Category of entry e.g. EVENT, AUDIT, REFERENCE")
    action_or_event: str = Field(description="Action name or event type")
    actor: Optional[str] = None
    description: Optional[str] = None
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class IncidentTimelineRead(BaseModel):
    incident_id: uuid.UUID
    incident_code: str
    current_status: IncidentStatus
    entries: List[IncidentTimelineEntry]
    total_entries: int
