"""Incident-to-Replanning Operational Escalation Bridge (Milestone A7).

Coordinates cross-domain incident response and the Control Tower replanning engine:
1. Validates incident operational lifecycle status (rejects CLOSED).
2. Enforces expedition boundary and tenant isolation.
3. Inspects propagated impacts across referenced locations, assets, and transport legs.
4. Traverses semantic dependencies via ImpactService to determine affected missions and constraints.
5. Idempotently creates or retrieves an incident-linked operational Replan (REQUESTED state).
6. Preserves correlation IDs, audit logs, and operational event chains.
7. Strictly preserves human governance (NO autonomous approval or mutation).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.domains.incidents.service import IncidentService
from backend.app.domains.incidents.propagation import IncidentPropagationService
from backend.app.domains.incidents.states import IncidentStatus
from backend.app.domains.replanning.service import ReplanService
from backend.app.domains.replanning.models import ReplanModel
from backend.app.domains.replanning.states import ReplanStatus, TERMINAL_REPLAN_STATUSES
from backend.app.domains.replanning.schemas import ReplanTriggerRequest
from backend.app.services.impact.service import ImpactService
from backend.app.services.constraints.service import ConstraintService
from backend.app.shared.types.reasoning import ConstraintState
from backend.app.domains.control_tower.schemas import (
    IncidentEscalationResult,
    IncidentContextView,
)
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.assets.models import AssetModel
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import (
    EntityNotFoundError,
    DomainValidationError,
    ConflictError,
)


class IncidentEscalationService:
    """
    Public domain orchestrator for escalating an active operational incident
    into the Control Tower replanning and decision engine.
    """

    def __init__(self, session: Session):
        self.session = session
        self.incident_service = IncidentService(session)
        self.propagation_service = IncidentPropagationService(session)
        self.impact_service = ImpactService(session)
        self.constraint_service = ConstraintService(session)
        self.replan_service = ReplanService(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def escalate_incident(
        self,
        incident_id: uuid.UUID,
        expedition_id: Optional[uuid.UUID] = None,
        requested_by: Optional[uuid.UUID] = None,
        depth: int = 3,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None,
    ) -> IncidentEscalationResult:
        """
        Escalates an active operational incident into a Control Tower replan.

        Invariants enforced:
        - Validates incident exists and is not CLOSED.
        - Respects expedition isolation.
        - Idempotent: returns existing active replan if previously escalated.
        - Emits ReplanRequested event without approving or applying.
        """
        cid = correlation_id or uuid.uuid4()

        # 1. Load and validate incident
        incident = self.incident_service.get_incident(incident_id)
        if not incident:
            raise EntityNotFoundError("Incident", incident_id)

        # 2. Lifecycle validation
        if incident.status == IncidentStatus.CLOSED.value:
            raise ConflictError(
                f"Cannot escalate CLOSED incident '{incident.incident_code}'. Incident is in a terminal state.",
                field="status",
                details={"status": incident.status, "incident_code": incident.incident_code},
            )
        if incident.status not in (
            IncidentStatus.OPEN.value,
            IncidentStatus.ACKNOWLEDGED.value,
            IncidentStatus.MITIGATING.value,
        ):
            raise ConflictError(
                f"Incident '{incident.incident_code}' in status '{incident.status}' cannot be escalated. Incident must be active (OPEN, ACKNOWLEDGED, or MITIGATING).",
                field="status",
                details={"status": incident.status, "incident_code": incident.incident_code},
            )

        # 3. Expedition isolation
        target_expedition_id = expedition_id or incident.expedition_id
        if expedition_id and incident.expedition_id and incident.expedition_id != expedition_id:
            raise DomainValidationError(
                f"Incident '{incident.incident_code}' belongs to expedition '{incident.expedition_id}', not '{expedition_id}'.",
                field="expedition_id",
            )

        # 4. Idempotency Check: Return existing active replan if present
        #    CROSS-DOMAIN READ (ReplanModel): Direct query required for idempotency
        #    check — no public ReplanService method exists that queries by
        #    trigger_entity_type + trigger_entity_id + non-terminal status.
        active_replan_stmt = (
            select(ReplanModel)
            .where(
                ReplanModel.trigger_entity_type == "INCIDENT",
                ReplanModel.trigger_entity_id == incident.id,
                ReplanModel.status.not_in([s.value for s in TERMINAL_REPLAN_STATUSES]),
            )
            .order_by(ReplanModel.created_at.desc())
        )
        existing_replan = self.session.execute(active_replan_stmt).scalars().first()
        if existing_replan:
            aff_missions = [
                aff for aff in (existing_replan.affected_entities or [])
                if aff.get("entity_type") == "MISSION"
            ]
            return IncidentEscalationResult(
                incident_id=incident.id,
                incident_code=incident.incident_code,
                incident_title=incident.title,
                incident_severity=incident.severity,
                incident_status=incident.status,
                expedition_id=existing_replan.expedition_id,
                replan_id=existing_replan.id,
                replan_code=existing_replan.replan_code,
                replan_status=existing_replan.status,
                affected_entities=existing_replan.affected_entities or [],
                violated_constraints=existing_replan.violated_constraints or [],
                affected_missions_count=len(aff_missions),
                violated_constraints_count=len(existing_replan.violated_constraints or []),
                is_existing=True,
                correlation_id=str(existing_replan.correlation_id or cid),
                data_provenance="DERIVED",
            )

        # 5. Inspect existing propagations & references
        refs = self.incident_service.list_references(incident.id)
        props = self.propagation_service.list_propagations(incident.id)
        if refs and len(props) == 0:
            # Trigger cross-domain impact propagation if unpropagated references exist
            self.propagation_service.propagate_incident_impact(
                incident.id, correlation_id=cid, actor_person_id=requested_by
            )
            props = self.propagation_service.list_propagations(incident.id)

        # 6. Build unified blast-radius across incident references and dependencies
        seed_targets: List[Tuple[str, uuid.UUID]] = [("INCIDENT", incident.id)]
        if incident.asset_id:
            seed_targets.append(("ASSET", incident.asset_id))
        if incident.location_id:
            seed_targets.append(("LOCATION", incident.location_id))
        for p in props:
            seed_targets.append((p.reference_type, p.reference_id))
        for r in refs:
            seed_targets.append((r.reference_type, r.reference_id))

        seen_seeds: Set[Tuple[str, uuid.UUID]] = set()
        unique_seeds: List[Tuple[str, uuid.UUID]] = []
        for st in seed_targets:
            if st not in seen_seeds:
                seen_seeds.add(st)
                unique_seeds.append(st)

        merged_affected: Dict[Tuple[str, str], Dict[str, Any]] = {}
        merged_constraints: Dict[str, Dict[str, Any]] = {}

        # Include direct seeds in affected entities for replanning visibility
        for st_type, st_id in unique_seeds:
            if st_type != "INCIDENT":
                merged_affected[(st_type, str(st_id))] = {
                    "entity_type": st_type,
                    "entity_id": str(st_id),
                    "relationship": "INCIDENT_REFERENCE",
                    "depth": 1,
                    "direction": "DIRECT",
                    "reason": f"Directly referenced by incident {incident.incident_code}",
                }

        # Traverse semantic dependencies from seeds.
        # ISSUE-1 FIX: Impact engine failures MUST propagate as domain errors.
        # If dependency traversal or constraint evaluation fails, the system
        # must not silently produce an incomplete blast radius and proceed
        # to create a replan based on partial/missing impact data.
        _logger = logging.getLogger(__name__)
        impact_failures: List[Dict[str, Any]] = []
        for st_type, st_id in unique_seeds:
            try:
                impact_res = self.impact_service.calculate_impact(
                    entity_type=st_type,
                    entity_id=st_id,
                    change_summary=f"Incident {incident.incident_code} escalation: {incident.title}",
                    depth=depth,
                    correlation_id=cid,
                )
                for aff in impact_res.affected_entities:
                    key = (aff.entity_type, str(aff.entity_id))
                    if key not in merged_affected:
                        merged_affected[key] = aff.model_dump()
                for c in impact_res.constraint_candidates:
                    if c.state == ConstraintState.VIOLATED:
                        c_dict = c.model_dump()
                        c_id = str(c_dict.get("constraint_id") or c_dict.get("code"))
                        if c_id not in merged_constraints:
                            merged_constraints[c_id] = c_dict
            except (DomainValidationError, EntityNotFoundError):
                # Known domain errors (e.g. seed entity not in dependency graph)
                # are non-fatal — the seed simply contributes no additional
                # downstream impact beyond its direct reference entry.
                _logger.warning(
                    "Impact calculation returned domain error for seed (%s, %s) "
                    "during incident %s escalation — seed skipped.",
                    st_type, st_id, incident.incident_code,
                )
            except Exception as exc:
                # Infrastructure / unexpected failures are collected and
                # surfaced after all seeds are attempted, to give the operator
                # maximum diagnostic context.
                impact_failures.append({
                    "seed_type": st_type,
                    "seed_id": str(st_id),
                    "error": str(exc),
                })
                _logger.error(
                    "Impact engine failure for seed (%s, %s) during incident %s "
                    "escalation: %s",
                    st_type, st_id, incident.incident_code, exc,
                    exc_info=True,
                )

        if impact_failures:
            raise DomainValidationError(
                message=(
                    f"Impact analysis failed for {len(impact_failures)} of "
                    f"{len(unique_seeds)} seed entities during escalation of "
                    f"incident '{incident.incident_code}'. Cannot produce a "
                    f"reliable blast radius for replanning."
                ),
                field="impact_analysis",
                code="IMPACT_ENGINE_FAILURE",
                details={
                    "incident_code": incident.incident_code,
                    "incident_id": str(incident.id),
                    "failures": impact_failures,
                    "total_seeds": len(unique_seeds),
                    "failed_seeds": len(impact_failures),
                },
            )

        affected_entities_list = list(merged_affected.values())
        violated_constraints_list = list(merged_constraints.values())

        # 7. Identify impacted missions and primary mission
        aff_missions = [
            a for a in affected_entities_list if a.get("entity_type") == "MISSION"
        ]
        primary_mission_id = uuid.UUID(str(aff_missions[0]["entity_id"])) if aff_missions else None

        # 8. Resolve target expedition — STRICT resolution order:
        #    explicit expedition_id → incident.expedition_id → primary mission's expedition_id
        #    If none resolves, reject the escalation. An incident escalation
        #    must NEVER choose an arbitrary expedition.
        if not target_expedition_id and primary_mission_id:
            #  CROSS-DOMAIN READ (MissionModel): Read-only lookup to resolve
            #  the expedition boundary from the first affected mission. No
            #  public MissionService.get_expedition_id() method exists.
            m_ent = self.session.get(MissionModel, primary_mission_id)
            if m_ent and m_ent.expedition_id:
                target_expedition_id = m_ent.expedition_id
        if not target_expedition_id:
            raise DomainValidationError(
                message=(
                    f"Cannot resolve expedition for incident '{incident.incident_code}'. "
                    f"Provide an explicit expedition_id, or ensure the incident or its "
                    f"affected missions are associated with a valid expedition."
                ),
                field="expedition_id",
                code="EXPEDITION_UNRESOLVABLE",
                details={
                    "incident_code": incident.incident_code,
                    "incident_id": str(incident.id),
                    "incident_expedition_id": str(incident.expedition_id) if incident.expedition_id else None,
                    "primary_mission_id": str(primary_mission_id) if primary_mission_id else None,
                },
            )

        # 9. Create operational replan request (REQUESTED state, no autonomous approval/apply)
        req_by_uuid = None
        if requested_by:
            if isinstance(requested_by, uuid.UUID):
                req_by_uuid = requested_by
            elif isinstance(requested_by, str):
                try:
                    req_by_uuid = uuid.UUID(requested_by)
                except ValueError:
                    req_by_uuid = None

        trigger_req = ReplanTriggerRequest(
            trigger_mode="INCIDENT_ESCALATION",
            expedition_id=target_expedition_id,
            mission_id=primary_mission_id,
            incident_id=incident.id,
            trigger_entity_type="INCIDENT",
            trigger_entity_id=incident.id,
            reason=f"Incident Escalation [{incident.incident_code}]: {incident.title} ({incident.severity})",
            requested_by=req_by_uuid,
            correlation_id=cid,
            depth=depth,
        )
        actor_ctx = actor_context or {
            "actor_type": "OPERATOR" if requested_by else "SYSTEM",
            "actor_id": req_by_uuid,
            "source": "INCIDENT_ESCALATION_BRIDGE",
        }
        replan = self.replan_service.create_replan_request(
            trigger_req, actor_context=actor_ctx, auto_commit=False
        )

        # Merge discovered blast-radius into the replan
        existing_aff = {(a["entity_type"], str(a["entity_id"])) for a in (replan.affected_entities or [])}
        combined_affected = list(replan.affected_entities or [])
        for a in affected_entities_list:
            if (a["entity_type"], str(a["entity_id"])) not in existing_aff:
                combined_affected.append(a)
                existing_aff.add((a["entity_type"], str(a["entity_id"])))

        existing_c = {str(c.get("constraint_id") or c.get("code")) for c in (replan.violated_constraints or [])}
        combined_constraints = list(replan.violated_constraints or [])
        for c in violated_constraints_list:
            c_key = str(c.get("constraint_id") or c.get("code"))
            if c_key not in existing_c:
                combined_constraints.append(c)
                existing_c.add(c_key)

        replan.affected_entities = combined_affected
        replan.violated_constraints = combined_constraints
        replan.current_state_evidence = {
            "trigger_mode": "INCIDENT_ESCALATION",
            "incident_id": str(incident.id),
            "incident_code": incident.incident_code,
            "incident_title": incident.title,
            "incident_severity": incident.severity,
            "incident_status": incident.status,
            "location_id": str(incident.location_id) if incident.location_id else None,
            "asset_id": str(incident.asset_id) if incident.asset_id else None,
            "total_propagations": len(props),
            "total_affected_entities": len(combined_affected),
            "total_violated_constraints": len(combined_constraints),
            "reason": replan.trigger_reason,
            "data_provenance": "DERIVED",
        }

        # 10. Audit log for escalation
        self.audit_service.record_audit(
            action="INCIDENT_ESCALATED_TO_REPLAN",
            entity_type="INCIDENT",
            entity_id=incident.id,
            after_snapshot={
                "replan_id": str(replan.id),
                "replan_code": replan.replan_code,
                "replan_status": replan.status,
                "affected_entities_count": len(combined_affected),
                "violated_constraints_count": len(combined_constraints),
            },
            correlation_id=cid,
            actor_user_id=None,
            actor_person_id=req_by_uuid,
            metadata={
                "incident_code": incident.incident_code,
                "replan_code": replan.replan_code,
                "expedition_id": str(target_expedition_id),
                "requested_by": str(requested_by) if requested_by else None,
            },
        )

        self.session.commit()

        return IncidentEscalationResult(
            incident_id=incident.id,
            incident_code=incident.incident_code,
            incident_title=incident.title,
            incident_severity=incident.severity,
            incident_status=incident.status,
            expedition_id=replan.expedition_id,
            replan_id=replan.id,
            replan_code=replan.replan_code,
            replan_status=replan.status,
            affected_entities=combined_affected,
            violated_constraints=combined_constraints,
            affected_missions_count=len(aff_missions),
            violated_constraints_count=len(combined_constraints),
            is_existing=False,
            correlation_id=str(cid),
            data_provenance="DERIVED",
        )

    def get_incident_context(self, incident_id: uuid.UUID) -> IncidentContextView:
        """
        Retrieves rich operational context for an incident to display
        in the Control Tower escalation context banner.
        """
        incident = self.incident_service.get_incident(incident_id)
        if not incident:
            raise EntityNotFoundError("Incident", incident_id)

        # CROSS-DOMAIN READ (LocationModel): Read-only lookup for display
        # context in the escalation banner. No public LocationService.get_code()
        # method exists; the incident already owns the location_id FK.
        loc_code = None
        loc_name = None
        if incident.location_id:
            loc = self.session.get(LocationModel, incident.location_id)
            if loc:
                loc_code = loc.code
                loc_name = loc.name

        # CROSS-DOMAIN READ (AssetModel): Read-only lookup for display context.
        # No public AssetService.get_code() method exists.
        asset_code = None
        if incident.asset_id:
            ast = self.session.get(AssetModel, incident.asset_id)
            if ast:
                asset_code = ast.asset_code

        props = self.propagation_service.list_propagations(incident.id)

        # CROSS-DOMAIN READ (ReplanModel): Direct query for linked replan to
        # populate the context banner. Same justification as the idempotency
        # check in escalate_incident — no public ReplanService query method
        # supports this filter combination.
        active_replan_stmt = (
            select(ReplanModel)
            .where(
                ReplanModel.trigger_entity_type == "INCIDENT",
                ReplanModel.trigger_entity_id == incident.id,
                ReplanModel.status.not_in([s.value for s in TERMINAL_REPLAN_STATUSES]),
            )
            .order_by(ReplanModel.created_at.desc())
        )
        linked_replan = self.session.execute(active_replan_stmt).scalars().first()

        aff_entities: list[dict[str, Any]] = []
        violated_constraints: list[dict[str, Any]] = []
        correlation_id = None

        if linked_replan:
            aff_entities = linked_replan.affected_entities or []
            violated_constraints = linked_replan.violated_constraints or []
            correlation_id = str(linked_replan.correlation_id) if linked_replan.correlation_id else None
        else:
            # Preview blast radius from incident domain references and seeds
            for p in props:
                aff_entities.append({
                    "entity_type": p.target_entity_type,
                    "entity_id": str(p.target_entity_id),
                    "relationship": p.propagation_type,
                    "impact_score": p.impact_score,
                })

        aff_missions = [
            a for a in aff_entities
            if a.get("entity_type") == "MISSION"
        ]

        if aff_entities or props:
            prop_summary = (
                f"Blast radius propagated across {len(aff_entities)} operational entities "
                f"and {len(aff_missions)} active missions."
            )
        else:
            prop_summary = (
                f"Incident impact localized to {loc_name or loc_code or 'current sector'}; "
                "blast radius evaluated across polar logistics network."
            )

        return IncidentContextView(
            incident_id=incident.id,
            incident_code=incident.incident_code,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            incident_type=incident.incident_type,
            location_id=incident.location_id,
            location_code=loc_code,
            location_name=loc_name,
            asset_id=incident.asset_id,
            asset_code=asset_code,
            expedition_id=incident.expedition_id,
            detected_at=incident.detected_at,
            description=incident.description,
            propagation_summary=prop_summary,
            propagations_count=len(props),
            affected_entities=aff_entities,
            affected_missions=aff_missions,
            affected_constraints=violated_constraints,
            affected_entities_count=len(aff_entities),
            affected_missions_count=len(aff_missions),
            violated_constraints_count=len(violated_constraints),
            replan_id=linked_replan.id if linked_replan else None,
            replan_code=linked_replan.replan_code if linked_replan else None,
            correlation_id=correlation_id,
            data_provenance="DERIVED",
        )
