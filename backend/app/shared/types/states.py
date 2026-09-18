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


class LocationStatus(str, Enum):
    """Operational status of a polar/logistics location."""
    AVAILABLE = "AVAILABLE"
    RESTRICTED = "RESTRICTED"
    INACCESSIBLE = "INACCESSIBLE"
    CLOSED = "CLOSED"


class TransportStatus(str, Enum):
    """Lifecycle status of a transport leg."""
    PLANNED = "PLANNED"
    BOOKED = "BOOKED"
    READY = "READY"
    DEPARTED = "DEPARTED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    CLOSED = "CLOSED"
    DELAYED = "DELAYED"
    DIVERTED = "DIVERTED"
    CANCELLED = "CANCELLED"


class CargoStatus(str, Enum):
    """Lifecycle status of a cargo consignment shipment."""
    REQUESTED = "REQUESTED"
    DECLARED = "DECLARED"
    APPROVED = "APPROVED"
    PACKED = "PACKED"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    RECEIVED = "RECEIVED"
    HELD = "HELD"
    DELAYED = "DELAYED"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    REJECTED = "REJECTED"


class CargoPackageStatus(str, Enum):
    """Lifecycle status of an individual cargo package unit."""
    PACKED = "PACKED"
    LOADED = "LOADED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    ISSUED = "ISSUED"
    RETURNED = "RETURNED"
    HELD = "HELD"
    DAMAGED = "DAMAGED"
    LOST = "LOST"


class CargoRiskLevel(str, Enum):
    """Deterministic operational delivery risk classification for cargo."""
    NOMINAL = "NOMINAL"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


class AssignmentStatus(str, Enum):
    """Operational assignment status."""
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

