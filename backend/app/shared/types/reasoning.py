"""Shared Reasoning Enums and Vocabulary conforming to docs/DEPENDENCY_CONTRACT.md."""

from enum import Enum


class DependencyRelationship(str, Enum):
    """
    Canonical 15 semantic dependency relationships.
    No synonyms or unapproved types allowed.
    """
    REQUIRES = "REQUIRES"
    SUPPORTS = "SUPPORTS"
    ASSIGNED_TO = "ASSIGNED_TO"
    LOCATED_AT = "LOCATED_AT"
    MOVES_VIA = "MOVES_VIA"
    CONTAINS = "CONTAINS"
    DELIVERED_TO = "DELIVERED_TO"
    RESERVED_FOR = "RESERVED_FOR"
    REPLENISHED_BY = "REPLENISHED_BY"
    AFFECTS = "AFFECTS"
    DEPENDS_ON = "DEPENDS_ON"
    CONSTRAINED_BY = "CONSTRAINED_BY"
    OPERATED_BY = "OPERATED_BY"
    OCCURS_AT = "OCCURS_AT"
    BELONGS_TO = "BELONGS_TO"


class ConstraintSeverity(str, Enum):
    """Severity classification for operational constraints."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ConstraintState(str, Enum):
    """Deterministic evaluation outcome for operational constraints."""
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ReadinessState(str, Enum):
    """Operational readiness classification for missions and expeditions."""
    READY = "READY"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"


class TraversalDirection(str, Enum):
    """Direction for dependency graph navigation."""
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"
