"""Inventory Stock Lot State Machine and Operational Transition Rules."""

from typing import Dict, Set
from backend.app.shared.types.states import InventoryStatus
from backend.app.core.errors import InvalidStateTransitionError

ALLOWED_INVENTORY_TRANSITIONS: Dict[InventoryStatus, Set[InventoryStatus]] = {
    InventoryStatus.ON_ORDER: {
        InventoryStatus.ON_ORDER,
        InventoryStatus.INBOUND,
        InventoryStatus.QUARANTINED,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.INBOUND: {
        InventoryStatus.INBOUND,
        InventoryStatus.AVAILABLE,
        InventoryStatus.QUARANTINED,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.AVAILABLE: {
        InventoryStatus.AVAILABLE,
        InventoryStatus.RESERVED,
        InventoryStatus.ISSUED,
        InventoryStatus.CONSUMED,
        InventoryStatus.TRANSFERRED,
        InventoryStatus.QUARANTINED,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.RESERVED: {
        InventoryStatus.RESERVED,
        InventoryStatus.AVAILABLE,
        InventoryStatus.ISSUED,
        InventoryStatus.CONSUMED,
        InventoryStatus.TRANSFERRED,
        InventoryStatus.QUARANTINED,
    },
    InventoryStatus.ISSUED: {
        InventoryStatus.ISSUED,
        InventoryStatus.CONSUMED,
        InventoryStatus.AVAILABLE,
        InventoryStatus.QUARANTINED,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.TRANSFERRED: {
        InventoryStatus.TRANSFERRED,
        InventoryStatus.INBOUND,
        InventoryStatus.AVAILABLE,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.QUARANTINED: {
        InventoryStatus.QUARANTINED,
        InventoryStatus.AVAILABLE,
        InventoryStatus.DISPOSED,
    },
    InventoryStatus.CONSUMED: {
        InventoryStatus.CONSUMED,
    },
    InventoryStatus.DISPOSED: {
        InventoryStatus.DISPOSED,
    },
}


def validate_inventory_transition(current_state_str: str, target_state_str: str) -> None:
    """
    Validates operational lifecycle state transitions for inventory stock lots.
    Raises InvalidStateTransitionError if transition violates domain rules.
    """
    try:
        current_state = InventoryStatus(current_state_str)
    except ValueError:
        raise InvalidStateTransitionError(
            entity_type="InventoryStockLot",
            current_state=current_state_str,
            target_state=target_state_str,
            allowed_transitions=[]
        )

    try:
        target_state = InventoryStatus(target_state_str)
    except ValueError:
        allowed = [s.value for s in ALLOWED_INVENTORY_TRANSITIONS.get(current_state, set())]
        raise InvalidStateTransitionError(
            entity_type="InventoryStockLot",
            current_state=current_state.value,
            target_state=target_state_str,
            allowed_transitions=allowed
        )

    allowed_targets = ALLOWED_INVENTORY_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            entity_type="InventoryStockLot",
            current_state=current_state.value,
            target_state=target_state.value,
            allowed_transitions=[s.value for s in allowed_targets]
        )
