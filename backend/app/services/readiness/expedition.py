"""Deterministic Expedition Campaign Readiness Service."""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from backend.app.domains.expeditions.repository import ExpeditionRepository
from backend.app.domains.missions.models import MissionModel
from backend.app.services.readiness.mission import MissionReadinessService
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.readiness.schemas import (
    ExpeditionReadinessResult,
    MissionReadinessResult,
    BlockerItem,
    WarningItem,
    UnknownRequirement,
)
from backend.app.shared.types.reasoning import (
    ReadinessState,
    ConstraintState,
)
from backend.app.shared.types.states import HardSoftConstraint
from backend.app.core.errors import EntityNotFoundError


class ExpeditionReadinessService:
    """
    Evaluates campaign-wide operational readiness for an entire polar expedition.
    Rolls up underlying mission readiness results and evaluates expedition-level constraints.
    """

    def __init__(self, session: Session):
        self.session = session
        self.expedition_repo = ExpeditionRepository(session)
        self.mission_readiness_service = MissionReadinessService(session)
        self.constraint_service = ConstraintService(session)

    def evaluate(self, expedition_id: uuid.UUID) -> ExpeditionReadinessResult:
        """Evaluates expedition readiness derived from its missions and global constraints."""
        expedition = self.expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise EntityNotFoundError("Expedition", expedition_id)

        # 1. Fetch all missions for this expedition
        missions = self.session.execute(
            select(MissionModel).where(MissionModel.expedition_id == expedition_id).order_by(MissionModel.code.asc())
        ).scalars().all()

        mission_summaries: List[MissionReadinessResult] = []
        blockers: List[BlockerItem] = []
        warnings: List[WarningItem] = []
        unknowns: List[UnknownRequirement] = []

        ready_count = 0
        at_risk_count = 0
        blocked_count = 0

        for m in missions:
            res = self.mission_readiness_service.evaluate(m.id)
            mission_summaries.append(res)

            if res.state == ReadinessState.BLOCKED:
                blocked_count += 1
                for b in res.blockers:
                    blockers.append(b)
            elif res.state == ReadinessState.AT_RISK:
                at_risk_count += 1
                for w in res.warnings:
                    warnings.append(w)
            else:
                ready_count += 1

            for u in res.unknown_requirements:
                if u not in unknowns:
                    unknowns.append(u)

        # 2. Evaluate Expedition-Level Constraints
        exp_constraints = self.constraint_service.evaluate_for_entity("EXPEDITION", expedition_id)
        for cr in exp_constraints.results:
            if cr.state == ConstraintState.VIOLATED:
                if cr.hard_or_soft == HardSoftConstraint.HARD:
                    blockers.append(
                        BlockerItem(
                            type="EXPEDITION_CONSTRAINT",
                            entity_type="EXPEDITION",
                            entity_id=expedition_id,
                            entity_code=expedition.code,
                            reason=f"Expedition hard constraint '{cr.code}' violated: {cr.reason}",
                            evidence=cr.evidence
                        )
                    )
                else:
                    warnings.append(
                        WarningItem(
                            type="EXPEDITION_CONSTRAINT",
                            entity_type="EXPEDITION",
                            entity_id=expedition_id,
                            entity_code=expedition.code,
                            reason=f"Expedition soft constraint '{cr.code}' breached: {cr.reason}",
                            evidence=cr.evidence
                        )
                    )
            elif cr.state == ConstraintState.NOT_EVALUABLE:
                unknowns.append(
                    UnknownRequirement(
                        category="EXPEDITION_CONSTRAINT",
                        description=f"Expedition constraint '{cr.code}' unevaluable",
                        reason=cr.reason,
                        status="PENDING_TRACK_B"
                    )
                )

        # 3. Determine Overall State & Construct Explanation
        if blocked_count > 0 or any(b.type == "EXPEDITION_CONSTRAINT" for b in blockers):
            overall_state = ReadinessState.BLOCKED
            reasons = []
            if blocked_count > 0:
                blocked_codes = [m.mission_code for m in mission_summaries if m.state == ReadinessState.BLOCKED]
                reasons.append(f"{blocked_count} mission(s) BLOCKED ({', '.join(blocked_codes)})")
            exp_viol = [b.reason for b in blockers if b.type == "EXPEDITION_CONSTRAINT"]
            if exp_viol:
                reasons.append(f"Expedition hard constraints violated: {'; '.join(exp_viol)}")
            explanation = f"Expedition {expedition.code} is BLOCKED because: {'; '.join(reasons)}."
        elif at_risk_count > 0 or any(w.type == "EXPEDITION_CONSTRAINT" for w in warnings) or len(unknowns) > 0:
            overall_state = ReadinessState.AT_RISK
            reasons = []
            if at_risk_count > 0:
                at_risk_codes = [m.mission_code for m in mission_summaries if m.state == ReadinessState.AT_RISK]
                reasons.append(f"{at_risk_count} mission(s) AT_RISK ({', '.join(at_risk_codes)})")
            exp_warns = [w.reason for w in warnings if w.type == "EXPEDITION_CONSTRAINT"]
            if exp_warns:
                reasons.append(f"Expedition soft warnings: {'; '.join(exp_warns)}")
            if unknowns:
                reasons.append(f"{len(unknowns)} required constraint(s) unevaluable pending Track B data")
            explanation = f"Expedition {expedition.code} is AT_RISK because: {'; '.join(reasons)}."
        else:
            overall_state = ReadinessState.READY
            explanation = f"Expedition {expedition.code} is READY. All {len(missions)} mission(s) and expedition constraints are satisfied."

        return ExpeditionReadinessResult(
            expedition_id=expedition_id,
            expedition_code=expedition.code,
            state=overall_state,
            total_missions=len(missions),
            ready_missions=ready_count,
            at_risk_missions=at_risk_count,
            blocked_missions=blocked_count,
            mission_summaries=mission_summaries,
            blockers=blockers,
            warnings=warnings,
            unknown_requirements=unknowns,
            explanation=explanation
        )
