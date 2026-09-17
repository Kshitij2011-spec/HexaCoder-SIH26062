"""Mission Lifecycle State Transition Rules and Event Mapping."""

from typing import Dict, List
from backend.app.shared.types.states import MissionStatus
from backend.app.core.errors import InvalidStateTransitionError

# Authoritative transition graph defining legal operational states for missions
ALLOWED_MISSION_TRANSITIONS: Dict[MissionStatus, List[MissionStatus]] = {
    MissionStatus.PROPOSED: [MissionStatus.APPROVED, MissionStatus.CANCELLED],
    MissionStatus.APPROVED: [MissionStatus.READY, MissionStatus.BLOCKED, MissionStatus.DEFERRED, MissionStatus.CANCELLED],
    MissionStatus.READY: [MissionStatus.SCHEDULED, MissionStatus.BLOCKED, MissionStatus.DEFERRED, MissionStatus.CANCELLED],
    MissionStatus.SCHEDULED: [MissionStatus.IN_PROGRESS, MissionStatus.BLOCKED, MissionStatus.DEFERRED, MissionStatus.CANCELLED],
    MissionStatus.IN_PROGRESS: [MissionStatus.COMPLETED, MissionStatus.BLOCKED, MissionStatus.CANCELLED],
    MissionStatus.BLOCKED: [MissionStatus.READY, MissionStatus.SCHEDULED, MissionStatus.CANCELLED],
    MissionStatus.DEFERRED: [MissionStatus.APPROVED, MissionStatus.READY, MissionStatus.CANCELLED],
    MissionStatus.COMPLETED: [],  # Terminal state
    MissionStatus.CANCELLED: [],  # Terminal state
}

MISSION_EVENT_MAP: Dict[tuple, str] = {
    (MissionStatus.PROPOSED, MissionStatus.APPROVED): "MissionApproved",
    (MissionStatus.APPROVED, MissionStatus.READY): "MissionReady",
    (MissionStatus.APPROVED, MissionStatus.BLOCKED): "MissionBlocked",
    (MissionStatus.READY, MissionStatus.SCHEDULED): "MissionScheduled",
    (MissionStatus.SCHEDULED, MissionStatus.IN_PROGRESS): "MissionStarted",
    (MissionStatus.IN_PROGRESS, MissionStatus.COMPLETED): "MissionCompleted",
    (MissionStatus.READY, MissionStatus.BLOCKED): "MissionBlocked",
    (MissionStatus.SCHEDULED, MissionStatus.BLOCKED): "MissionBlocked",
    (MissionStatus.IN_PROGRESS, MissionStatus.BLOCKED): "MissionBlocked",
    (MissionStatus.APPROVED, MissionStatus.DEFERRED): "MissionDeferred",
    (MissionStatus.READY, MissionStatus.DEFERRED): "MissionDeferred",
    (MissionStatus.SCHEDULED, MissionStatus.DEFERRED): "MissionDeferred",
    (MissionStatus.PROPOSED, MissionStatus.CANCELLED): "MissionCancelled",
    (MissionStatus.APPROVED, MissionStatus.CANCELLED): "MissionCancelled",
    (MissionStatus.READY, MissionStatus.CANCELLED): "MissionCancelled",
    (MissionStatus.SCHEDULED, MissionStatus.CANCELLED): "MissionCancelled",
    (MissionStatus.BLOCKED, MissionStatus.CANCELLED): "MissionCancelled",
}


def validate_mission_transition(current_status: str, target_status: str) -> str:
    """
    Validates if transitioning from current_status to target_status is permitted.
    Returns canonical event type if valid, or raises InvalidStateTransitionError.
    """
    curr = MissionStatus(current_status)
    tgt = MissionStatus(target_status)

    if curr == tgt:
        return "MissionUpdated"

    allowed = ALLOWED_MISSION_TRANSITIONS.get(curr, [])
    if tgt not in allowed:
        raise InvalidStateTransitionError(
            entity_type="Mission",
            current_state=curr.value,
            target_state=tgt.value,
            allowed_transitions=[s.value for s in allowed]
        )

    return MISSION_EVENT_MAP.get((curr, tgt), "MissionStatusChanged")
