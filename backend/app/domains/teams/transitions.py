"""Team Lifecycle Transitions and Event Mapping."""

from typing import Dict, List
from backend.app.shared.types.states import TeamStatus
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_TEAM_TRANSITIONS: Dict[TeamStatus, List[TeamStatus]] = {
    TeamStatus.FORMING: [TeamStatus.READY],
    TeamStatus.READY: [TeamStatus.DEPLOYED, TeamStatus.FORMING],
    TeamStatus.DEPLOYED: [TeamStatus.FIELD, TeamStatus.RETURNED, TeamStatus.READY],
    TeamStatus.FIELD: [TeamStatus.DEPLOYED, TeamStatus.RETURNED],
    TeamStatus.RETURNED: [TeamStatus.FORMING, TeamStatus.READY],
}

TEAM_EVENT_MAP: Dict[tuple, str] = {
    (TeamStatus.FORMING, TeamStatus.READY): "TeamReady",
    (TeamStatus.READY, TeamStatus.DEPLOYED): "TeamDeployed",
    (TeamStatus.READY, TeamStatus.FORMING): "TeamReorganizing",
    (TeamStatus.DEPLOYED, TeamStatus.FIELD): "TeamEnteredField",
    (TeamStatus.DEPLOYED, TeamStatus.RETURNED): "TeamReturned",
    (TeamStatus.FIELD, TeamStatus.RETURNED): "TeamReturned",
    (TeamStatus.FIELD, TeamStatus.DEPLOYED): "TeamBaseReturned",
    (TeamStatus.RETURNED, TeamStatus.READY): "TeamReactivated",
    (TeamStatus.RETURNED, TeamStatus.FORMING): "TeamDisbanding",
}


def validate_team_transition(current_state: str, target_state: str) -> str:
    """Validates team status transition and returns canonical event name."""
    curr = TeamStatus(current_state)
    tgt = TeamStatus(target_state)

    if curr == tgt:
        return "TeamStatusUpdated"

    allowed = ALLOWED_TEAM_TRANSITIONS.get(curr, [])
    if tgt not in allowed:
        raise InvalidStateTransitionError(
            entity_type="Team",
            current_state=curr.value,
            target_state=tgt.value,
            allowed_transitions=[s.value for s in allowed]
        )

    return TEAM_EVENT_MAP.get((curr, tgt), "TeamStatusChanged")
