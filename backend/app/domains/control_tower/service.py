"""Domain Service for Operational Control Tower Aggregation & Read Model."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_

from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.expeditions.repository import ExpeditionRepository
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.missions.repository import MissionRepository
from backend.app.services.readiness.expedition import ExpeditionReadinessService
from backend.app.services.readiness.mission import MissionReadinessService
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.constraints.models import ConstraintModel
from backend.app.platform.events.service import EventService
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.events.schemas import OperationalEventFilter
from backend.app.platform.audit.service import AuditService
from backend.app.platform.audit.models import AuditLogModel
from backend.app.domains.replanning.models import (
    ReplanModel,
    ReplanOptionModel,
    RecommendationModel,
    ApprovalModel,
)
from backend.app.domains.replanning.repository import ReplanRepository
from backend.app.domains.replanning.states import (
    ReplanStatus,
    RecommendationStatus,
    ApprovalStatus,
    ApprovalDecision,
)
from backend.app.domains.incidents.models import IncidentModel
from backend.app.domains.sync.models import OfflineOperationModel
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.control_tower.schemas import (
    ControlTowerOverview,
    ExpeditionControlSummary,
    MissionOperationsItem,
    OperationalEventFeedItem,
    ControlTowerConstraintItem,
    DecisionQueueSummary,
    DecisionReplanItem,
    DecisionRecommendationItem,
    DecisionApprovalItem,
    ConsequentialActionItem,
)
from backend.app.shared.types.reasoning import (
    ReadinessState,
    ConstraintState,
)
from backend.app.core.errors import EntityNotFoundError


class ControlTowerService:
    """
    Pure aggregation and read-model orchestrator for the Operational Control Tower.
    Composes existing domain services without duplicating their underlying rules.
    """

    def __init__(self, session: Session):
        self.session = session
        self.expedition_repo = ExpeditionRepository(session)
        self.mission_repo = MissionRepository(session)
        self.expedition_readiness = ExpeditionReadinessService(session)
        self.mission_readiness = MissionReadinessService(session)
        self.constraint_service = ConstraintService(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)
        self.replan_repo = ReplanRepository(session)

    # -----------------------------------------------------------------------
    # 1. Global Overview
    # -----------------------------------------------------------------------

    def get_overview(self, expedition_id: Optional[uuid.UUID] = None) -> ControlTowerOverview:
        """
        Builds a comprehensive campaign-wide operational overview.
        Aggregates readiness, missions, incidents, constraints, replans, approvals, and sync status.
        """
        now = datetime.now(timezone.utc)

        # 1. Expeditions
        exp_stmt = select(ExpeditionModel)
        if expedition_id:
            exp_stmt = exp_stmt.where(ExpeditionModel.id == expedition_id)
        expeditions = list(self.session.execute(exp_stmt.order_by(ExpeditionModel.code.asc())).scalars().all())

        expedition_summaries = []
        for exp in expeditions:
            expedition_summaries.append(self.get_expedition_summary(exp.id))

        # 2. Missions Aggregate
        m_stmt = select(MissionModel)
        if expedition_id:
            m_stmt = m_stmt.where(MissionModel.expedition_id == expedition_id)
        all_missions = list(self.session.execute(m_stmt).scalars().all())

        readiness_counts: Dict[str, int] = {
            ReadinessState.READY.value: 0,
            ReadinessState.AT_RISK.value: 0,
            ReadinessState.BLOCKED.value: 0,
            "UNKNOWN": 0,
        }
        status_counts: Dict[str, int] = {}

        for m in all_missions:
            status_counts[m.status] = status_counts.get(m.status, 0) + 1
            # Derive readiness using mission readiness service
            r_res = self.mission_readiness.evaluate(m.id)
            state_val = r_res.state.value if hasattr(r_res.state, "value") else str(r_res.state)
            readiness_counts[state_val] = readiness_counts.get(state_val, 0) + 1

        # 3. Active Incidents (status not in RESOLVED, CLOSED)
        inc_stmt = select(func.count(IncidentModel.id)).where(
            IncidentModel.status.notin_(["RESOLVED", "CLOSED"])
        )
        if expedition_id:
            inc_stmt = inc_stmt.where(IncidentModel.expedition_id == expedition_id)
        active_incidents = self.session.execute(inc_stmt).scalar() or 0

        # 4. Critical Hard Constraints Violated
        # Evaluate active hard constraints
        hc_stmt = select(ConstraintModel).where(
            ConstraintModel.active.is_(True),
            ConstraintModel.hard_or_soft == "HARD",
        )
        if expedition_id:
            m_ids = list(
                self.session.execute(
                    select(MissionModel.id).where(MissionModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            t_ids = list(
                self.session.execute(
                    select(TransportLegModel.id).where(TransportLegModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            c_ids = list(
                self.session.execute(
                    select(CargoConsignmentModel.id).where(CargoConsignmentModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            target_ids = [expedition_id] + m_ids + t_ids + c_ids
            hc_stmt = hc_stmt.where(
                or_(
                    ConstraintModel.subject_id.in_(target_ids),
                    ConstraintModel.subject_id.is_(None),
                )
            )

        hard_constraints = self.session.execute(hc_stmt).scalars().all()

        crit_violated_count = 0
        for hc in hard_constraints:
            ev = self.constraint_service.evaluate_constraint(hc)
            if ev.state == ConstraintState.VIOLATED:
                crit_violated_count += 1

        # 5. Pending Replans, Recommendations, Approvals
        pending_replan_statuses = [
            ReplanStatus.REQUESTED.value,
            ReplanStatus.ANALYZING.value,
            ReplanStatus.OPTIONS_READY.value,
            ReplanStatus.AWAITING_APPROVAL.value,
        ]
        r_stmt = select(func.count(ReplanModel.id)).where(ReplanModel.status.in_(pending_replan_statuses))
        if expedition_id:
            r_stmt = r_stmt.where(ReplanModel.expedition_id == expedition_id)
        pending_replans = self.session.execute(r_stmt).scalar() or 0

        rec_stmt = select(func.count(RecommendationModel.id)).where(
            RecommendationModel.status.in_([RecommendationStatus.PROPOSED.value, RecommendationStatus.SELECTED.value])
        )
        if expedition_id:
            rec_stmt = rec_stmt.join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id).where(
                ReplanModel.expedition_id == expedition_id
            )
        pending_recs = self.session.execute(rec_stmt).scalar() or 0

        appr_stmt = select(func.count(ApprovalModel.id)).where(ApprovalModel.status == ApprovalStatus.PENDING.value)
        if expedition_id:
            appr_stmt = (
                appr_stmt.join(RecommendationModel, ApprovalModel.recommendation_id == RecommendationModel.id)
                .join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id)
                .where(ReplanModel.expedition_id == expedition_id)
            )
        pending_approvals = self.session.execute(appr_stmt).scalar() or 0

        # 6. Offline Sync Summary
        sync_counts = dict(
            self.session.execute(
                select(OfflineOperationModel.status, func.count(OfflineOperationModel.id)).group_by(
                    OfflineOperationModel.status
                )
            ).all()
        )

        # 7. Recent Operational Events
        feed_items, _ = self.get_events_feed(expedition_id=expedition_id, page=1, page_size=10)

        return ControlTowerOverview(
            total_expeditions=len(expedition_summaries),
            expeditions=expedition_summaries,
            total_missions=len(all_missions),
            missions_by_readiness=readiness_counts,
            missions_by_status=status_counts,
            active_incidents_count=active_incidents,
            critical_constraints_violated_count=crit_violated_count,
            pending_replans_count=pending_replans,
            pending_recommendations_count=pending_recs,
            pending_approvals_count=pending_approvals,
            offline_sync_summary=sync_counts,
            recent_operational_events=feed_items,
            data_provenance="DERIVED",
            generated_at=now,
        )

    # -----------------------------------------------------------------------
    # 2. Expedition Summary
    # -----------------------------------------------------------------------

    def get_expedition_summary(self, expedition_id: uuid.UUID) -> ExpeditionControlSummary:
        """Evaluates and rolls up a single expedition's operational posture."""
        exp = self.expedition_repo.get_by_id(expedition_id)
        if not exp:
            raise EntityNotFoundError("Expedition", expedition_id)

        now = datetime.now(timezone.utc)
        readiness_res = self.expedition_readiness.evaluate(expedition_id)
        state_str = readiness_res.state.value if hasattr(readiness_res.state, "value") else str(readiness_res.state)

        # Active incidents for expedition
        inc_count = (
            self.session.execute(
                select(func.count(IncidentModel.id)).where(
                    IncidentModel.expedition_id == expedition_id,
                    IncidentModel.status.notin_(["RESOLVED", "CLOSED"]),
                )
            ).scalar()
            or 0
        )

        # Active hard constraint violations on this expedition's missions
        mission_ids = [m.mission_id for m in readiness_res.mission_summaries]
        hard_violations = 0
        if mission_ids:
            constraints = self.session.execute(
                select(ConstraintModel).where(
                    ConstraintModel.active.is_(True),
                    ConstraintModel.hard_or_soft == "HARD",
                    or_(
                        ConstraintModel.subject_id.in_(mission_ids),
                        ConstraintModel.subject_id == expedition_id,
                    ),
                )
            ).scalars().all()
            for c in constraints:
                ev = self.constraint_service.evaluate_constraint(c)
                if ev.state == ConstraintState.VIOLATED:
                    hard_violations += 1

        # Pending replans
        pending_replan_statuses = [
            ReplanStatus.REQUESTED.value,
            ReplanStatus.ANALYZING.value,
            ReplanStatus.OPTIONS_READY.value,
            ReplanStatus.AWAITING_APPROVAL.value,
        ]
        pending_replans = (
            self.session.execute(
                select(func.count(ReplanModel.id)).where(
                    ReplanModel.expedition_id == expedition_id,
                    ReplanModel.status.in_(pending_replan_statuses),
                )
            ).scalar()
            or 0
        )

        # Pending approvals
        pending_approvals = (
            self.session.execute(
                select(func.count(ApprovalModel.id))
                .join(RecommendationModel, ApprovalModel.recommendation_id == RecommendationModel.id)
                .join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id)
                .where(
                    ReplanModel.expedition_id == expedition_id,
                    ApprovalModel.status == ApprovalStatus.PENDING.value,
                )
            ).scalar()
            or 0
        )

        # Latest events
        events, _ = self.get_events_feed(expedition_id=expedition_id, page=1, page_size=5)

        return ExpeditionControlSummary(
            expedition_id=exp.id,
            code=exp.code,
            name=exp.name,
            season=exp.season,
            lifecycle_status=getattr(exp, "status", "ACTIVE") or "ACTIVE",
            readiness_state=state_str,
            total_missions=readiness_res.total_missions,
            ready_missions_count=readiness_res.ready_missions,
            at_risk_missions_count=readiness_res.at_risk_missions,
            blocked_missions_count=readiness_res.blocked_missions,
            active_incidents_count=inc_count,
            active_hard_constraint_violations_count=hard_violations,
            pending_replans_count=pending_replans,
            pending_approvals_count=pending_approvals,
            latest_events=events,
            blockers=[b.model_dump() for b in readiness_res.blockers],
            warnings=[w.model_dump() for w in readiness_res.warnings],
            unknown_requirements=[u.model_dump() for u in readiness_res.unknown_requirements],
            data_provenance="DERIVED",
            generated_at=now,
        )

    # -----------------------------------------------------------------------
    # 3. Mission Operations View
    # -----------------------------------------------------------------------

    def _build_mission_operations_item(
        self, m: MissionModel, r_res: Any, r_state: str
    ) -> MissionOperationsItem:
        """Helper to construct a typed MissionOperationsItem with evaluated context."""
        c_summary = self.constraint_service.evaluate_for_entity("MISSION", m.id)
        violated_constraints = [
            c.model_dump() for c in c_summary.results if c.state == ConstraintState.VIOLATED
        ]

        replans = list(
            self.session.execute(
                select(ReplanModel).where(
                    or_(
                        ReplanModel.mission_id == m.id,
                        ReplanModel.trigger_entity_id == m.id,
                    ),
                    ReplanModel.status.in_([
                        ReplanStatus.REQUESTED.value,
                        ReplanStatus.ANALYZING.value,
                        ReplanStatus.OPTIONS_READY.value,
                        ReplanStatus.AWAITING_APPROVAL.value,
                    ])
                )
            ).scalars().all()
        )
        replan_list = [
            {"replan_id": str(r.id), "replan_code": r.replan_code, "status": r.status}
            for r in replans
        ]

        latest_ev_model = self.session.execute(
            select(OperationalEventModel)
            .where(
                OperationalEventModel.entity_type == "MISSION",
                OperationalEventModel.entity_id == m.id,
            )
            .order_by(OperationalEventModel.occurred_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        latest_ev = None
        if latest_ev_model:
            latest_ev = OperationalEventFeedItem.model_validate(latest_ev_model)

        return MissionOperationsItem(
            mission_id=m.id,
            code=m.code,
            title=m.title,
            status=m.status,
            priority=m.priority,
            type=m.type,
            required_by_at=m.required_by_at,
            location_id=m.location_id,
            readiness_state=r_state,
            readiness_blockers=[b.model_dump() for b in r_res.blockers],
            warnings=[w.model_dump() for w in r_res.warnings],
            unknown_requirements=[u.model_dump() for u in r_res.unknown_requirements],
            violated_constraints=violated_constraints,
            pending_replans=replan_list,
            latest_event=latest_ev,
            data_provenance="DERIVED",
        )

    def get_mission_operations_view(
        self,
        expedition_id: uuid.UUID,
        status: Optional[str] = None,
        readiness: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[MissionOperationsItem], int]:
        """Provides detailed operational context for missions within an expedition."""
        exp = self.expedition_repo.get_by_id(expedition_id)
        if not exp:
            raise EntityNotFoundError("Expedition", expedition_id)

        stmt = select(MissionModel).where(MissionModel.expedition_id == expedition_id)
        if status:
            stmt = stmt.where(MissionModel.status == status.upper())

        offset = (page - 1) * page_size
        items: List[MissionOperationsItem] = []

        if readiness is None:
            count_stmt = select(func.count(MissionModel.id)).where(MissionModel.expedition_id == expedition_id)
            if status:
                count_stmt = count_stmt.where(MissionModel.status == status.upper())
            total = self.session.execute(count_stmt).scalar() or 0

            paged_missions = list(
                self.session.execute(
                    stmt.order_by(MissionModel.code.asc())
                    .offset(offset)
                    .limit(page_size)
                ).scalars().all()
            )
            for m in paged_missions:
                r_res = self.mission_readiness.evaluate(m.id)
                r_state = r_res.state.value if hasattr(r_res.state, "value") else str(r_res.state)
                items.append(self._build_mission_operations_item(m, r_res, r_state))
            return items, total
        else:
            all_missions = list(self.session.execute(stmt.order_by(MissionModel.code.asc())).scalars().all())
            matching_tuples = []
            for m in all_missions:
                r_res = self.mission_readiness.evaluate(m.id)
                r_state = r_res.state.value if hasattr(r_res.state, "value") else str(r_res.state)
                if r_state == readiness.upper():
                    matching_tuples.append((m, r_res, r_state))

            total = len(matching_tuples)
            paged_tuples = matching_tuples[offset : offset + page_size]
            for m, r_res, r_state in paged_tuples:
                items.append(self._build_mission_operations_item(m, r_res, r_state))
            return items, total

    # -----------------------------------------------------------------------
    # 4. Operational Events Feed
    # -----------------------------------------------------------------------

    def get_events_feed(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        event_type: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OperationalEventFeedItem], int]:
        """Provides a read-only timeline of operational events."""
        stmt = select(OperationalEventModel)

        if entity_type:
            stmt = stmt.where(OperationalEventModel.entity_type == entity_type.upper())
        if event_type:
            stmt = stmt.where(OperationalEventModel.event_type == event_type)
        if from_time:
            stmt = stmt.where(OperationalEventModel.occurred_at >= from_time)
        if to_time:
            stmt = stmt.where(OperationalEventModel.occurred_at <= to_time)

        if expedition_id:
            m_ids = list(
                self.session.execute(
                    select(MissionModel.id).where(MissionModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            r_ids = list(
                self.session.execute(
                    select(ReplanModel.id).where(ReplanModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            t_ids = list(
                self.session.execute(
                    select(TransportLegModel.id).where(TransportLegModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            c_ids = list(
                self.session.execute(
                    select(CargoConsignmentModel.id).where(CargoConsignmentModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            inc_ids = list(
                self.session.execute(
                    select(IncidentModel.id).where(IncidentModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            rec_ids = []
            if r_ids:
                rec_ids = list(
                    self.session.execute(
                        select(RecommendationModel.id).where(RecommendationModel.replan_id.in_(r_ids))
                    ).scalars().all()
                )
            appr_ids = []
            if rec_ids:
                appr_ids = list(
                    self.session.execute(
                        select(ApprovalModel.id).where(ApprovalModel.recommendation_id.in_(rec_ids))
                    ).scalars().all()
                )

            target_ids = [expedition_id] + m_ids + r_ids + t_ids + c_ids + inc_ids + rec_ids + appr_ids
            stmt = stmt.where(OperationalEventModel.entity_id.in_(target_ids))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        events = list(
            self.session.execute(
                stmt.order_by(OperationalEventModel.occurred_at.desc())
                .offset(offset)
                .limit(page_size)
            ).scalars().all()
        )

        return [OperationalEventFeedItem.model_validate(e) for e in events], total

    # -----------------------------------------------------------------------
    # 5. Active Risk / Constraints View
    # -----------------------------------------------------------------------

    def _build_constraint_item(
        self, c: ConstraintModel, eval_res: Any = None, state_val: str = None
    ) -> ControlTowerConstraintItem:
        """Helper to construct a typed ControlTowerConstraintItem with evaluated context."""
        if eval_res is None or state_val is None:
            eval_res = self.constraint_service.evaluate_constraint(c)
            state_val = eval_res.state.value if hasattr(eval_res.state, "value") else str(eval_res.state)

        return ControlTowerConstraintItem(
            constraint_id=c.id,
            code=c.code,
            name=c.name,
            type=c.type,
            rule_code=c.rule_code,
            subject_type=c.subject_type or "UNKNOWN",
            subject_id=c.subject_id or uuid.UUID(int=0),
            subject_code=getattr(c, "subject_code", None),
            hard_or_soft=c.hard_or_soft,
            severity=c.severity,
            state=state_val,
            reason=eval_res.reason,
            evidence=eval_res.evidence,
            data_provenance="DERIVED",
        )

    def get_active_constraints(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        state: Optional[str] = None,
        hard_or_soft: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ControlTowerConstraintItem], int]:
        """Exposes active operational constraints with explicit tri-state outcomes."""
        stmt = select(ConstraintModel).where(ConstraintModel.active.is_(True))
        if hard_or_soft:
            stmt = stmt.where(ConstraintModel.hard_or_soft == hard_or_soft.upper())

        if expedition_id:
            m_ids = list(
                self.session.execute(
                    select(MissionModel.id).where(MissionModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            t_ids = list(
                self.session.execute(
                    select(TransportLegModel.id).where(TransportLegModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            c_ids = list(
                self.session.execute(
                    select(CargoConsignmentModel.id).where(CargoConsignmentModel.expedition_id == expedition_id)
                ).scalars().all()
            )
            target_ids = [expedition_id] + m_ids + t_ids + c_ids
            stmt = stmt.where(
                or_(
                    ConstraintModel.subject_id.in_(target_ids),
                    ConstraintModel.subject_id.is_(None),
                )
            )

        offset = (page - 1) * page_size
        items: List[ControlTowerConstraintItem] = []

        if state is None:
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = self.session.execute(count_stmt).scalar() or 0

            paged_constraints = list(
                self.session.execute(
                    stmt.order_by(ConstraintModel.code.asc())
                    .offset(offset)
                    .limit(page_size)
                ).scalars().all()
            )
            for c in paged_constraints:
                items.append(self._build_constraint_item(c))
            return items, total
        else:
            all_constraints = list(self.session.execute(stmt.order_by(ConstraintModel.code.asc())).scalars().all())
            matching_tuples = []
            for c in all_constraints:
                eval_res = self.constraint_service.evaluate_constraint(c)
                st_val = eval_res.state.value if hasattr(eval_res.state, "value") else str(eval_res.state)
                if st_val == state.upper():
                    matching_tuples.append((c, eval_res, st_val))

            total = len(matching_tuples)
            paged_tuples = matching_tuples[offset : offset + page_size]
            for c, eval_res, st_val in paged_tuples:
                items.append(self._build_constraint_item(c, eval_res=eval_res, state_val=st_val))
            return items, total

    # -----------------------------------------------------------------------
    # 6. Replan / Recommendation / Approval Decision Queue
    # -----------------------------------------------------------------------

    def get_decision_queue(
        self,
        expedition_id: Optional[uuid.UUID] = None,
    ) -> DecisionQueueSummary:
        """Aggregates pending operational decisions awaiting human inspection or approval."""
        now = datetime.now(timezone.utc)

        # 1. Pending Replans
        pending_replan_statuses = [
            ReplanStatus.REQUESTED.value,
            ReplanStatus.ANALYZING.value,
            ReplanStatus.OPTIONS_READY.value,
            ReplanStatus.AWAITING_APPROVAL.value,
        ]
        r_stmt = select(ReplanModel).where(ReplanModel.status.in_(pending_replan_statuses))
        if expedition_id:
            r_stmt = r_stmt.where(ReplanModel.expedition_id == expedition_id)
        replans = list(self.session.execute(r_stmt.order_by(ReplanModel.created_at.desc())).scalars().all())

        replan_items = []
        for r in replans:
            replan_items.append(
                DecisionReplanItem(
                    replan_id=r.id,
                    replan_code=r.replan_code,
                    expedition_id=r.expedition_id,
                    mission_id=r.mission_id,
                    status=r.status,
                    trigger_mode=r.current_state_evidence.get("trigger_mode", "OPERATOR_REQUESTED") if r.current_state_evidence else "OPERATOR_REQUESTED",
                    trigger_reason=r.trigger_reason,
                    what_changed=r.trigger_reason or "Operational mutation requiring replanning",
                    affected_entities_count=len(r.affected_entities) if r.affected_entities else 0,
                    violated_constraints_count=len(r.violated_constraints) if r.violated_constraints else 0,
                    created_at=r.created_at,
                )
            )

        # 2. Pending Recommendations
        rec_stmt = select(RecommendationModel).where(
            RecommendationModel.status.in_([RecommendationStatus.PROPOSED.value, RecommendationStatus.SELECTED.value])
        )
        if expedition_id:
            rec_stmt = rec_stmt.join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id).where(
                ReplanModel.expedition_id == expedition_id
            )
        recommendations = list(self.session.execute(rec_stmt.order_by(RecommendationModel.created_at.desc())).scalars().all())

        rec_items = []
        for rec in recommendations:
            rec_items.append(
                DecisionRecommendationItem(
                    recommendation_id=rec.id,
                    replan_id=rec.replan_id,
                    option_id=rec.option_id,
                    title=rec.title,
                    summary=rec.summary,
                    status=rec.status,
                    approval_state=rec.approval_state,
                    what_is_affected=rec.affected_entities or [],
                    rationale=rec.rationale or [],
                    proposed_changes=rec.proposed_changes or [],
                    created_at=rec.created_at,
                )
            )

        # 3. Pending Approvals
        appr_stmt = select(ApprovalModel).where(ApprovalModel.status == ApprovalStatus.PENDING.value)
        if expedition_id:
            appr_stmt = (
                appr_stmt.join(RecommendationModel, ApprovalModel.recommendation_id == RecommendationModel.id)
                .join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id)
                .where(ReplanModel.expedition_id == expedition_id)
            )
        approvals = list(self.session.execute(appr_stmt.order_by(ApprovalModel.created_at.desc())).scalars().all())

        appr_items = []
        for a in approvals:
            rec = self.session.get(RecommendationModel, a.recommendation_id)
            replan = self.session.get(ReplanModel, rec.replan_id) if rec else None

            what_changed = replan.trigger_reason if replan and replan.trigger_reason else "Operational state disruption"
            why_it_matters = (
                f"Requires operational adjustment to restore expedition readiness: {rec.title}"
                if rec
                else "Human decision boundary required"
            )
            v_constraints = replan.violated_constraints if replan and replan.violated_constraints else []
            constraint_names = ", ".join([c.get("name", c.get("code", "Constraint")) for c in v_constraints]) or "Operational Invariant"
            opt_count = len(replan.options) if replan and replan.options else 1

            appr_items.append(
                DecisionApprovalItem(
                    approval_id=a.id,
                    recommendation_id=a.recommendation_id,
                    replan_id=rec.replan_id if rec else None,
                    recommendation_title=rec.title if rec else "Operational Recommendation",
                    status=a.status,
                    required_approver_role=a.approver_role or "EXPEDITION_OPERATOR",
                    what_changed=what_changed,
                    why_it_matters=why_it_matters,
                    what_constraint_is_involved=constraint_names,
                    available_options_count=opt_count,
                    created_at=a.created_at,
                )
            )

        return DecisionQueueSummary(
            expedition_id=expedition_id,
            total_pending_replans=len(replan_items),
            total_pending_recommendations=len(rec_items),
            total_pending_approvals=len(appr_items),
            pending_replans=replan_items,
            pending_recommendations=rec_items,
            pending_approvals=appr_items,
            data_provenance="DERIVED",
            generated_at=now,
        )

    # -----------------------------------------------------------------------
    # 7. Consequential Action / Audit Summary
    # -----------------------------------------------------------------------

    def get_recent_actions(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ConsequentialActionItem], int]:
        """Provides an auditable feed of consequential approved decisions and applied updates."""
        stmt = select(ApprovalModel).where(
            ApprovalModel.status.in_([ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value])
        )

        if expedition_id:
            stmt = (
                stmt.join(RecommendationModel, ApprovalModel.recommendation_id == RecommendationModel.id)
                .join(ReplanModel, RecommendationModel.replan_id == ReplanModel.id)
                .where(ReplanModel.expedition_id == expedition_id)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        approvals = list(
            self.session.execute(
                stmt.order_by(ApprovalModel.created_at.desc())
                .offset(offset)
                .limit(page_size)
            ).scalars().all()
        )

        items: List[ConsequentialActionItem] = []
        for a in approvals:
            rec = self.session.get(RecommendationModel, a.recommendation_id)
            replan = self.session.get(ReplanModel, rec.replan_id) if rec else None

            action_summary = (
                f"Operator rendered decision '{a.decision}' for recommendation '{rec.title if rec else a.recommendation_id}'."
            )

            items.append(
                ConsequentialActionItem(
                    approval_id=a.id,
                    recommendation_id=a.recommendation_id,
                    replan_id=rec.replan_id if rec else None,
                    decision=a.decision,
                    approver_person_id=a.approver_person_id,
                    approver_role=a.approver_role,
                    comment=a.comment,
                    decided_at=a.decided_at,
                    action_summary=action_summary,
                    applied_changes=rec.proposed_changes if rec and rec.proposed_changes else [],
                    resulting_event_id=a.resulting_event_id,
                    correlation_id=a.correlation_id,
                    created_at=a.created_at,
                    data_provenance="DERIVED",
                )
            )

        return items, total
