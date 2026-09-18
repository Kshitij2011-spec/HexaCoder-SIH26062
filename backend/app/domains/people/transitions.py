"""Personnel Dual-State Lifecycle Transitions and Event Mapping."""

from typing import Dict, List
from backend.app.shared.types.states import PersonReadiness, PersonMovement
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_READINESS_TRANSITIONS: Dict[PersonReadiness, List[PersonReadiness]] = {
    PersonReadiness.NOMINATED: [PersonReadiness.CLEARANCE_PENDING, PersonReadiness.UNAVAILABLE],
    PersonReadiness.CLEARANCE_PENDING: [PersonReadiness.READY, PersonReadiness.NOT_CLEARED, PersonReadiness.UNAVAILABLE],
    PersonReadiness.READY: [PersonReadiness.CLEARANCE_PENDING, PersonReadiness.UNAVAILABLE],
    PersonReadiness.NOT_CLEARED: [PersonReadiness.CLEARANCE_PENDING, PersonReadiness.UNAVAILABLE],
    PersonReadiness.UNAVAILABLE: [PersonReadiness.NOMINATED, PersonReadiness.CLEARANCE_PENDING],
}

READINESS_EVENT_MAP: Dict[tuple, str] = {
    (PersonReadiness.NOMINATED, PersonReadiness.CLEARANCE_PENDING): "PersonClearancePending",
    (PersonReadiness.CLEARANCE_PENDING, PersonReadiness.READY): "PersonCleared",
    (PersonReadiness.CLEARANCE_PENDING, PersonReadiness.NOT_CLEARED): "PersonMedicalHold",
    (PersonReadiness.READY, PersonReadiness.UNAVAILABLE): "PersonUnavailable",
    (PersonReadiness.CLEARANCE_PENDING, PersonReadiness.UNAVAILABLE): "PersonUnavailable",
    (PersonReadiness.NOMINATED, PersonReadiness.UNAVAILABLE): "PersonUnavailable",
}

ALLOWED_MOVEMENT_TRANSITIONS: Dict[PersonMovement, List[PersonMovement]] = {
    PersonMovement.NOT_DEPLOYED: [PersonMovement.IN_TRANSIT],
    PersonMovement.IN_TRANSIT: [PersonMovement.AT_STATION, PersonMovement.NOT_DEPLOYED],
    PersonMovement.AT_STATION: [PersonMovement.FIELD, PersonMovement.RETURNING, PersonMovement.IN_TRANSIT],
    PersonMovement.FIELD: [PersonMovement.AT_STATION, PersonMovement.RETURNING],
    PersonMovement.RETURNING: [PersonMovement.AT_STATION, PersonMovement.RETURNED],
    PersonMovement.RETURNED: [PersonMovement.NOT_DEPLOYED, PersonMovement.IN_TRANSIT],
}

MOVEMENT_EVENT_MAP: Dict[tuple, str] = {
    (PersonMovement.NOT_DEPLOYED, PersonMovement.IN_TRANSIT): "PersonDeparted",
    (PersonMovement.IN_TRANSIT, PersonMovement.AT_STATION): "PersonArrived",
    (PersonMovement.AT_STATION, PersonMovement.FIELD): "PersonEnteredField",
    (PersonMovement.FIELD, PersonMovement.AT_STATION): "PersonArrived",
    (PersonMovement.AT_STATION, PersonMovement.RETURNING): "PersonReturning",
    (PersonMovement.FIELD, PersonMovement.RETURNING): "PersonReturning",
    (PersonMovement.RETURNING, PersonMovement.RETURNED): "PersonReturned",
}


def validate_readiness_transition(current_state: str, target_state: str) -> str:
    """Validates readiness qualification transition and returns canonical event name."""
    curr = PersonReadiness(current_state)
    tgt = PersonReadiness(target_state)

    if curr == tgt:
        return "PersonReadinessUpdated"

    allowed = ALLOWED_READINESS_TRANSITIONS.get(curr, [])
    if tgt not in allowed:
        raise InvalidStateTransitionError(
            entity_type="PersonReadiness",
            current_state=curr.value,
            target_state=tgt.value,
            allowed_transitions=[s.value for s in allowed]
        )

    return READINESS_EVENT_MAP.get((curr, tgt), "PersonReadinessChanged")


def validate_movement_transition(current_state: str, target_state: str) -> str:
    """Validates movement location transition and returns canonical event name."""
    curr = PersonMovement(current_state)
    tgt = PersonMovement(target_state)

    if curr == tgt:
        return "PersonMovementUpdated"

    allowed = ALLOWED_MOVEMENT_TRANSITIONS.get(curr, [])
    if tgt not in allowed:
        raise InvalidStateTransitionError(
            entity_type="PersonMovement",
            current_state=curr.value,
            target_state=tgt.value,
            allowed_transitions=[s.value for s in allowed]
        )

    return MOVEMENT_EVENT_MAP.get((curr, tgt), "PersonMovementChanged")
