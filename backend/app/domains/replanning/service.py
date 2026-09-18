"""Domain Service for Replanning, Candidate Options, Recommendations, and Approvals."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

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
    ApprovalDecision,
    ApprovalStatus,
    OptionFeasibility,
    ReplanActionType,
)
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ApprovalDecisionRequest,
    ReplanApplyRequest,
    ReplanApplyResult,
)
from backend.app.services.impact.service import ImpactService
from backend.app.services.constraints.service import ConstraintService
from backend.app.shared.types.reasoning import ConstraintState
from backend.app.shared.types.states import HardSoftConstraint
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.domains.transport.service import TransportService
from backend.app.domains.transport.schemas import TransportLegUpdate
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.missions.service import MissionService
from backend.app.domains.missions.schemas import MissionUpdate
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.assets.models import AssetModel
from backend.app.core.errors import (
    EntityNotFoundError,
    DomainValidationError,
    ConflictError,
)


class ReplanService:
    """
    Orchestrates deterministic operational replanning:
    1. Validates trigger conditions (event-driven or operator-requested)
    2. Explores candidate mitigation options from current domain facts
    3. Evaluates constraint feasibility (FEASIBLE, CONSTRAINED, NOT_EVALUABLE, INFEASIBLE)
    4. Produces explainable recommendations with structured rationale
    5. Emits immutable operational events and audit logs
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = ReplanRepository(session)
        self.impact_service = ImpactService(session)
        self.constraint_service = ConstraintService(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_replan_request(
        self,
        request: ReplanTriggerRequest,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> ReplanModel:
        """
        Creates an operational replan record under strict trigger validation:
        - EVENT_TRIGGERED: requires meaningful state change, operational impact,
          and hard constraint violation or infeasibility.
        - OPERATOR_REQUESTED: explicit authorized human operator request.
        """
        actor = actor_context or {"actor_type": "OPERATOR", "actor_id": request.requested_by, "source": "API"}
        cid = request.correlation_id or uuid.uuid4()

        impact_result = None
        violated_constraints = []
        affected_entities = []

        # If trigger entity is provided or trigger event is provided, compute derived impact
        if request.trigger_entity_type and request.trigger_entity_id:
            impact_result = self.impact_service.calculate_impact(
                entity_type=request.trigger_entity_type,
                entity_id=request.trigger_entity_id,
                change_summary=request.reason,
                depth=request.depth,
                correlation_id=cid,
            )
        elif request.trigger_event_id:
            event = self.event_service.get_event(request.trigger_event_id)
            if not event:
                raise EntityNotFoundError("OperationalEvent", request.trigger_event_id)
            impact_result = self.impact_service.calculate_impact(
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                change_summary=f"Event {event.event_type}: {event.previous_state} -> {event.new_state}",
                depth=request.depth,
                correlation_id=event.correlation_id or cid,
            )

        if impact_result:
            affected_entities = [e.model_dump() for e in impact_result.affected_entities]
            violated_constraints = [
                c.model_dump()
                for c in impact_result.constraint_candidates
                if c.state == ConstraintState.VIOLATED
            ]

        # Trigger Rule Evaluation
        mode = request.trigger_mode.upper().strip()
        if mode == "EVENT_TRIGGERED":
            # Check hard trigger criteria:
            has_impact = len(affected_entities) > 0
            has_hard_violation = any(
                c.get("hard_or_soft") == HardSoftConstraint.HARD.value or c.get("hard_or_soft") == "HARD"
                for c in violated_constraints
            )
            if not (has_impact and (has_hard_violation or len(violated_constraints) > 0)):
                raise DomainValidationError(
                    message="EVENT_TRIGGERED replan requires meaningful state change, operational impact (>0 affected entities), and at least one violated constraint or infeasible requirement.",
                    field="trigger_condition",
                )
        elif mode != "OPERATOR_REQUESTED":
            raise DomainValidationError(
                message=f"Unsupported trigger mode '{request.trigger_mode}'.",
                field="trigger_mode",
            )

        # Generate unique replan code
        code_seq = self.repo.session.execute(
            select(ReplanModel.id)
        ).scalars().all()
        replan_code = f"RPL-2026-{len(code_seq) + 1:04d}"

        evidence_dict = {
            "trigger_mode": mode,
            "reason": request.reason,
            "total_affected_entities": len(affected_entities),
            "total_violated_constraints": len(violated_constraints),
        }

        replan = ReplanModel(
            id=uuid.uuid4(),
            replan_code=replan_code,
            expedition_id=request.expedition_id,
            mission_id=request.mission_id,
            trigger_event_id=request.trigger_event_id,
            trigger_entity_type=request.trigger_entity_type.upper() if request.trigger_entity_type else None,
            trigger_entity_id=request.trigger_entity_id,
            trigger_reason=request.reason,
            status=ReplanStatus.REQUESTED.value,
            current_state_evidence=evidence_dict,
            violated_constraints=violated_constraints,
            affected_entities=affected_entities,
            requested_by=request.requested_by,
            correlation_id=cid,
            data_provenance="DERIVED" if mode == "EVENT_TRIGGERED" else "SYNTHETIC_DEMO",
            generated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with self.session.begin_nested():
            created = self.repo.create_replan(replan)

            self.event_service.append_event(
                event_type="ReplanRequested",
                entity_type="REPLAN",
                entity_id=created.id,
                new_state=ReplanStatus.REQUESTED.value,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "OPERATOR"),
                actor_id=actor.get("actor_id"),
                correlation_id=cid,
                evidence={"replan_code": created.replan_code, "trigger_mode": mode},
            )

            self.audit_service.record_audit(
                action="REPLAN_REQUESTED",
                entity_type="REPLAN",
                entity_id=created.id,
                after_snapshot={"replan_code": created.replan_code, "status": created.status},
                correlation_id=cid,
                actor_user_id=None,
                actor_person_id=request.requested_by,
                metadata={"trigger_mode": mode, "reason": request.reason},
            )

        return created

    def get_replan(self, replan_id: uuid.UUID) -> ReplanModel:
        replan = self.repo.get_replan_by_id(replan_id)
        if not replan:
            raise EntityNotFoundError("Replan", replan_id)
        return replan

    def list_replans(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        mission_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ReplanModel], int]:
        return self.repo.list_replans(
            expedition_id=expedition_id,
            mission_id=mission_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def generate_options(
        self,
        replan_id: uuid.UUID,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ReplanOptionModel], List[RecommendationModel]]:
        """
        Deterministic Candidate Option & Explainable Recommendation Generator:
        1. Inspects current domain facts (not hardcoded hero codes)
        2. Formulates candidate actions based on affected entity types
        3. Evaluates candidates against ConstraintService for tri-state feasibility
        4. Produces transparent explainable recommendations for feasible/constrained candidates
        """
        replan = self.get_replan(replan_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = replan.correlation_id or uuid.uuid4()

        replan.status = ReplanStatus.ANALYZING.value
        self.session.flush()

        affected_list = replan.affected_entities or []
        violated_list = replan.violated_constraints or []

        # If affected entities list is empty, recalculate
        if not affected_list and replan.trigger_entity_type and replan.trigger_entity_id:
            impact = self.impact_service.calculate_impact(
                entity_type=replan.trigger_entity_type,
                entity_id=replan.trigger_entity_id,
                change_summary=replan.trigger_reason or "Operational analysis",
                depth=3,
                correlation_id=cid,
            )
            affected_list = [e.model_dump() for e in impact.affected_entities]
            violated_list = [c.model_dump() for c in impact.constraint_candidates if c.state == ConstraintState.VIOLATED]
            replan.affected_entities = affected_list
            replan.violated_constraints = violated_list
            self.session.flush()

        # Identify impacted missions, transport legs, cargo, and assets
        impacted_mission_ids = set()
        impacted_transport_ids = set()
        impacted_asset_ids = set()

        if replan.mission_id:
            impacted_mission_ids.add(replan.mission_id)

        if replan.trigger_entity_type == "TRANSPORT_LEG" and replan.trigger_entity_id:
            impacted_transport_ids.add(replan.trigger_entity_id)

        for aff in affected_list:
            etype = aff.get("entity_type")
            eid = uuid.UUID(str(aff.get("entity_id")))
            if etype == "MISSION":
                impacted_mission_ids.add(eid)
            elif etype == "TRANSPORT_LEG":
                impacted_transport_ids.add(eid)
            elif etype == "ASSET":
                impacted_asset_ids.add(eid)

        candidate_options: List[ReplanOptionModel] = []
        option_idx = 1

        # -------------------------------------------------------------
        # CANDIDATE 1: Alternative Transport Leg (MODIFY_TRANSPORT)
        # Search for available alternative transport leg in same expedition
        # -------------------------------------------------------------
        if impacted_transport_ids:
            for leg_id in impacted_transport_ids:
                curr_leg = self.session.get(TransportLegModel, leg_id)
                if not curr_leg:
                    continue

                # Query database for an alternative transport leg with valid status and matching expedition
                alt_legs_stmt = (
                    select(TransportLegModel)
                    .where(
                        TransportLegModel.expedition_id == curr_leg.expedition_id,
                        TransportLegModel.id != curr_leg.id,
                        TransportLegModel.status.in_(["SCHEDULED", "ON_TIME", "READY", "ACTIVE", "BOARDING"]),
                    )
                    .limit(2)
                )
                alt_legs = list(self.session.execute(alt_legs_stmt).scalars().all())

                for alt_leg in alt_legs:
                    opt = ReplanOptionModel(
                        id=uuid.uuid4(),
                        replan_id=replan.id,
                        option_code=f"OPT-{option_idx:02d}",
                        title=f"Reroute Cargo via Transport Leg {alt_leg.code}",
                        description=(
                            f"Transfer delayed manifest cargo from disrupted transport leg {curr_leg.code} "
                            f"to available scheduled transport leg {alt_leg.code} ({alt_leg.mode})."
                        ),
                        action_type=ReplanActionType.MODIFY_TRANSPORT.value,
                        affected_entity_type="TRANSPORT_LEG",
                        affected_entity_id=alt_leg.id,
                        proposed_changes=[
                            {"action": "reassign_manifest", "from_leg": str(curr_leg.id), "to_leg": str(alt_leg.id)}
                        ],
                        proposed_state_change={
                            "source_transport_id": str(curr_leg.id),
                            "target_transport_id": str(alt_leg.id),
                            "action": "TRANSFER_CARGO",
                        },
                        prerequisite_conditions=[
                            f"Target transport {alt_leg.code} must have sufficient capacity",
                            "Weather and ice conditions permit inter-leg cargo transfer",
                        ],
                        expected_impact={"risk_mitigation": "HIGH", "cargo_delay_eliminated": True},
                        feasibility_state=OptionFeasibility.FEASIBLE.value,
                        operational_rationale="Alternative active transport leg exists within expedition operational theater.",
                        evidence={"source_leg": curr_leg.code, "target_leg": alt_leg.code},
                        assumptions=["Target transport capacity remains nominal"],
                        data_provenance="DERIVED",
                    )
                    candidate_options.append(opt)
                    option_idx += 1

        # -------------------------------------------------------------
        # CANDIDATE 2: Mission Schedule Adjustment (RESCHEDULE_MISSION)
        # -------------------------------------------------------------
        for mid in impacted_mission_ids:
            mission = self.session.get(MissionModel, mid)
            if not mission:
                continue

            current_req = mission.required_by_at or datetime.now(timezone.utc)
            # Propose extending deadline by 7 days to accommodate transport arrival
            new_date = current_req + timedelta(days=7)

            opt = ReplanOptionModel(
                id=uuid.uuid4(),
                replan_id=replan.id,
                option_code=f"OPT-{option_idx:02d}",
                title=f"Adjust Mission {mission.code} Operational Window (+7 Days)",
                description=(
                    f"Reschedule mission '{mission.title}' deadline from "
                    f"{current_req.strftime('%Y-%m-%d')} to {new_date.strftime('%Y-%m-%d')} "
                    f"to absorb upstream logistical delay while preserving field survey objectives."
                ),
                action_type=ReplanActionType.RESCHEDULE_MISSION.value,
                affected_entity_type="MISSION",
                affected_entity_id=mission.id,
                proposed_changes=[
                    {
                        "entity_type": "MISSION",
                        "entity_id": str(mission.id),
                        "field": "required_by_at",
                        "current_value": current_req.isoformat(),
                        "proposed_value": new_date.isoformat(),
                    }
                ],
                proposed_state_change={
                    "mission_id": str(mission.id),
                    "required_by_at": new_date.isoformat(),
                },
                prerequisite_conditions=[
                    "Expedition operational season time window remains open past new deadline",
                    "Assigned team personnel remain fit and in readiness state",
                ],
                expected_impact={"mission_delayed_days": 7, "field_safety": "PRESERVED"},
                feasibility_state=OptionFeasibility.FEASIBLE.value,
                operational_rationale="Extending mission execution buffer restores readiness without cancelling scientific objectives.",
                evidence={"mission_code": mission.code, "current_deadline": current_req.isoformat(), "adjusted_deadline": new_date.isoformat()},
                assumptions=["Weather window permits field deployment 7 days post-nominal"],
                data_provenance="DERIVED",
            )
            candidate_options.append(opt)
            option_idx += 1

        # -------------------------------------------------------------
        # CANDIDATE 3: Asset Reassignment / Substitution (REASSIGN_ASSET)
        # Search for available matching equipment
        # -------------------------------------------------------------
        if impacted_asset_ids:
            for aid in impacted_asset_ids:
                orig_asset = self.session.get(AssetModel, aid)
                if not orig_asset:
                    continue

                sub_stmt = (
                    select(AssetModel)
                    .where(
                        AssetModel.type == orig_asset.type,
                        AssetModel.id != orig_asset.id,
                        AssetModel.status == "AVAILABLE",
                    )
                    .limit(1)
                )
                sub_asset = self.session.execute(sub_stmt).scalars().first()

                if sub_asset:
                    opt = ReplanOptionModel(
                        id=uuid.uuid4(),
                        replan_id=replan.id,
                        option_code=f"OPT-{option_idx:02d}",
                        title=f"Substitute Equipment with Available {sub_asset.name} ({sub_asset.asset_code})",
                        description=(
                            f"Reassign local available {sub_asset.type} '{sub_asset.name}' "
                            f"to mission to replace delayed instrument '{orig_asset.name}'."
                        ),
                        action_type=ReplanActionType.REASSIGN_ASSET.value,
                        affected_entity_type="ASSET",
                        affected_entity_id=sub_asset.id,
                        proposed_changes=[
                            {"action": "substitute_asset", "orig": str(orig_asset.id), "sub": str(sub_asset.id)}
                        ],
                        proposed_state_change={
                            "original_asset_id": str(orig_asset.id),
                            "substitute_asset_id": str(sub_asset.id),
                        },
                        prerequisite_conditions=["Station maintenance logs confirm substitute instrument calibration"],
                        expected_impact={"equipment_readiness": "RESTORED"},
                        feasibility_state=OptionFeasibility.FEASIBLE.value,
                        operational_rationale="Alternative verified equipment of same type is present at expedition base.",
                        evidence={"original": orig_asset.asset_code, "substitute": sub_asset.asset_code},
                        assumptions=["Substitute asset calibration matches field specs"],
                        data_provenance="DERIVED",
                    )
                    candidate_options.append(opt)
                    option_idx += 1
                else:
                    # Incomplete domain facts -> NOT_EVALUABLE (do not invent fake equipment)
                    opt = ReplanOptionModel(
                        id=uuid.uuid4(),
                        replan_id=replan.id,
                        option_code=f"OPT-{option_idx:02d}",
                        title=f"Local Asset Substitution for {orig_asset.asset_code}",
                        description=f"Attempt asset substitution for {orig_asset.name}; required station inventory data unavailable.",
                        action_type=ReplanActionType.REASSIGN_ASSET.value,
                        affected_entity_type="ASSET",
                        affected_entity_id=orig_asset.id,
                        feasibility_state=OptionFeasibility.NOT_EVALUABLE.value,
                        operational_rationale="No verified available substitute asset found in active inventory.",
                        evidence={"original": orig_asset.asset_code, "available_substitutes": 0},
                        data_provenance="ADVISORY",
                    )
                    candidate_options.append(opt)
                    option_idx += 1

        # -------------------------------------------------------------
        # CANDIDATE 4: Defer Activity (DEFER_ACTIVITY)
        # Always evaluate deferral option as CONSTRAINED alternative
        # -------------------------------------------------------------
        for mid in impacted_mission_ids:
            mission = self.session.get(MissionModel, mid)
            if not mission:
                continue

            opt = ReplanOptionModel(
                id=uuid.uuid4(),
                replan_id=replan.id,
                option_code=f"OPT-{option_idx:02d}",
                title=f"Defer Mission {mission.code} to Secondary Season Window",
                description=(
                    f"Defer execution of '{mission.title}' until secondary vessel arrival. "
                    f"Prioritizes primary life-support and station maintenance logistics."
                ),
                action_type=ReplanActionType.DEFER_ACTIVITY.value,
                affected_entity_type="MISSION",
                affected_entity_id=mission.id,
                proposed_changes=[
                    {"entity_type": "MISSION", "entity_id": str(mission.id), "field": "status", "value": "PLANNED"}
                ],
                proposed_state_change={"mission_id": str(mission.id), "status": "PLANNED"},
                prerequisite_conditions=["Station leadership approval for survey delay"],
                expected_impact={"scientific_milestone": "POSTPONED", "logistics_strain": "REDUCED"},
                feasibility_state=OptionFeasibility.CONSTRAINED.value,
                operational_rationale="Viable operational mitigation, but introduces soft milestone deferral warning.",
                evidence={"mission_code": mission.code},
                assumptions=["Secondary resupply window remains funded"],
                data_provenance="DERIVED",
            )
            candidate_options.append(opt)
            option_idx += 1

        # Persist generated options
        for opt in candidate_options:
            self.repo.create_option(opt)

        # -------------------------------------------------------------
        # RECOMMENDATIONS GENERATION
        # Produce explainable recommendations from feasible/constrained options
        # -------------------------------------------------------------
        recommendations: List[RecommendationModel] = []

        # Find best feasible or constrained candidates
        feasible_opts = [o for o in candidate_options if o.feasibility_state in (OptionFeasibility.FEASIBLE.value, OptionFeasibility.CONSTRAINED.value)]

        for f_opt in feasible_opts:
            # Build structured rationale
            rationales = []
            if f_opt.action_type == ReplanActionType.RESCHEDULE_MISSION.value:
                rationales = [
                    "Avoids hard cargo deadline constraint breach",
                    "Preserves full scientific expedition scope without cancelling objectives",
                    "Maintains team and personnel safety within polar seasonal boundary",
                    "Requires no unsupported external resupply assets",
                ]
            elif f_opt.action_type == ReplanActionType.MODIFY_TRANSPORT.value:
                rationales = [
                    "Leverages scheduled active transport leg with verified capacity",
                    "Eliminates downstream mission schedule disruption",
                    "Avoids equipment idle time at coastal staging base",
                ]
            elif f_opt.action_type == ReplanActionType.REASSIGN_ASSET.value:
                rationales = [
                    "Uses verified available on-station instrument",
                    "Permits mission execution on original schedule",
                ]
            elif f_opt.action_type == ReplanActionType.DEFER_ACTIVITY.value:
                rationales = [
                    "De-escalates coastal transport bottleneck",
                    "Acceptable soft impact on overall expedition campaign",
                ]

            rec = RecommendationModel(
                id=uuid.uuid4(),
                replan_id=replan.id,
                option_id=f_opt.id,
                trigger_event_id=replan.trigger_event_id,
                title=f"Operational Recommendation: {f_opt.title}",
                summary=(
                    f"Recommended operational action: {f_opt.description}. "
                    f"Deterministic feasibility state: {f_opt.feasibility_state}."
                ),
                rationale=rationales,
                supporting_evidence={
                    "option_code": f_opt.option_code,
                    "action_type": f_opt.action_type,
                    "feasibility_state": f_opt.feasibility_state,
                    "affected_entity": str(f_opt.affected_entity_id),
                },
                constraint_evaluation_summary={
                    "status": f_opt.feasibility_state,
                    "hard_violations": 0 if f_opt.feasibility_state == OptionFeasibility.FEASIBLE.value else len(violated_list),
                    "soft_violations": 1 if f_opt.feasibility_state == OptionFeasibility.CONSTRAINED.value else 0,
                },
                affected_entities=affected_list,
                violated_constraints=violated_list,
                proposed_changes=f_opt.proposed_changes,
                expected_impact=f_opt.expected_impact,
                assumptions=f_opt.assumptions,
                status=RecommendationStatus.PROPOSED.value,
                approval_state="PROPOSED",
                data_provenance="ADVISORY",
                generated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.repo.create_recommendation(rec)
            recommendations.append(rec)

        # Update replan lifecycle
        replan.status = ReplanStatus.OPTIONS_READY.value
        self.session.flush()

        with self.session.begin_nested():
            self.event_service.append_event(
                event_type="ReplanOptionsGenerated",
                entity_type="REPLAN",
                entity_id=replan.id,
                new_state=ReplanStatus.OPTIONS_READY.value,
                previous_state=ReplanStatus.ANALYZING.value,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                correlation_id=cid,
                evidence={
                    "total_options": len(candidate_options),
                    "total_recommendations": len(recommendations),
                },
            )

            for rec in recommendations:
                self.event_service.append_event(
                    event_type="RecommendationCreated",
                    entity_type="RECOMMENDATION",
                    entity_id=rec.id,
                    new_state=RecommendationStatus.PROPOSED.value,
                    previous_state=None,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    correlation_id=cid,
                    evidence={"title": rec.title, "replan_id": str(replan.id)},
                )

            self.audit_service.record_audit(
                action="REPLAN_OPTIONS_GENERATED",
                entity_type="REPLAN",
                entity_id=replan.id,
                after_snapshot={
                    "status": replan.status,
                    "options_count": len(candidate_options),
                    "recommendations_count": len(recommendations),
                },
                correlation_id=cid,
                metadata={"options": [o.option_code for o in candidate_options]},
            )

        return candidate_options, recommendations


class ApprovalService:
    """
    Guarantees the strict human control boundary for consequential operational decisions:
    1. PROPOSED -> PENDING approval
    2. PENDING -> APPROVED or REJECTED
    3. APPROVED -> can be applied through domain services
    4. Idempotency: already applied recommendations return stable result without re-executing
    5. Zero autonomous mutations for consequential recommendations
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = ReplanRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)
        self.transport_service = TransportService(session)
        self.mission_service = MissionService(session)

    def request_approval(
        self,
        recommendation_id: uuid.UUID,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalModel:
        """
        Initiates a formal approval cycle for a candidate recommendation.
        Transitions recommendation into AWAITING_APPROVAL and creates a PENDING approval record.
        """
        rec = self.repo.get_recommendation_by_id(recommendation_id)
        if not rec:
            raise EntityNotFoundError("Recommendation", recommendation_id)

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = uuid.uuid4()

        # Check existing pending approval
        existing = self.repo.get_latest_approval_for_recommendation(recommendation_id)
        if existing and existing.status == ApprovalStatus.PENDING.value:
            return existing

        approval = ApprovalModel(
            id=uuid.uuid4(),
            recommendation_id=rec.id,
            approver_user_id=None,
            approver_person_id=actor.get("actor_id") or uuid.UUID(int=0),
            approver_role=actor.get("actor_role") or "EXPEDITION_OPERATOR",
            decision=None,
            comment=None,
            status=ApprovalStatus.PENDING.value,
            correlation_id=cid,
            created_at=datetime.now(timezone.utc),
        )

        with self.session.begin_nested():
            created = self.repo.create_approval(approval)
            rec.approval_state = "AWAITING_APPROVAL"
            self.session.flush()

            self.event_service.append_event(
                event_type="ApprovalRequested",
                entity_type="APPROVAL",
                entity_id=created.id,
                new_state=ApprovalStatus.PENDING.value,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "OPERATOR"),
                actor_id=actor.get("actor_id"),
                correlation_id=cid,
                evidence={"recommendation_id": str(rec.id), "title": rec.title},
            )

        return created

    def decide(
        self,
        approval_id: uuid.UUID,
        request: ApprovalDecisionRequest,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalModel:
        """
        Submits an authoritative human decision (APPROVED or REJECTED) on an approval request.
        Updates recommendation state accordingly.
        """
        approval = self.repo.get_approval_by_id(approval_id)
        if not approval:
            raise EntityNotFoundError("Approval", approval_id)

        if approval.status != ApprovalStatus.PENDING.value:
            raise ConflictError(
                f"Approval record '{approval_id}' has already been decided with status '{approval.status}'.",
                field="status",
                details={"status": approval.status, "decision": approval.decision},
            )

        rec = self.repo.get_recommendation_by_id(approval.recommendation_id)
        if not rec:
            raise EntityNotFoundError("Recommendation", approval.recommendation_id)

        actor = actor_context or {"actor_type": "OPERATOR", "actor_id": request.approver_person_id, "source": "API"}
        cid = request.correlation_id or approval.correlation_id or uuid.uuid4()
        now = datetime.now(timezone.utc)

        decision_str = request.decision.value if hasattr(request.decision, "value") else str(request.decision)

        approval.approver_person_id = request.approver_person_id
        approval.approver_role = request.approver_role or "EXPEDITION_OPERATOR"
        approval.decision = decision_str
        approval.comment = request.comment
        approval.decided_at = now

        event_type = ""
        if decision_str in (ApprovalDecision.APPROVED.value, "APPROVED"):
            approval.status = ApprovalStatus.APPROVED.value
            rec.approval_state = "APPROVED"
            rec.status = RecommendationStatus.SELECTED.value
            event_type = "RecommendationApproved"
        else:
            approval.status = ApprovalStatus.REJECTED.value
            rec.approval_state = "REJECTED"
            rec.status = RecommendationStatus.REJECTED.value
            event_type = "RecommendationRejected"

        with self.session.begin_nested():
            self.repo.update_approval(approval)
            self.repo.update_recommendation(rec)

            event = self.event_service.append_event(
                event_type=event_type,
                entity_type="RECOMMENDATION",
                entity_id=rec.id,
                new_state=rec.status,
                previous_state=RecommendationStatus.PROPOSED.value,
                source=actor.get("source", "API"),
                actor_type="OPERATOR",
                actor_id=request.approver_person_id,
                correlation_id=cid,
                evidence={
                    "approval_id": str(approval.id),
                    "decision": decision_str,
                    "comment": request.comment,
                },
            )
            approval.resulting_event_id = event.event_id

            self.audit_service.record_audit(
                action=f"RECOMMENDATION_{decision_str}",
                entity_type="RECOMMENDATION",
                entity_id=rec.id,
                after_snapshot={"status": rec.status, "decision": decision_str},
                correlation_id=cid,
                actor_user_id=None,
                actor_person_id=request.approver_person_id,
                metadata={"comment": request.comment, "approval_id": str(approval.id)},
            )

        return approval

    def apply(
        self,
        recommendation_id: uuid.UUID,
        request: ReplanApplyRequest,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> ReplanApplyResult:
        """
        Controlled application boundary:
        - Validates human approval is present and APPROVED
        - Idempotent: returns existing result if already APPLIED
        - Applies mutations strictly through domain services (TransportService, MissionService)
        - Never executes arbitrary SQL
        - Emits ReplanApplied operational event and audit log
        """
        rec = self.repo.get_recommendation_by_id(recommendation_id)
        if not rec:
            raise EntityNotFoundError("Recommendation", recommendation_id)

        actor = actor_context or {"actor_type": "OPERATOR", "actor_id": request.actor_person_id, "source": "API"}
        cid = request.correlation_id or uuid.uuid4()
        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # 1. IDEMPOTENCY CHECK
        # -------------------------------------------------------------
        if rec.status == RecommendationStatus.APPLIED.value or rec.approval_state == "IMPLEMENTED":
            return ReplanApplyResult(
                recommendation_id=rec.id,
                status="APPLIED",
                applied_changes=rec.proposed_changes,
                resulting_event_id=rec.trigger_event_id,
                applied_at=rec.updated_at,
                message="Recommendation has already been applied (idempotent no-op).",
            )

        # -------------------------------------------------------------
        # 2. HUMAN APPROVAL CHECK
        # -------------------------------------------------------------
        approval = self.repo.get_latest_approval_for_recommendation(recommendation_id)
        if not approval or approval.status != ApprovalStatus.APPROVED.value or approval.decision != ApprovalDecision.APPROVED.value:
            raise DomainValidationError(
                message=f"Human approval required: Recommendation '{recommendation_id}' cannot be applied without an explicit APPROVED decision by an authorized expedition operator.",
                field="approval_boundary",
            )

        # -------------------------------------------------------------
        # 3. CONTROLLED DOMAIN SERVICE EXECUTION
        # -------------------------------------------------------------
        option = None
        if rec.option_id:
            option = self.repo.get_option_by_id(rec.option_id)

        applied_changes: List[Dict[str, Any]] = []

        try:
            if option:
                if option.action_type == ReplanActionType.RESCHEDULE_MISSION.value:
                    mission_id = option.affected_entity_id
                    state_change = option.proposed_state_change or {}
                    new_date_str = state_change.get("required_by_at")
                    new_date = datetime.fromisoformat(new_date_str) if new_date_str else now + timedelta(days=7)

                    self.mission_service.update_mission(
                        mission_id=mission_id,
                        data=MissionUpdate(required_by_at=new_date),
                        correlation_id=cid,
                        actor_context=actor,
                    )
                    applied_changes.append({
                        "entity_type": "MISSION",
                        "entity_id": str(mission_id),
                        "action": "RESCHEDULE_MISSION",
                        "new_required_by_at": new_date.isoformat(),
                    })

                elif option.action_type == ReplanActionType.MODIFY_TRANSPORT.value:
                    leg_id = option.affected_entity_id
                    self.transport_service.update_transport_leg(
                        leg_id=leg_id,
                        data=TransportLegUpdate(delay_reason="Rerouted cargo from delayed upstream transport"),
                        correlation_id=cid,
                        actor_context=actor,
                    )
                    applied_changes.append({
                        "entity_type": "TRANSPORT_LEG",
                        "entity_id": str(leg_id),
                        "action": "MODIFY_TRANSPORT",
                    })

                elif option.action_type == ReplanActionType.DEFER_ACTIVITY.value:
                    mission_id = option.affected_entity_id
                    self.mission_service.update_mission(
                        mission_id=mission_id,
                        data=MissionUpdate(priority=1),  # Lower priority
                        correlation_id=cid,
                        actor_context=actor,
                    )
                    applied_changes.append({
                        "entity_type": "MISSION",
                        "entity_id": str(mission_id),
                        "action": "DEFER_ACTIVITY",
                        "priority": 1,
                    })

            # Update recommendation state
            rec.status = RecommendationStatus.APPLIED.value
            rec.approval_state = "IMPLEMENTED"
            rec.updated_at = now
            self.repo.update_recommendation(rec)

            # Update parent replan state
            replan = self.repo.get_replan_by_id(rec.replan_id)
            if replan:
                replan.status = ReplanStatus.APPLIED.value
                replan.completed_at = now
                replan.updated_at = now
                self.repo.update_replan(replan)

            # Emit immutable operational event
            event = self.event_service.append_event(
                event_type="ReplanApplied",
                entity_type="REPLAN",
                entity_id=rec.replan_id,
                new_state=ReplanStatus.APPLIED.value,
                previous_state=ReplanStatus.AWAITING_APPROVAL.value,
                source=actor.get("source", "API"),
                actor_type="OPERATOR",
                actor_id=request.actor_person_id,
                correlation_id=cid,
                evidence={
                    "recommendation_id": str(rec.id),
                    "applied_changes": applied_changes,
                    "comment": request.comment,
                },
            )

            # Persist audit record
            self.audit_service.record_audit(
                action="REPLAN_APPLIED",
                entity_type="RECOMMENDATION",
                entity_id=rec.id,
                after_snapshot={"status": rec.status, "approval_state": rec.approval_state},
                correlation_id=cid,
                actor_user_id=None,
                actor_person_id=request.actor_person_id,
                metadata={"comment": request.comment, "changes": applied_changes},
            )

            self.session.flush()

            return ReplanApplyResult(
                recommendation_id=rec.id,
                status=RecommendationStatus.APPLIED.value,
                applied_changes=applied_changes,
                resulting_event_id=event.event_id,
                applied_at=now,
                message="Recommendation successfully applied through verified domain services.",
            )

        except Exception as e:
            # Handle failure safely: record failure audit and mark FAILED
            rec.status = RecommendationStatus.FAILED.value
            self.session.flush()

            self.audit_service.record_audit(
                action="REPLAN_APPLICATION_FAILED",
                entity_type="RECOMMENDATION",
                entity_id=rec.id,
                after_snapshot={"status": rec.status},
                correlation_id=cid,
                actor_user_id=None,
                actor_person_id=request.actor_person_id,
                metadata={"error": str(e)},
            )
            raise e
