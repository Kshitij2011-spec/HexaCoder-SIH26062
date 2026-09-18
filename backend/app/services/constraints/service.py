"""Constraint Service for Evaluating Operational Invariants."""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.services.constraints.models import ConstraintModel
from backend.app.services.constraints.repository import ConstraintRepository
from backend.app.services.constraints.schemas import (
    ConstraintEvaluationResult,
    EntityConstraintsSummary,
)
from backend.app.services.constraints.rules import RULE_REGISTRY, _parse_severity, _parse_hard_soft
from backend.app.shared.types.reasoning import (
    ConstraintState,
    ConstraintSeverity,
)
from backend.app.core.errors import EntityNotFoundError


class ConstraintService:
    """
    Evaluates operational constraints deterministically against current database state.
    Does NOT mutate primary state. Returns derived evaluation outcomes.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repository = ConstraintRepository(session)

    def get_constraint(self, constraint_id: uuid.UUID) -> ConstraintModel:
        c = self.repository.get_by_id(constraint_id)
        if not c:
            raise EntityNotFoundError("Constraint", constraint_id)
        return c

    def list_constraints(self, active_only: bool = True) -> List[ConstraintModel]:
        return self.repository.list_all(active_only=active_only)

    def evaluate_constraint(
        self,
        constraint: ConstraintModel,
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintEvaluationResult:
        """Dispatches constraint evaluation to verified rule evaluator in RULE_REGISTRY."""
        rule_fn = RULE_REGISTRY.get(constraint.rule_code)

        if not rule_fn:
            # Unsupported rule code
            return ConstraintEvaluationResult(
                constraint_id=constraint.id,
                code=constraint.code,
                name=constraint.name,
                severity=_parse_severity(constraint.severity),
                hard_or_soft=_parse_hard_soft(constraint.hard_or_soft),
                state=ConstraintState.NOT_EVALUABLE,
                subject_type=constraint.subject_type or "UNKNOWN",
                subject_id=constraint.subject_id or uuid.UUID(int=0),
                reason=f"No verified rule evaluator registered for rule_code '{constraint.rule_code}'.",
                evidence={"rule_code": constraint.rule_code}
            )

        return rule_fn(self.session, constraint, context)

    def evaluate_by_id(
        self,
        constraint_id: uuid.UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintEvaluationResult:
        constraint = self.get_constraint(constraint_id)
        return self.evaluate_constraint(constraint, context)

    def evaluate_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> EntityConstraintsSummary:
        """Evaluates all active constraints where subject matches the entity."""
        constraints = self.repository.get_for_subject(entity_type, entity_id, active_only=True)
        results = [self.evaluate_constraint(c, context) for c in constraints]

        satisfied = sum(1 for r in results if r.state == ConstraintState.SATISFIED)
        violated = sum(1 for r in results if r.state == ConstraintState.VIOLATED)
        not_evaluable = sum(1 for r in results if r.state == ConstraintState.NOT_EVALUABLE)

        return EntityConstraintsSummary(
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            total_evaluated=len(results),
            satisfied_count=satisfied,
            violated_count=violated,
            not_evaluable_count=not_evaluable,
            results=results
        )

    def evaluate_all(
        self,
        active_only: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ConstraintEvaluationResult]:
        """Evaluates all active constraints in the platform."""
        constraints = self.repository.list_all(active_only=active_only)
        return [self.evaluate_constraint(c, context) for c in constraints]
