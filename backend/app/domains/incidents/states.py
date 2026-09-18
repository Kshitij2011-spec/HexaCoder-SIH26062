"""Canonical State and Controlled Type Enumerations for Incident Response."""

from enum import Enum


class IncidentStatus(str, Enum):
    """Operational lifecycle status of an incident."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IncidentSeverity(str, Enum):
    """Incident severity classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentReferenceType(str, Enum):
    """Supported operational resource types for loose incident linkage."""
    LOCATION = "LOCATION"
    ASSET = "ASSET"
    INVENTORY_STOCK_LOT = "INVENTORY_STOCK_LOT"
    CARGO_CONSIGNMENT = "CARGO_CONSIGNMENT"
    TRANSPORT_LEG = "TRANSPORT_LEG"


class PropagationStatus(str, Enum):
    """Status of cross-domain operational impact propagation."""
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"
    REQUIRES_OPERATOR_ACTION = "REQUIRES_OPERATOR_ACTION"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class PropagationAction(str, Enum):
    """Authoritative cross-domain action triggered by incident propagation."""
    RESTRICT_LOCATION = "RESTRICT_LOCATION"
    ISOLATE_LOCATION = "ISOLATE_LOCATION"
    MAINTENANCE_ASSET = "MAINTENANCE_ASSET"
    QUARANTINE_ASSET = "QUARANTINE_ASSET"
    QUARANTINE_STOCK = "QUARANTINE_STOCK"
    DELAY_TRANSPORT = "DELAY_TRANSPORT"
    REVIEW_CARGO = "REVIEW_CARGO"
    NONE = "NONE"

