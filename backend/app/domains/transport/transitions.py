"""Transport Leg Lifecycle State Machine and Transition Validation."""

from typing import Dict, Set
from backend.app.shared.types.states import TransportStatus
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_TRANSPORT_TRANSITIONS: Dict[TransportStatus, Set[TransportStatus]] = {
    TransportStatus.PLANNED: {
        TransportStatus.PLANNED,
        TransportStatus.BOOKED,
        TransportStatus.CANCELLED,
    },
    TransportStatus.BOOKED: {
        TransportStatus.BOOKED,
        TransportStatus.READY,
        TransportStatus.DELAYED,
        TransportStatus.CANCELLED,
    },
    TransportStatus.READY: {
        TransportStatus.READY,
        TransportStatus.DEPARTED,
        TransportStatus.DELAYED,
        TransportStatus.CANCELLED,
    },
    TransportStatus.DEPARTED: {
        TransportStatus.DEPARTED,
        TransportStatus.IN_TRANSIT,
        TransportStatus.DELAYED,
        TransportStatus.DIVERTED,
    },
    TransportStatus.IN_TRANSIT: {
        TransportStatus.IN_TRANSIT,
        TransportStatus.ARRIVED,
        TransportStatus.DELAYED,
        TransportStatus.DIVERTED,
    },
    TransportStatus.DELAYED: {
        TransportStatus.DELAYED,
        TransportStatus.READY,
        TransportStatus.DEPARTED,
        TransportStatus.IN_TRANSIT,
        TransportStatus.ARRIVED,
        TransportStatus.DIVERTED,
        TransportStatus.CANCELLED,
    },
    TransportStatus.DIVERTED: {
        TransportStatus.DIVERTED,
        TransportStatus.ARRIVED,
        TransportStatus.DELAYED,
        TransportStatus.CANCELLED,
    },
    TransportStatus.ARRIVED: {
        TransportStatus.ARRIVED,
        TransportStatus.CLOSED,
    },
    TransportStatus.CLOSED: {TransportStatus.CLOSED},
    TransportStatus.CANCELLED: {TransportStatus.CANCELLED},
}


def validate_transport_transition(current_state_str: str, target_state_str: str) -> None:
    """Validates transport leg lifecycle state transitions, including direct transitions to DELAYED."""
    try:
        current_state = TransportStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError("TransportLeg", current_state_str, target_state_str, [])

    try:
        target_state = TransportStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_TRANSPORT_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError("TransportLeg", current_state.value, target_state_str, allowed)

    allowed_targets = ALLOWED_TRANSPORT_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            "TransportLeg",
            current_state.value,
            target_state.value,
            [s.value for s in allowed_targets]
        )
