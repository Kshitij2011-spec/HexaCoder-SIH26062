"""Operational Timeline Schemas and Enums for Person B Track B."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class TimelineEntityType(str, Enum):
    """Canonical Person B domain entity types supported by operational timeline."""
    LOCATION = "LOCATION"
    CARGO_CONSIGNMENT = "CARGO_CONSIGNMENT"
    CARGO_PACKAGE = "CARGO_PACKAGE"
    TRANSPORT_LEG = "TRANSPORT_LEG"
    INVENTORY_ITEM = "INVENTORY_ITEM"
    INVENTORY_STOCK_LOT = "INVENTORY_STOCK_LOT"
    ASSET = "ASSET"
    MAINTENANCE_RECORD = "MAINTENANCE_RECORD"
    INCIDENT = "INCIDENT"
    INCIDENT_REFERENCE = "INCIDENT_REFERENCE"
    OFFLINE_OPERATION = "OFFLINE_OPERATION"
    INCIDENT_PROPAGATION = "INCIDENT_PROPAGATION"


ENTITY_TYPE_ALIASES: Dict[str, str] = {
    "LOCATION": TimelineEntityType.LOCATION.value,
    "CARGO_CONSIGNMENT": TimelineEntityType.CARGO_CONSIGNMENT.value,
    "CARGO": TimelineEntityType.CARGO_CONSIGNMENT.value,
    "CONSIGNMENT": TimelineEntityType.CARGO_CONSIGNMENT.value,
    "CARGO_PACKAGE": TimelineEntityType.CARGO_PACKAGE.value,
    "PACKAGE": TimelineEntityType.CARGO_PACKAGE.value,
    "TRANSPORT_LEG": TimelineEntityType.TRANSPORT_LEG.value,
    "TRANSPORT": TimelineEntityType.TRANSPORT_LEG.value,
    "LEG": TimelineEntityType.TRANSPORT_LEG.value,
    "INVENTORY_ITEM": TimelineEntityType.INVENTORY_ITEM.value,
    "INVENTORY": TimelineEntityType.INVENTORY_ITEM.value,
    "ITEM": TimelineEntityType.INVENTORY_ITEM.value,
    "INVENTORY_STOCK_LOT": TimelineEntityType.INVENTORY_STOCK_LOT.value,
    "STOCK_LOT": TimelineEntityType.INVENTORY_STOCK_LOT.value,
    "LOT": TimelineEntityType.INVENTORY_STOCK_LOT.value,
    "ASSET": TimelineEntityType.ASSET.value,
    "MAINTENANCE_RECORD": TimelineEntityType.MAINTENANCE_RECORD.value,
    "MAINTENANCE": TimelineEntityType.MAINTENANCE_RECORD.value,
    "INCIDENT": TimelineEntityType.INCIDENT.value,
    "INCIDENT_REFERENCE": TimelineEntityType.INCIDENT_REFERENCE.value,
    "REFERENCE": TimelineEntityType.INCIDENT_REFERENCE.value,
    "OFFLINE_OPERATION": TimelineEntityType.OFFLINE_OPERATION.value,
    "OFFLINE_SYNC": TimelineEntityType.OFFLINE_OPERATION.value,
    "SYNC_OPERATION": TimelineEntityType.OFFLINE_OPERATION.value,
    "SYNC": TimelineEntityType.OFFLINE_OPERATION.value,
    "INCIDENT_PROPAGATION": TimelineEntityType.INCIDENT_PROPAGATION.value,
    "PROPAGATION": TimelineEntityType.INCIDENT_PROPAGATION.value,
}


def normalize_entity_type(raw_type: str) -> Optional[str]:
    """Normalizes an entity type or alias to its canonical Person B domain name."""
    if not raw_type:
        return None
    cleaned = raw_type.strip().upper()
    return ENTITY_TYPE_ALIASES.get(cleaned)


class TimelineEntryType(str, Enum):
    """Categorical source type of a timeline record."""
    OPERATIONAL_EVENT = "OPERATIONAL_EVENT"
    AUDIT_RECORD = "AUDIT_RECORD"
    PROPAGATION_RECORD = "PROPAGATION_RECORD"
    OFFLINE_SYNC = "OFFLINE_SYNC"


class TimelineEntry(BaseModel):
    """Unified operational timeline item preserving event, audit, and domain context."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique technical identifier for the timeline item")
    entry_type: TimelineEntryType = Field(..., description="Categorical classification of the entry")
    timestamp: datetime = Field(..., description="UTC timestamp of when the action occurred")
    event_or_action: str = Field(..., description="Operational event type or primary action name")
    audit_action: Optional[str] = Field(None, description="Corresponding audit log action if correlated")
    entity_type: str = Field(..., description="Canonical entity type of the primary target")
    entity_id: uuid.UUID = Field(..., description="Technical UUID of the primary target")
    entity_name: Optional[str] = Field(None, description="Human-readable code or label of the target")
    source: str = Field(default="SYSTEM", description="Originating subsystem (e.g. EVENT_JOURNAL, AUDIT_LOG, SYNC_API)")
    previous_state: Optional[str] = Field(None, description="Previous status or lifecycle state")
    new_state: Optional[str] = Field(None, description="Resulting status or lifecycle state")
    status: Optional[str] = Field(None, description="Operational status flag or propagation outcome")
    actor_type: Optional[str] = Field(None, description="Actor type (USER, SYSTEM, FIELD_CLIENT)")
    actor_id: Optional[uuid.UUID] = Field(None, description="Attributable person or user UUID")
    correlation_id: Optional[uuid.UUID] = Field(None, description="Transaction correlation UUID")
    data_provenance: str = Field(default="SYNTHETIC_DEMO", description="Data provenance classification")
    description: Optional[str] = Field(None, description="Human-readable operational summary")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured snapshot, evidence, or metadata")
    related_entity_type: Optional[str] = Field(None, description="Type of related entity if cross-domain query")
    related_entity_id: Optional[uuid.UUID] = Field(None, description="UUID of related entity if cross-domain query")
    audit_id: Optional[uuid.UUID] = Field(None, description="Attributable AuditLog UUID if linked")
    event_id: Optional[uuid.UUID] = Field(None, description="Immutable OperationalEvent UUID if linked")


class TimelineResponse(BaseModel):
    """Paginated operational timeline payload."""
    model_config = ConfigDict(from_attributes=True)

    entity_type: str = Field(..., description="Canonical entity type queried")
    entity_id: uuid.UUID = Field(..., description="Primary entity UUID queried")
    entity_name: Optional[str] = Field(None, description="Human-readable name or code of queried entity")
    total_entries: int = Field(..., description="Total available timeline records matching query")
    page: int = Field(..., description="Current page index (1-based)")
    page_size: int = Field(..., description="Number of entries per page")
    total_pages: int = Field(..., description="Total pages available")
    entries: List[TimelineEntry] = Field(default_factory=list, description="Ordered list of timeline entries")
    related_entities_included: bool = Field(default=False, description="Whether 1-hop cross-domain entities were aggregated")
