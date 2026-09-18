"""Cargo Lifecycle State Machines and Transition Validation."""

from typing import Dict, Set
from backend.app.shared.types.states import CargoStatus, CargoPackageStatus
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_CONSIGNMENT_TRANSITIONS: Dict[CargoStatus, Set[CargoStatus]] = {
    CargoStatus.REQUESTED: {
        CargoStatus.REQUESTED,
        CargoStatus.DECLARED,
        CargoStatus.REJECTED,
    },
    CargoStatus.DECLARED: {
        CargoStatus.DECLARED,
        CargoStatus.APPROVED,
        CargoStatus.REJECTED,
    },
    CargoStatus.APPROVED: {
        CargoStatus.APPROVED,
        CargoStatus.PACKED,
        CargoStatus.READY,
        CargoStatus.REJECTED,
    },
    CargoStatus.PACKED: {
        CargoStatus.PACKED,
        CargoStatus.READY,
        CargoStatus.HELD,
    },
    CargoStatus.READY: {
        CargoStatus.READY,
        CargoStatus.DISPATCHED,
        CargoStatus.DELAYED,
        CargoStatus.HELD,
    },
    CargoStatus.DISPATCHED: {
        CargoStatus.DISPATCHED,
        CargoStatus.IN_TRANSIT,
        CargoStatus.DELAYED,
        CargoStatus.HELD,
    },
    CargoStatus.IN_TRANSIT: {
        CargoStatus.IN_TRANSIT,
        CargoStatus.ARRIVED,
        CargoStatus.DELAYED,
        CargoStatus.HELD,
        CargoStatus.DAMAGED,
        CargoStatus.LOST,
    },
    CargoStatus.DELAYED: {
        CargoStatus.DELAYED,
        CargoStatus.READY,
        CargoStatus.DISPATCHED,
        CargoStatus.IN_TRANSIT,
        CargoStatus.ARRIVED,
        CargoStatus.HELD,
        CargoStatus.LOST,
    },
    CargoStatus.HELD: {
        CargoStatus.HELD,
        CargoStatus.APPROVED,
        CargoStatus.PACKED,
        CargoStatus.READY,
        CargoStatus.DISPATCHED,
        CargoStatus.IN_TRANSIT,
        CargoStatus.REJECTED,
    },
    CargoStatus.ARRIVED: {
        CargoStatus.ARRIVED,
        CargoStatus.RECEIVED,
        CargoStatus.DAMAGED,
    },
    CargoStatus.RECEIVED: {
        CargoStatus.RECEIVED,
        CargoStatus.DAMAGED,
    },
    CargoStatus.DAMAGED: {CargoStatus.DAMAGED},
    CargoStatus.LOST: {CargoStatus.LOST},
    CargoStatus.REJECTED: {CargoStatus.REJECTED},
}

ALLOWED_PACKAGE_TRANSITIONS: Dict[CargoPackageStatus, Set[CargoPackageStatus]] = {
    CargoPackageStatus.PACKED: {
        CargoPackageStatus.PACKED,
        CargoPackageStatus.LOADED,
        CargoPackageStatus.HELD,
    },
    CargoPackageStatus.LOADED: {
        CargoPackageStatus.LOADED,
        CargoPackageStatus.IN_TRANSIT,
        CargoPackageStatus.PACKED,
        CargoPackageStatus.HELD,
    },
    CargoPackageStatus.IN_TRANSIT: {
        CargoPackageStatus.IN_TRANSIT,
        CargoPackageStatus.RECEIVED,
        CargoPackageStatus.HELD,
        CargoPackageStatus.DAMAGED,
        CargoPackageStatus.LOST,
    },
    CargoPackageStatus.RECEIVED: {
        CargoPackageStatus.RECEIVED,
        CargoPackageStatus.ISSUED,
        CargoPackageStatus.RETURNED,
        CargoPackageStatus.DAMAGED,
    },
    CargoPackageStatus.ISSUED: {
        CargoPackageStatus.ISSUED,
        CargoPackageStatus.RETURNED,
    },
    CargoPackageStatus.RETURNED: {
        CargoPackageStatus.RETURNED,
        CargoPackageStatus.RECEIVED,
    },
    CargoPackageStatus.HELD: {
        CargoPackageStatus.HELD,
        CargoPackageStatus.PACKED,
        CargoPackageStatus.LOADED,
        CargoPackageStatus.IN_TRANSIT,
    },
    CargoPackageStatus.DAMAGED: {CargoPackageStatus.DAMAGED},
    CargoPackageStatus.LOST: {CargoPackageStatus.LOST},
}


def validate_cargo_consignment_transition(current_state_str: str, target_state_str: str) -> None:
    """Validates consignment lifecycle state transitions."""
    try:
        current_state = CargoStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError("CargoConsignment", current_state_str, target_state_str, [])

    try:
        target_state = CargoStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_CONSIGNMENT_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError("CargoConsignment", current_state.value, target_state_str, allowed)

    allowed_targets = ALLOWED_CONSIGNMENT_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            "CargoConsignment",
            current_state.value,
            target_state.value,
            [s.value for s in allowed_targets]
        )


def validate_cargo_package_transition(current_state_str: str, target_state_str: str) -> None:
    """Validates individual package lifecycle state transitions."""
    try:
        current_state = CargoPackageStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError("CargoPackage", current_state_str, target_state_str, [])

    try:
        target_state = CargoPackageStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_PACKAGE_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError("CargoPackage", current_state.value, target_state_str, allowed)

    allowed_targets = ALLOWED_PACKAGE_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            "CargoPackage",
            current_state.value,
            target_state.value,
            [s.value for s in allowed_targets]
        )
