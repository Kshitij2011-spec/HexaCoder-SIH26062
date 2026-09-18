"""Incident State Machine and Transition Enforcement."""

from typing import Dict, Set

from backend.app.core.errors import InvalidStateTransitionError
from backend.app.domains.incidents.states import IncidentStatus

# Explicit allowable lifecycle state transitions
INCIDENT_ALLOWED_TRANSITIONS: Dict[IncidentStatus, Set[IncidentStatus]] = {
    IncidentStatus.OPEN: {
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.ACKNOWLEDGED: {
        IncidentStatus.MITIGATING,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.MITIGATING: {
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.CLOSED,
    },
    IncidentStatus.CLOSED: set(),  # Terminal state
}

TERMINAL_INCIDENT_STATUSES: Set[IncidentStatus] = {
    IncidentStatus.CLOSED,
}


def is_terminal_incident_status(status: IncidentStatus) -> bool:
    """Check if the given incident status is terminal."""
    return status in TERMINAL_INCIDENT_STATUSES


def validate_incident_transition(
    current_status: IncidentStatus,
    target_status: IncidentStatus,
) -> None:
    """
    Validate that an incident can legally transition from current_status to target_status.
    Raises InvalidStateTransitionError if the transition is illegal or the incident is closed.
    """
    if current_status == target_status:
        return

    if is_terminal_incident_status(current_status):
        raise InvalidStateTransitionError(
            entity_type="Incident",
            current_state=current_status.value,
            target_state=target_status.value,
            allowed_transitions=[],
        )

    allowed = INCIDENT_ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            entity_type="Incident",
            current_state=current_status.value,
            target_state=target_status.value,
            allowed_transitions=[s.value for s in allowed],
        )
