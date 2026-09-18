"""Domain States, Enums, and State Transitions for Replanning and Approvals."""

from enum import Enum
from typing import Dict, List, Set


class ReplanStatus(str, Enum):
    """Lifecycle states for operational replanning workflows."""
    REQUESTED = "REQUESTED"
    ANALYZING = "ANALYZING"
    OPTIONS_READY = "OPTIONS_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecommendationStatus(str, Enum):
    """Lifecycle states for generated candidate recommendations."""
    PROPOSED = "PROPOSED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


class ApprovalDecision(str, Enum):
    """Formal decision outcomes rendered by an authorized human operator."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalStatus(str, Enum):
    """Lifecycle state of an approval request record."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class OptionFeasibility(str, Enum):
    """Deterministic constraint evaluation outcome for candidate options."""
    FEASIBLE = "FEASIBLE"
    CONSTRAINED = "CONSTRAINED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    INFEASIBLE = "INFEASIBLE"


class ReplanActionType(str, Enum):
    """Domain action types supported by deterministic candidate option generation."""
    MODIFY_TRANSPORT = "MODIFY_TRANSPORT"
    RESCHEDULE_MISSION = "RESCHEDULE_MISSION"
    REASSIGN_ASSET = "REASSIGN_ASSET"
    REASSIGN_PERSONNEL = "REASSIGN_PERSONNEL"
    ADJUST_CARGO_PLAN = "ADJUST_CARGO_PLAN"
    DEFER_ACTIVITY = "DEFER_ACTIVITY"
    SPLIT_ACTIVITY = "SPLIT_ACTIVITY"
    CANCEL_ACTIVITY = "CANCEL_ACTIVITY"


# Valid state transitions for replans
REPLAN_TRANSITIONS: Dict[ReplanStatus, List[ReplanStatus]] = {
    ReplanStatus.REQUESTED: [ReplanStatus.ANALYZING, ReplanStatus.OPTIONS_READY, ReplanStatus.CANCELLED],
    ReplanStatus.ANALYZING: [ReplanStatus.OPTIONS_READY, ReplanStatus.FAILED, ReplanStatus.CANCELLED],
    ReplanStatus.OPTIONS_READY: [ReplanStatus.AWAITING_APPROVAL, ReplanStatus.REJECTED, ReplanStatus.CANCELLED],
    ReplanStatus.AWAITING_APPROVAL: [ReplanStatus.APPROVED, ReplanStatus.REJECTED, ReplanStatus.CANCELLED],
    ReplanStatus.APPROVED: [ReplanStatus.APPLIED, ReplanStatus.FAILED],
    ReplanStatus.REJECTED: [],  # Terminal
    ReplanStatus.APPLIED: [],   # Terminal
    ReplanStatus.FAILED: [ReplanStatus.REQUESTED],  # Can be re-analyzed/re-requested
    ReplanStatus.CANCELLED: [], # Terminal
}

# Valid state transitions for recommendations
RECOMMENDATION_TRANSITIONS: Dict[RecommendationStatus, List[RecommendationStatus]] = {
    RecommendationStatus.PROPOSED: [RecommendationStatus.SELECTED, RecommendationStatus.REJECTED, RecommendationStatus.EXPIRED],
    RecommendationStatus.SELECTED: [RecommendationStatus.APPLIED, RecommendationStatus.FAILED, RecommendationStatus.REJECTED],
    RecommendationStatus.REJECTED: [],
    RecommendationStatus.EXPIRED: [],
    RecommendationStatus.APPLIED: [],
    RecommendationStatus.FAILED: [RecommendationStatus.PROPOSED],
}

# Valid state transitions for approvals
APPROVAL_TRANSITIONS: Dict[ApprovalStatus, List[ApprovalStatus]] = {
    ApprovalStatus.PENDING: [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.REVOKED],
    ApprovalStatus.APPROVED: [],  # Immutable once decided
    ApprovalStatus.REJECTED: [],  # Immutable once decided
    ApprovalStatus.REVOKED: [],
}

TERMINAL_REPLAN_STATUSES: Set[ReplanStatus] = {
    ReplanStatus.REJECTED,
    ReplanStatus.APPLIED,
    ReplanStatus.CANCELLED,
}
