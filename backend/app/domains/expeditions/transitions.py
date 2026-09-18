"""Expedition Lifecycle State Transition Rules and Event Mapping."""

from typing import Dict, List, Optional
from backend.app.shared.types.states import ExpeditionStatus
from backend.app.core.errors import InvalidStateTransitionError

# Authoritative transition map defining legal next states for an expedition
ALLOWED_EXPEDITION_TRANSITIONS: Dict[ExpeditionStatus, List[ExpeditionStatus]] = {
    ExpeditionStatus.DRAFT: [ExpeditionStatus.PLANNED],
    ExpeditionStatus.PLANNED: [ExpeditionStatus.MOBILIZATION, ExpeditionStatus.ON_HOLD],
    ExpeditionStatus.MOBILIZATION: [ExpeditionStatus.ACTIVE, ExpeditionStatus.PLANNED, ExpeditionStatus.ON_HOLD],
    ExpeditionStatus.ACTIVE: [ExpeditionStatus.CLOSEOUT, ExpeditionStatus.ON_HOLD],
    ExpeditionStatus.ON_HOLD: [
        ExpeditionStatus.PLANNED,
        ExpeditionStatus.MOBILIZATION,
        ExpeditionStatus.ACTIVE,
        ExpeditionStatus.ARCHIVED,
    ],
    ExpeditionStatus.CLOSEOUT: [ExpeditionStatus.ARCHIVED],
    ExpeditionStatus.ARCHIVED: [],
}

# Mapping of transitions to canonical operational event types
EXPEDITION_EVENT_MAP: Dict[tuple, str] = {
    (ExpeditionStatus.DRAFT, ExpeditionStatus.PLANNED): "ExpeditionPlanned",
    (ExpeditionStatus.PLANNED, ExpeditionStatus.MOBILIZATION): "ExpeditionMobilized",
    (ExpeditionStatus.MOBILIZATION, ExpeditionStatus.ACTIVE): "ExpeditionActivated",
    (ExpeditionStatus.ACTIVE, ExpeditionStatus.CLOSEOUT): "ExpeditionClosed",
    (ExpeditionStatus.CLOSEOUT, ExpeditionStatus.ARCHIVED): "ExpeditionArchived",
    (ExpeditionStatus.PLANNED, ExpeditionStatus.ON_HOLD): "ExpeditionHoldDeclared",
    (ExpeditionStatus.MOBILIZATION, ExpeditionStatus.ON_HOLD): "ExpeditionHoldDeclared",
    (ExpeditionStatus.ACTIVE, ExpeditionStatus.ON_HOLD): "ExpeditionHoldDeclared",
}


def validate_expedition_transition(current_status: str, target_status: str) -> str:
    """
    Validates if transitioning from current_status to target_status is permitted.
    Returns canonical event type if valid, or raises InvalidStateTransitionError.
    """
    curr = ExpeditionStatus(current_status)
    tgt = ExpeditionStatus(target_status)

    if curr == tgt:
        return "ExpeditionUpdated"

    allowed = ALLOWED_EXPEDITION_TRANSITIONS.get(curr, [])
    if tgt not in allowed:
        raise InvalidStateTransitionError(
            entity_type="Expedition",
            current_state=curr.value,
            target_state=tgt.value,
            allowed_transitions=[s.value for s in allowed]
        )

    return EXPEDITION_EVENT_MAP.get((curr, tgt), "ExpeditionStatusChanged")
