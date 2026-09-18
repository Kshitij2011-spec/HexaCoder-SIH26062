"""Location State Machine and Operational Transition Rules."""

from typing import Dict, List, Set
from backend.app.shared.types.states import LocationStatus
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_LOCATION_TRANSITIONS: Dict[LocationStatus, Set[LocationStatus]] = {
    LocationStatus.AVAILABLE: {
        LocationStatus.AVAILABLE,
        LocationStatus.RESTRICTED,
        LocationStatus.INACCESSIBLE,
        LocationStatus.CLOSED,
    },
    LocationStatus.RESTRICTED: {
        LocationStatus.RESTRICTED,
        LocationStatus.AVAILABLE,
        LocationStatus.INACCESSIBLE,
        LocationStatus.CLOSED,
    },
    LocationStatus.INACCESSIBLE: {
        LocationStatus.INACCESSIBLE,
        LocationStatus.RESTRICTED,
        LocationStatus.AVAILABLE,
        LocationStatus.CLOSED,
    },
    LocationStatus.CLOSED: {
        LocationStatus.CLOSED,
        LocationStatus.AVAILABLE,
        LocationStatus.RESTRICTED,
    },
}


def validate_location_transition(current_state_str: str, target_state_str: str) -> None:
    """
    Validates operational lifecycle state transitions for locations.
    Raises InvalidStateTransitionError if transition violates domain rules.
    """
    try:
        current_state = LocationStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError(
            entity_type="Location",
            current_state=current_state_str,
            target_state=target_state_str,
            allowed_transitions=[]
        )

    try:
        target_state = LocationStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_LOCATION_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError(
            entity_type="Location",
            current_state=current_state.value,
            target_state=target_state_str,
            allowed_transitions=allowed
        )

    allowed_targets = ALLOWED_LOCATION_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            entity_type="Location",
            current_state=current_state.value,
            target_state=target_state.value,
            allowed_transitions=[s.value for s in allowed_targets]
        )
