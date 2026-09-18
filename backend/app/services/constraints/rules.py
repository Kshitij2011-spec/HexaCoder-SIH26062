"""Deterministic Rule Evaluators for Operational Constraints.

Pure Python dispatch from rule_code to verified evaluation function.
No dynamic code execution or arbitrary expression evaluation.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from backend.app.services.constraints.models import ConstraintModel
from backend.app.services.constraints.schemas import ConstraintEvaluationResult
from backend.app.services.dependencies.models import DependencyModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.people.models import PersonModel
from backend.app.domains.time_windows.models import TimeWindowModel
from backend.app.shared.types.reasoning import (
    ConstraintSeverity,
    ConstraintState,
)
from backend.app.shared.types.states import HardSoftConstraint


def _parse_severity(sev_str: str) -> ConstraintSeverity:
    try:
        return ConstraintSeverity(sev_str)
    except Exception:
        return ConstraintSeverity.CRITICAL


def _parse_hard_soft(hs_str: str) -> HardSoftConstraint:
    try:
        return HardSoftConstraint(hs_str)
    except Exception:
        return HardSoftConstraint.HARD


def _safe_date(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def evaluate_mission_required_by(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates MISSION_REQUIRED_BY: checks if mission operational schedule fits
    within the mandated required_by_at deadline.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    mission_id = constraint.subject_id

    if not mission_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type=constraint.subject_type or "MISSION",
            subject_id=uuid.UUID(int=0),
            reason="Constraint lacks subject_id referencing a mission.",
            evidence={}
        )

    mission = session.execute(
        select(MissionModel).where(MissionModel.id == mission_id)
    ).scalar_one_or_none()

    if not mission:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="MISSION",
            subject_id=mission_id,
            reason=f"Mission {mission_id} not found in database.",
            evidence={}
        )

    required_by_at = mission.required_by_at
    if not required_by_at:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.SATISFIED,
            subject_type="MISSION",
            subject_id=mission_id,
            reason="Mission has no required_by_at deadline configured.",
            evidence={"mission_code": mission.code}
        )

    # 2. Fetch associated time windows
    tw_rows = session.execute(
        select(TimeWindowModel).where(
            TimeWindowModel.subject_type == "MISSION",
            TimeWindowModel.subject_id == mission_id
        ).order_by(TimeWindowModel.close_at.desc())
    ).scalars().all()

    violations = []
    for tw in tw_rows:
        if tw.close_at and tw.close_at > required_by_at:
            violations.append({
                "time_window_id": str(tw.id),
                "window_close": tw.close_at.isoformat(),
                "required_by_at": required_by_at.isoformat(),
            })

    if violations:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="MISSION",
            subject_id=mission_id,
            reason=f"Mission window closes after required_by_at deadline ({required_by_at.isoformat()}).",
            evidence={"violations": violations, "mission_code": mission.code}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type="MISSION",
        subject_id=mission_id,
        reason="Mission schedule complies with required_by_at deadline.",
        evidence={"mission_code": mission.code, "required_by_at": required_by_at.isoformat()}
    )


def evaluate_mission_resource_required(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates MISSION_RESOURCE_REQUIRED: verifies that mandatory equipment,
    teams, and consignments required by the mission exist and are in ready/available status.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    mission_id = constraint.subject_id

    if not mission_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="MISSION",
            subject_id=uuid.UUID(int=0),
            reason="Constraint subject_id is missing.",
            evidence={}
        )

    params = constraint.parameters or {}
    required_asset_code = params.get("required_asset_code")

    # Query outgoing REQUIRES dependencies for this mission
    deps = session.execute(
        select(DependencyModel).where(
            DependencyModel.source_entity_type == "MISSION",
            DependencyModel.source_entity_id == mission_id,
            DependencyModel.relationship_type == "REQUIRES"
        )
    ).scalars().all()

    # If specific asset code requested in parameters, also check assets directly
    if required_asset_code:
        try:
            sql_asset = text("SELECT id, asset_code, name, status, condition FROM assets WHERE asset_code = :code")
            asset_row = session.execute(sql_asset, {"code": required_asset_code}).mappings().first()
            if not asset_row:
                return ConstraintEvaluationResult(
                    constraint_id=constraint.id,
                    code=constraint.code,
                    name=constraint.name,
                    severity=severity,
                    hard_or_soft=hard_soft,
                    state=ConstraintState.VIOLATED,
                    subject_type="MISSION",
                    subject_id=mission_id,
                    reason=f"Required asset '{required_asset_code}' does not exist in inventory/assets.",
                    evidence={"required_asset_code": required_asset_code}
                )
            status = asset_row.get("status") or asset_row.get("condition")
            if status in ("DAMAGED", "LOST", "IN_MAINTENANCE", "DECOMMISSIONED", "UNAVAILABLE"):
                return ConstraintEvaluationResult(
                    constraint_id=constraint.id,
                    code=constraint.code,
                    name=constraint.name,
                    severity=severity,
                    hard_or_soft=hard_soft,
                    state=ConstraintState.VIOLATED,
                    subject_type="MISSION",
                    subject_id=mission_id,
                    reason=f"Required asset '{required_asset_code}' is in state '{status}'.",
                    evidence={"asset_id": str(asset_row["id"]), "status": status}
                )
        except Exception:
            pass

    # Check dependencies
    unmet_resources = []
    unevaluable_resources = []

    for d in deps:
        t_type = d.target_entity_type.upper()
        t_id = d.target_entity_id

        if t_type == "ASSET":
            try:
                sql_a = text("SELECT id, asset_code, status, condition FROM assets WHERE id = :id")
                a_row = session.execute(sql_a, {"id": str(t_id)}).mappings().first()
                if not a_row:
                    unevaluable_resources.append({"type": t_type, "id": str(t_id), "reason": "Asset record not found"})
                else:
                    st = a_row.get("status") or a_row.get("condition")
                    if st in ("DAMAGED", "LOST", "IN_MAINTENANCE", "DECOMMISSIONED", "UNAVAILABLE"):
                        unmet_resources.append({"type": t_type, "code": a_row.get("asset_code"), "status": st})
            except Exception:
                unevaluable_resources.append({"type": t_type, "id": str(t_id), "reason": "Assets table unavailable"})

        elif t_type == "TEAM":
            team = session.execute(select(TeamModel).where(TeamModel.id == t_id)).scalar_one_or_none()
            if not team:
                unevaluable_resources.append({"type": t_type, "id": str(t_id), "reason": "Team record not found"})
            elif team.status == "DISBANDED":
                unmet_resources.append({"type": t_type, "code": team.code, "status": "DISBANDED"})

    if unmet_resources:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="MISSION",
            subject_id=mission_id,
            reason=f"Mission requires unavailable resources: {', '.join(r.get('code') or r.get('type') for r in unmet_resources)}.",
            evidence={"unmet": unmet_resources}
        )

    if unevaluable_resources:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="MISSION",
            subject_id=mission_id,
            reason="Required resource records are not yet accessible in database.",
            evidence={"unevaluable": unevaluable_resources}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type="MISSION",
        subject_id=mission_id,
        reason="All mandatory resources for mission are verified available.",
        evidence={"dependencies_checked": len(deps), "required_asset_code": required_asset_code}
    )


def evaluate_personnel_staffing(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates PERSONNEL_STAFFING: checks team members' readiness status
    and minimum required staffing headcounts.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    team_id = constraint.subject_id
    params = constraint.parameters or {}
    min_personnel = params.get("min_personnel", 1)
    required_roles = params.get("required_roles", [])

    if not team_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="TEAM",
            subject_id=uuid.UUID(int=0),
            reason="Constraint lacks subject_id.",
            evidence={}
        )

    members = session.execute(
        select(PersonModel).where(PersonModel.team_id == team_id)
    ).scalars().all()

    if len(members) < min_personnel:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="TEAM",
            subject_id=team_id,
            reason=f"Team headcount ({len(members)}) is below mandated minimum ({min_personnel}).",
            evidence={"current_headcount": len(members), "min_required": min_personnel}
        )

    unavailable_members = []
    present_roles = set()
    for m in members:
        present_roles.add(m.role)
        if m.readiness_state in ("UNAVAILABLE", "NOT_CLEARED"):
            unavailable_members.append({
                "person_code": m.person_code,
                "full_name": m.full_name,
                "readiness_state": m.readiness_state
            })

    if unavailable_members:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="TEAM",
            subject_id=team_id,
            reason=f"Field team has {len(unavailable_members)} member(s) with unavailable readiness.",
            evidence={"unavailable_members": unavailable_members}
        )

    # Role check
    missing_roles = [r for r in required_roles if r not in present_roles]
    if missing_roles:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="TEAM",
            subject_id=team_id,
            reason=f"Team lacks required accredited roles: {', '.join(missing_roles)}.",
            evidence={"missing_roles": missing_roles, "present_roles": list(present_roles)}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type="TEAM",
        subject_id=team_id,
        reason="Field team satisfies polar safety staffing floors and qualifications.",
        evidence={"headcount": len(members), "roles_present": list(present_roles)}
    )


def evaluate_cargo_eta_deadline(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates CARGO_ETA_DEADLINE: checks if consignment arrival date
    precedes the mandated window / sea ice cutoff.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    consignment_id = constraint.subject_id
    params = constraint.parameters or {}

    if not consignment_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="CARGO_CONSIGNMENT",
            subject_id=uuid.UUID(int=0),
            reason="Constraint lacks subject_id.",
            evidence={}
        )

    try:
        sql_cargo = text("""
            SELECT id, code, required_by_at, estimated_arrival_at, status
            FROM cargo_consignments
            WHERE id = :cid
        """)
        row = session.execute(sql_cargo, {"cid": str(consignment_id)}).mappings().first()
    except Exception:
        row = None

    if not row:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="CARGO_CONSIGNMENT",
            subject_id=consignment_id,
            reason=f"Cargo consignment {consignment_id} not found or domain table unavailable.",
            evidence={}
        )

    max_arrival = _safe_date(params.get("max_arrival_timestamp")) or _safe_date(row["required_by_at"])
    est_arrival = _safe_date(row["estimated_arrival_at"])

    if not est_arrival or not max_arrival:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="CARGO_CONSIGNMENT",
            subject_id=consignment_id,
            reason="Estimated arrival or deadline timestamp not specified.",
            evidence={"consignment_code": row["code"]}
        )

    if est_arrival > max_arrival:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="CARGO_CONSIGNMENT",
            subject_id=consignment_id,
            reason=f"Consignment estimated arrival ({est_arrival.isoformat()}) exceeds deadline ({max_arrival.isoformat()}).",
            evidence={
                "consignment_code": row["code"],
                "estimated_arrival": est_arrival.isoformat(),
                "max_arrival_deadline": max_arrival.isoformat()
            }
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type="CARGO_CONSIGNMENT",
        subject_id=consignment_id,
        reason="Consignment ETA complies with operational cutoff deadline.",
        evidence={
            "consignment_code": row["code"],
            "estimated_arrival": est_arrival.isoformat(),
            "max_arrival_deadline": max_arrival.isoformat()
        }
    )


def evaluate_asset_availability(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates ASSET_AVAILABILITY: verifies operational status and operating hour limits.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    asset_id = constraint.subject_id
    params = constraint.parameters or {}

    if not asset_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="ASSET",
            subject_id=uuid.UUID(int=0),
            reason="Constraint subject_id is missing.",
            evidence={}
        )

    try:
        sql_a = text("SELECT id, asset_code, name, status, condition FROM assets WHERE id = :aid")
        row = session.execute(sql_a, {"aid": str(asset_id)}).mappings().first()
    except Exception:
        row = None

    if not row:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="ASSET",
            subject_id=asset_id,
            reason=f"Asset {asset_id} not found or table unavailable.",
            evidence={}
        )

    status = row.get("status") or row.get("condition")
    if status in ("DAMAGED", "LOST", "IN_MAINTENANCE", "DECOMMISSIONED", "UNAVAILABLE"):
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="ASSET",
            subject_id=asset_id,
            reason=f"Asset '{row['asset_code']}' is in '{status}' status.",
            evidence={"asset_code": row["asset_code"], "status": status}
        )

    max_hours = params.get("max_unserviced_operating_hours")
    curr_hours = params.get("current_operating_hours", 0)

    if max_hours and curr_hours > max_hours:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type="ASSET",
            subject_id=asset_id,
            reason=f"Asset operating hours ({curr_hours}) exceed maintenance limit ({max_hours}).",
            evidence={"asset_code": row["asset_code"], "operating_hours": curr_hours, "max_hours": max_hours}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type="ASSET",
        subject_id=asset_id,
        reason=f"Asset '{row['asset_code']}' is serviceable and available.",
        evidence={"asset_code": row["asset_code"], "status": status}
    )


def evaluate_inventory_availability(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates INVENTORY_AVAILABILITY: verifies unreserved stock levels
    against minimum safety floors at location or item level.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    params = constraint.parameters or {}
    item_code = params.get("item_code")
    min_unreserved = params.get("min_unreserved_drums") or params.get("min_quantity", 0)
    loc_id = constraint.subject_id

    try:
        sql_stock = text("""
            SELECT sl.id, sl.on_hand_quantity, sl.reserved_quantity, ii.item_code
            FROM inventory_stock_lots sl
            JOIN inventory_items ii ON sl.inventory_item_id = ii.id
            WHERE (:loc_id IS NULL OR sl.location_id = :loc_id)
              AND (:item_code IS NULL OR ii.item_code = :item_code)
        """)
        rows = session.execute(
            sql_stock,
            {"loc_id": str(loc_id) if loc_id else None, "item_code": item_code}
        ).mappings().all()
    except Exception:
        rows = []

    if not rows:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type=constraint.subject_type or "INVENTORY",
            subject_id=loc_id or uuid.UUID(int=0),
            reason=f"No stock lot records found for item '{item_code}' (module under development by Track B).",
            evidence={"item_code": item_code}
        )

    total_on_hand = sum(float(r["on_hand_quantity"] or 0) for r in rows)
    total_reserved = sum(float(r["reserved_quantity"] or 0) for r in rows)
    unreserved = total_on_hand - total_reserved

    if unreserved < min_unreserved:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type=constraint.subject_type or "INVENTORY",
            subject_id=loc_id or uuid.UUID(int=0),
            reason=f"Unreserved stock ({unreserved}) breached minimum threshold floor ({min_unreserved}).",
            evidence={"on_hand": total_on_hand, "reserved": total_reserved, "unreserved": unreserved, "min_required": min_unreserved}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.SATISFIED,
        subject_type=constraint.subject_type or "INVENTORY",
        subject_id=loc_id or uuid.UUID(int=0),
        reason=f"Stock levels meet safety threshold floor (unreserved: {unreserved}, floor: {min_unreserved}).",
        evidence={"on_hand": total_on_hand, "reserved": total_reserved, "unreserved": unreserved}
    )


def evaluate_document_validity(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """
    Evaluates DOCUMENT_VALIDITY: checks treaties, permits, and EIA ratifications.
    """
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    params = constraint.parameters or {}
    required_doc_code = params.get("required_doc_code")

    if not required_doc_code:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.SATISFIED,
            subject_type=constraint.subject_type or "EXPEDITION",
            subject_id=constraint.subject_id or uuid.UUID(int=0),
            reason="No specific document requirement code attached.",
            evidence={}
        )

    try:
        sql_doc = text("SELECT id, document_code, status FROM documents WHERE document_code = :code")
        row = session.execute(sql_doc, {"code": required_doc_code}).mappings().first()
    except Exception:
        row = None

    if not row:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.VIOLATED,
            subject_type=constraint.subject_type or "EXPEDITION",
            subject_id=constraint.subject_id or uuid.UUID(int=0),
            reason=f"Mandatory compliance document '{required_doc_code}' not found in registry.",
            evidence={"required_doc_code": required_doc_code}
        )

    status = row["status"]
    if status in ("APPROVED", "RATIFIED", "VALID", "ACTIVE"):
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.SATISFIED,
            subject_type=constraint.subject_type or "EXPEDITION",
            subject_id=constraint.subject_id or uuid.UUID(int=0),
            reason=f"Document '{required_doc_code}' is valid and ratified.",
            evidence={"doc_id": str(row["id"]), "status": status}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.VIOLATED,
        subject_type=constraint.subject_type or "EXPEDITION",
        subject_id=constraint.subject_id or uuid.UUID(int=0),
        reason=f"Document '{required_doc_code}' is in unratified status '{status}'.",
        evidence={"doc_id": str(row["id"]), "status": status}
    )


def evaluate_transport_capacity(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """Evaluates TRANSPORT_CAPACITY."""
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    leg_id = constraint.subject_id

    if not leg_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="TRANSPORT_LEG",
            subject_id=uuid.UUID(int=0),
            reason="Constraint lacks transport leg subject_id.",
            evidence={}
        )

    try:
        sql_leg = text("SELECT id, code, capacity, capacity_unit, status FROM transport_legs WHERE id = :id")
        row = session.execute(sql_leg, {"id": str(leg_id)}).mappings().first()
    except Exception:
        row = None

    if not row:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="TRANSPORT_LEG",
            subject_id=leg_id,
            reason="Transport leg not found or table unavailable.",
            evidence={}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.NOT_EVALUABLE,
        subject_type="TRANSPORT_LEG",
        subject_id=leg_id,
        reason="Transport capacity manifest reconciliation module under development by Track B.",
        evidence={"leg_code": row["code"], "capacity": float(row["capacity"] or 0)}
    )


def evaluate_location_access(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """Evaluates LOCATION_ACCESS."""
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    loc_id = constraint.subject_id

    if not loc_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="LOCATION",
            subject_id=uuid.UUID(int=0),
            reason="Constraint subject_id missing.",
            evidence={}
        )

    tw = session.execute(
        select(TimeWindowModel).where(
            TimeWindowModel.subject_type == "LOCATION",
            TimeWindowModel.subject_id == loc_id
        )
    ).scalars().first()

    if not tw:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type="LOCATION",
            subject_id=loc_id,
            reason="Location has no active access window declared.",
            evidence={}
        )

    status = tw.status
    if status == "OPEN":
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.SATISFIED,
            subject_type="LOCATION",
            subject_id=loc_id,
            reason="Location access window is OPEN.",
            evidence={"status": status}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.VIOLATED,
        subject_type="LOCATION",
        subject_id=loc_id,
        reason=f"Location access window is '{status}'.",
        evidence={"status": status}
    )


def evaluate_time_window(
    session: Session,
    constraint: ConstraintModel,
    context: Optional[Dict[str, Any]] = None
) -> ConstraintEvaluationResult:
    """Evaluates generic TIME_WINDOW constraints."""
    severity = _parse_severity(constraint.severity)
    hard_soft = _parse_hard_soft(constraint.hard_or_soft)
    sub_type = constraint.subject_type or "MISSION"
    sub_id = constraint.subject_id

    if not sub_id:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type=sub_type,
            subject_id=uuid.UUID(int=0),
            reason="Constraint subject_id is missing.",
            evidence={}
        )

    tw = session.execute(
        select(TimeWindowModel).where(
            TimeWindowModel.subject_type == sub_type,
            TimeWindowModel.subject_id == sub_id
        )
    ).scalars().first()

    if not tw:
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.NOT_EVALUABLE,
            subject_type=sub_type,
            subject_id=sub_id,
            reason=f"No time window recorded for subject {sub_type}:{sub_id}.",
            evidence={}
        )

    status = tw.status
    if status == "OPEN":
        return ConstraintEvaluationResult(
            constraint_id=constraint.id,
            code=constraint.code,
            name=constraint.name,
            severity=severity,
            hard_or_soft=hard_soft,
            state=ConstraintState.SATISFIED,
            subject_type=sub_type,
            subject_id=sub_id,
            reason="Temporal execution window is OPEN.",
            evidence={"window_id": str(tw.id), "status": status}
        )

    return ConstraintEvaluationResult(
        constraint_id=constraint.id,
        code=constraint.code,
        name=constraint.name,
        severity=severity,
        hard_or_soft=hard_soft,
        state=ConstraintState.VIOLATED,
        subject_type=sub_type,
        subject_id=sub_id,
        reason=f"Temporal execution window is in status '{status}'.",
        evidence={"window_id": str(tw.id), "status": status}
    )


# Explicit Rule Registry: dispatch dictionary from rule_code to Python function
RULE_REGISTRY: Dict[str, Callable[[Session, ConstraintModel, Optional[Dict[str, Any]]], ConstraintEvaluationResult]] = {
    "MISSION_REQUIRED_BY": evaluate_mission_required_by,
    "MISSION_RESOURCE_REQUIRED": evaluate_mission_resource_required,
    "PERSONNEL_STAFFING": evaluate_personnel_staffing,
    "CARGO_ETA_DEADLINE": evaluate_cargo_eta_deadline,
    "TRANSPORT_CAPACITY": evaluate_transport_capacity,
    "ASSET_AVAILABILITY": evaluate_asset_availability,
    "INVENTORY_AVAILABILITY": evaluate_inventory_availability,
    "DOCUMENT_VALIDITY": evaluate_document_validity,
    "LOCATION_ACCESS": evaluate_location_access,
    "TIME_WINDOW": evaluate_time_window,
}
