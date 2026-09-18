"""Canonical State and Controlled Type Enumerations for Assets and Maintenance."""

from enum import Enum


class AssetStatus(str, Enum):
    """Operational lifecycle status of polar physical assets."""
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class MaintenanceStatus(str, Enum):
    """Lifecycle status of an asset maintenance order/task."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    OVERDUE = "OVERDUE"


class AssetCriticality(str, Enum):
    """Expedition criticality tier for physical assets."""
    STANDARD = "STANDARD"
    MISSION_CRITICAL = "MISSION_CRITICAL"
    LIFE_SUPPORT = "LIFE_SUPPORT"
    SAFETY = "SAFETY"


class AssetCondition(str, Enum):
    """Physical and operational condition assessment."""
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    DAMAGED = "DAMAGED"
    INOPERABLE = "INOPERABLE"
