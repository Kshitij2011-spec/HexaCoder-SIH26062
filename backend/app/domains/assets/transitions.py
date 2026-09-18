"""State Machine and Transition Validation for Assets and Maintenance."""

from typing import Dict, Set
from backend.app.domains.assets.states import AssetStatus, MaintenanceStatus
from backend.app.core.errors import InvalidStateTransitionError

# ============================================================
# 1. ASSET STATE MACHINE
# ============================================================

ALLOWED_ASSET_TRANSITIONS: Dict[AssetStatus, Set[AssetStatus]] = {
    AssetStatus.AVAILABLE: {
        AssetStatus.AVAILABLE,
        AssetStatus.RESERVED,
        AssetStatus.IN_USE,
        AssetStatus.MAINTENANCE,
        AssetStatus.QUARANTINED,
        AssetStatus.RETIRED,
    },
    AssetStatus.RESERVED: {
        AssetStatus.RESERVED,
        AssetStatus.AVAILABLE,
        AssetStatus.IN_USE,
        AssetStatus.QUARANTINED,
        AssetStatus.RETIRED,
    },
    AssetStatus.IN_USE: {
        AssetStatus.IN_USE,
        AssetStatus.AVAILABLE,
        AssetStatus.MAINTENANCE,
        AssetStatus.QUARANTINED,
        AssetStatus.RETIRED,
    },
    AssetStatus.MAINTENANCE: {
        AssetStatus.MAINTENANCE,
        AssetStatus.AVAILABLE,
        AssetStatus.QUARANTINED,
        AssetStatus.RETIRED,
    },
    AssetStatus.QUARANTINED: {
        AssetStatus.QUARANTINED,
        AssetStatus.AVAILABLE,
        AssetStatus.MAINTENANCE,
        AssetStatus.RETIRED,
    },
    AssetStatus.RETIRED: set(),  # Strictly terminal
}


def validate_asset_transition(current_state_str: str, target_state_str: str) -> None:
    """
    Validates operational lifecycle state transitions for assets.
    Raises InvalidStateTransitionError if transition is invalid.
    """
    try:
        current_state = AssetStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError(
            entity_type="Asset",
            current_state=current_state_str,
            target_state=target_state_str,
            allowed_transitions=[]
        )

    try:
        target_state = AssetStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_ASSET_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError(
            entity_type="Asset",
            current_state=current_state.value,
            target_state=target_state_str,
            allowed_transitions=allowed
        )

    allowed_targets = ALLOWED_ASSET_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            entity_type="Asset",
            current_state=current_state.value,
            target_state=target_state.value,
            allowed_transitions=[s.value for s in allowed_targets]
        )


# ============================================================
# 2. MAINTENANCE STATE MACHINE
# ============================================================

ALLOWED_MAINTENANCE_TRANSITIONS: Dict[MaintenanceStatus, Set[MaintenanceStatus]] = {
    MaintenanceStatus.SCHEDULED: {
        MaintenanceStatus.SCHEDULED,
        MaintenanceStatus.IN_PROGRESS,
        MaintenanceStatus.CANCELLED,
        MaintenanceStatus.OVERDUE,
    },
    MaintenanceStatus.IN_PROGRESS: {
        MaintenanceStatus.IN_PROGRESS,
        MaintenanceStatus.COMPLETED,
        MaintenanceStatus.CANCELLED,
    },
    MaintenanceStatus.OVERDUE: {
        MaintenanceStatus.OVERDUE,
        MaintenanceStatus.IN_PROGRESS,
        MaintenanceStatus.CANCELLED,
    },
    MaintenanceStatus.COMPLETED: set(),  # Terminal
    MaintenanceStatus.CANCELLED: set(),  # Terminal
}


def validate_maintenance_transition(current_state_str: str, target_state_str: str) -> None:
    """
    Validates lifecycle state transitions for maintenance records.
    Raises InvalidStateTransitionError if transition is invalid.
    """
    try:
        current_state = MaintenanceStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError(
            entity_type="MaintenanceRecord",
            current_state=current_state_str,
            target_state=target_state_str,
            allowed_transitions=[]
        )

    try:
        target_state = MaintenanceStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_MAINTENANCE_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError(
            entity_type="MaintenanceRecord",
            current_state=current_state.value,
            target_state=target_state_str,
            allowed_transitions=allowed
        )

    allowed_targets = ALLOWED_MAINTENANCE_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            entity_type="MaintenanceRecord",
            current_state=current_state.value,
            target_state=target_state.value,
            allowed_transitions=[s.value for s in allowed_targets]
        )
