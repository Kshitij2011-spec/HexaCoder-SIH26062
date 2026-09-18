"""Canonical Domain Lifecycle State Enumerations."""

from enum import Enum


class ExpeditionStatus(str, Enum):
    """Expedition campaign operational status."""
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    MOBILIZATION = "MOBILIZATION"
    ACTIVE = "ACTIVE"
    CLOSEOUT = "CLOSEOUT"
    ARCHIVED = "ARCHIVED"
    ON_HOLD = "ON_HOLD"


class MissionStatus(str, Enum):
    """Mission operational lifecycle status."""
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class PersonReadiness(str, Enum):
    """Personnel training, qualification, and medical clearance status."""
    NOMINATED = "NOMINATED"
    CLEARANCE_PENDING = "CLEARANCE_PENDING"
    READY = "READY"
    NOT_CLEARED = "NOT_CLEARED"
    UNAVAILABLE = "UNAVAILABLE"


class PersonMovement(str, Enum):
    """Personnel physical operational location status."""
    NOT_DEPLOYED = "NOT_DEPLOYED"
    IN_TRANSIT = "IN_TRANSIT"
    AT_STATION = "AT_STATION"
    FIELD = "FIELD"
    RETURNING = "RETURNING"
    RETURNED = "RETURNED"


class TeamStatus(str, Enum):
    """Field or operational team readiness status."""
    FORMING = "FORMING"
    READY = "READY"
    DEPLOYED = "DEPLOYED"
    FIELD = "FIELD"
    RETURNED = "RETURNED"


class HardSoftConstraint(str, Enum):
    """Time window and constraint rigidity."""
    HARD = "HARD"
    SOFT = "SOFT"
