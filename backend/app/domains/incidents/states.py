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
