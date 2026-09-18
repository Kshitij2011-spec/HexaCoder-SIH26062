"""Deterministic Mission Readiness Service."""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from backend.app.domains.missions.repository import MissionRepository
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.people.models import PersonModel
from backend.app.domains.time_windows.models import TimeWindowModel
from backend.app.services.dependencies.service import DependencyService
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.readiness.schemas import (
    MissionReadinessResult,
    BlockerItem,
    WarningItem,
    SatisfiedRequirement,
    UnknownRequirement,
)
from backend.app.shared.types.reasoning import (
    ReadinessState,
    ConstraintState,
)
from backend.app.shared.types.states import HardSoftConstraint
from backend.app.core.errors import EntityNotFoundError


class MissionReadinessService:
    """
    Evaluates multi-dimensional operational readiness for polar missions.
    Derives readiness state (READY, AT_RISK, BLOCKED) from verified domain facts
    across personnel, assets, logistics, temporal windows, and constraints.
    """

    def __init__(self, session: Session):
        self.session = session
        self.mission_repo = MissionRepository(session)
        self.dependency_service = DependencyService(session)
        self.constraint_service = ConstraintService(session)

    def evaluate(self, mission_id: uuid.UUID) -> MissionReadinessResult:
        """Deterministically evaluates mission readiness without mutating primary records."""
        mission = self.mission_repo.get_by_id(mission_id)
        if not mission:
            raise EntityNotFoundError("Mission", mission_id)

        blockers: List[BlockerItem] = []
        warnings: List[WarningItem] = []
        satisfied: List[SatisfiedRequirement] = []
        unknowns: List[UnknownRequirement] = []

        # 1. Personnel & Team Readiness Evaluation
        self._evaluate_personnel(mission_id, blockers, warnings, satisfied, unknowns)

        # 2. Equipment & Asset Readiness Evaluation
        self._evaluate_assets(mission_id, blockers, warnings, satisfied, unknowns)

        # 3. Time Window Evaluation
        self._evaluate_time_windows(mission_id, blockers, warnings, satisfied, unknowns)

        # 4. Operational Constraints Evaluation
        constraint_summary = self.constraint_service.evaluate_for_entity("MISSION", mission_id)
        violated_constraints = []

        for cr in constraint_summary.results:
            if cr.state == ConstraintState.VIOLATED:
                violated_constraints.append(cr)
                if cr.hard_or_soft == HardSoftConstraint.HARD:
                    blockers.append(
                        BlockerItem(
                            type="CONSTRAINT",
                            entity_type="MISSION",
                            entity_id=mission_id,
                            entity_code=mission.code,
                            reason=f"Hard constraint '{cr.code}' ({cr.name}) violated: {cr.reason}",
                            evidence=cr.evidence
                        )
                    )
                else:
                    warnings.append(
                        WarningItem(
                            type="CONSTRAINT",
                            entity_type="MISSION",
                            entity_id=mission_id,
                            entity_code=mission.code,
                            reason=f"Soft constraint '{cr.code}' breached: {cr.reason}",
                            evidence=cr.evidence
                        )
                    )
            elif cr.state == ConstraintState.SATISFIED:
                satisfied.append(
                    SatisfiedRequirement(
                        category="CONSTRAINT",
                        description=f"Constraint '{cr.code}' satisfied: {cr.reason}",
                        entity_type="MISSION",
                        entity_id=mission_id,
                        evidence=cr.evidence
                    )
                )
            elif cr.state == ConstraintState.NOT_EVALUABLE:
                unknowns.append(
                    UnknownRequirement(
                        category="CONSTRAINT",
                        description=f"Constraint '{cr.code}' ({cr.name}) currently unevaluable",
                        reason=cr.reason,
                        status="PENDING_TRACK_B"
                    )
                )

        # 5. Synthesize Operational Readiness State
        # Hard blockers take precedence -> BLOCKED
        # Soft warnings -> AT_RISK
        # Unevaluable / missing evidence -> AT_RISK (never reported as READY)
        # Only fully satisfied requirements with zero unknowns -> READY
        if blockers:
            overall_state = ReadinessState.BLOCKED
        elif warnings:
            overall_state = ReadinessState.AT_RISK
        elif unknowns:
            overall_state = ReadinessState.AT_RISK
        else:
            overall_state = ReadinessState.READY

        return MissionReadinessResult(
            mission_id=mission_id,
            mission_code=mission.code,
            state=overall_state,
            blockers=blockers,
            warnings=warnings,
            satisfied_requirements=satisfied,
            unknown_requirements=unknowns,
            constraints_evaluated=constraint_summary.total_evaluated,
            violated_constraints=violated_constraints,
            evidence={
                "mission_status": mission.status,
                "required_by_at": mission.required_by_at.isoformat() if mission.required_by_at else None,
                "priority": mission.priority,
            }
        )

    def _evaluate_personnel(
        self,
        mission_id: uuid.UUID,
        blockers: List[BlockerItem],
        warnings: List[WarningItem],
        satisfied: List[SatisfiedRequirement],
        unknowns: List[UnknownRequirement]
    ) -> None:
        """Evaluates assigned teams and personnel readiness."""
        # Find team dependencies
        team_deps = self.dependency_service.get_outgoing_dependencies(
            entity_type="MISSION",
            entity_id=mission_id,
            relationship_type="REQUIRES"
        )
        assigned_teams = [d for d in team_deps if d.target_entity_type == "TEAM"]

        # Also check incoming ASSIGNED_TO from TEAM
        incoming_teams = self.dependency_service.get_incoming_dependencies(
            entity_type="MISSION",
            entity_id=mission_id,
            relationship_type="ASSIGNED_TO"
        )
        for it in incoming_teams:
            if it.source_entity_type == "TEAM" and it not in assigned_teams:
                assigned_teams.append(it)

        if not assigned_teams:
            # Check if mission requires a team
            satisfied.append(
                SatisfiedRequirement(
                    category="PERSONNEL",
                    description="No mandatory dedicated team requirements declared for mission.",
                    evidence={}
                )
            )
            return

        for td in assigned_teams:
            team_id = td.target_entity_id if td.target_entity_type == "TEAM" else td.source_entity_id
            team = self.session.execute(select(TeamModel).where(TeamModel.id == team_id)).scalar_one_or_none()

            if not team:
                unknowns.append(
                    UnknownRequirement(
                        category="PERSONNEL",
                        description=f"Assigned team {team_id} record not located in database.",
                        reason="Missing team entity.",
                        status="DATA_GAP"
                    )
                )
                continue

            if team.status == "DISBANDED":
                blockers.append(
                    BlockerItem(
                        type="PERSONNEL",
                        entity_type="TEAM",
                        entity_id=team_id,
                        entity_code=team.code,
                        reason=f"Assigned field team '{team.code}' is DISBANDED.",
                        evidence={"team_status": team.status}
                    )
                )
                continue

            # Query members
            members = self.session.execute(
                select(PersonModel).where(PersonModel.team_id == team_id)
            ).scalars().all()

            if not members:
                warnings.append(
                    WarningItem(
                        type="PERSONNEL",
                        entity_type="TEAM",
                        entity_id=team_id,
                        entity_code=team.code,
                        reason=f"Field team '{team.code}' has zero assigned personnel.",
                        evidence={"team_status": team.status}
                    )
                )
            else:
                unready = [m for m in members if m.readiness_state in ("UNAVAILABLE", "NOT_CLEARED")]
                if unready:
                    blockers.append(
                        BlockerItem(
                            type="PERSONNEL",
                            entity_type="TEAM",
                            entity_id=team_id,
                            entity_code=team.code,
                            reason=f"Team member '{unready[0].person_code}' is in state '{unready[0].readiness_state}'.",
                            evidence={"unready_members": [{"person_code": u.person_code, "readiness_state": u.readiness_state} for u in unready]}
                        )
                    )
                else:
                    satisfied.append(
                        SatisfiedRequirement(
                            category="PERSONNEL",
                            description=f"Team '{team.code}' has {len(members)} qualified personnel cleared for operations.",
                            entity_type="TEAM",
                            entity_id=team_id,
                            evidence={"member_count": len(members)}
                        )
                    )

    def _evaluate_assets(
        self,
        mission_id: uuid.UUID,
        blockers: List[BlockerItem],
        warnings: List[WarningItem],
        satisfied: List[SatisfiedRequirement],
        unknowns: List[UnknownRequirement]
    ) -> None:
        """Evaluates required scientific instruments and vehicles."""
        asset_deps = self.dependency_service.get_outgoing_dependencies(
            entity_type="MISSION",
            entity_id=mission_id,
            relationship_type="REQUIRES"
        )
        required_assets = [d for d in asset_deps if d.target_entity_type == "ASSET"]

        for ad in required_assets:
            try:
                sql_asset = text("SELECT id, asset_code, name, status, condition FROM assets WHERE id = :aid")
                a_row = self.session.execute(sql_asset, {"aid": str(ad.target_entity_id)}).mappings().first()
            except Exception:
                a_row = None

            if not a_row:
                unknowns.append(
                    UnknownRequirement(
                        category="ASSET",
                        description=f"Required asset {ad.target_entity_id} record not found in assets inventory.",
                        reason="Assets module under development by Track B.",
                        status="PENDING_TRACK_B"
                    )
                )
                continue

            status = a_row.get("status") or a_row.get("condition")
            if status in ("DAMAGED", "LOST", "IN_MAINTENANCE", "DECOMMISSIONED", "UNAVAILABLE"):
                blockers.append(
                    BlockerItem(
                        type="ASSET",
                        entity_type="ASSET",
                        entity_id=ad.target_entity_id,
                        entity_code=a_row["asset_code"],
                        reason=f"Mandatory asset '{a_row['asset_code']}' is in '{status}' status.",
                        evidence={"asset_code": a_row["asset_code"], "status": status}
                    )
                )
            else:
                satisfied.append(
                    SatisfiedRequirement(
                        category="ASSET",
                        description=f"Mandatory asset '{a_row['asset_code']}' ({a_row['name']}) verified serviceable ({status}).",
                        entity_type="ASSET",
                        entity_id=ad.target_entity_id,
                        evidence={"asset_code": a_row["asset_code"], "status": status}
                    )
                )

    def _evaluate_time_windows(
        self,
        mission_id: uuid.UUID,
        blockers: List[BlockerItem],
        warnings: List[WarningItem],
        satisfied: List[SatisfiedRequirement],
        unknowns: List[UnknownRequirement]
    ) -> None:
        """Evaluates associated operational time windows."""
        tw_rows = self.session.execute(
            select(TimeWindowModel).where(
                TimeWindowModel.subject_type == "MISSION",
                TimeWindowModel.subject_id == mission_id
            )
        ).scalars().all()

        if not tw_rows:
            satisfied.append(
                SatisfiedRequirement(
                    category="TIME_WINDOW",
                    description="No restrictive time windows bound to mission.",
                    evidence={}
                )
            )
            return

        for tw in tw_rows:
            if tw.status == "CLOSED":
                blockers.append(
                    BlockerItem(
                        type="TIME_WINDOW",
                        entity_type="TIME_WINDOW",
                        entity_id=tw.id,
                        entity_code=None,
                        reason=f"Mission execution time window is CLOSED (close_at: {tw.close_at.isoformat()}).",
                        evidence={"open_at": tw.open_at.isoformat(), "close_at": tw.close_at.isoformat()}
                    )
                )
            elif tw.status == "OPEN":
                satisfied.append(
                    SatisfiedRequirement(
                        category="TIME_WINDOW",
                        description=f"Operational time window is OPEN until {tw.close_at.isoformat()}.",
                        entity_type="TIME_WINDOW",
                        entity_id=tw.id,
                        evidence={"open_at": tw.open_at.isoformat(), "close_at": tw.close_at.isoformat()}
                    )
                )
            else:
                warnings.append(
                    WarningItem(
                        type="TIME_WINDOW",
                        entity_type="TIME_WINDOW",
                        entity_id=tw.id,
                        entity_code=None,
                        reason=f"Time window in status '{tw.status}'.",
                        evidence={"status": tw.status}
                    )
                )
