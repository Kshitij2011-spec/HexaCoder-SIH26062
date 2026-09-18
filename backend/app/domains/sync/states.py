"""Offline Operation status states for Track B Sync domain."""

from enum import Enum


class OfflineOperationStatus(str, Enum):
    """Lifecycle states for an offline operation in the queue."""
    PENDING = "PENDING"       # Queued, not yet applied
    APPLIED = "APPLIED"       # Successfully replayed/applied
    FAILED = "FAILED"         # Attempted but failed (retryable)
    REJECTED = "REJECTED"     # Permanently invalid/non-retryable


class OfflineOperationType(str, Enum):
    """Allowed operation types that can be queued offline."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    STATE_TRANSITION = "STATE_TRANSITION"
    DELETE = "DELETE"


# Terminal states — no further transitions allowed
TERMINAL_STATUSES = {OfflineOperationStatus.APPLIED, OfflineOperationStatus.REJECTED}

# Allowed domain entity types for offline operations
ALLOWED_ENTITY_TYPES = {
    "INVENTORY_ITEM",
    "INVENTORY_STOCK_LOT",
    "INVENTORY_TRANSACTION",
    "ASSET",
    "MAINTENANCE_RECORD",
    "INCIDENT",
    "INCIDENT_REFERENCE",
    "LOCATION",
    "TRANSPORT",
    "TRANSPORT_LEG",
    "CARGO",
    "CARGO_CONSIGNMENT",
    "CARGO_PACKAGE",
    "EXPEDITION",
    "MISSION",
    "PERSON",
    "TEAM",
    "TIME_WINDOW",
    "DOCUMENT",
}

# Valid status transitions
OFFLINE_OP_TRANSITIONS: dict[str, list[str]] = {
    OfflineOperationStatus.PENDING: [
        OfflineOperationStatus.APPLIED,
        OfflineOperationStatus.FAILED,
        OfflineOperationStatus.REJECTED,
    ],
    OfflineOperationStatus.FAILED: [
        OfflineOperationStatus.PENDING,  # retry
        OfflineOperationStatus.REJECTED,
    ],
    OfflineOperationStatus.APPLIED: [],
    OfflineOperationStatus.REJECTED: [],
}
