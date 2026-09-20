"""FastAPI Router for Operational Control Tower Endpoints."""

import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.domains.control_tower.service import ControlTowerService
from backend.app.domains.control_tower.schemas import (
    ControlTowerOverview,
    ExpeditionControlSummary,
    MissionOperationsItem,
    OperationalEventFeedItem,
    ControlTowerConstraintItem,
    DecisionQueueSummary,
    ConsequentialActionItem,
    ScenarioInjectRequest,
    ScenarioInjectResult,
    IncidentEscalationRequest,
    IncidentEscalationResult,
    IncidentContextView,
    ResourceRunwaySummary,
    PersonnelPostureSummary,
)
from backend.app.domains.control_tower.scenarios import ScenarioInjectionService
from backend.app.domains.control_tower.incident_escalation import IncidentEscalationService
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(tags=["Operational Control Tower"])


@router.get("/overview/fast", response_model=ApiResponse[ControlTowerOverview])
def get_control_tower_overview_fast(
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter overview to a single expedition"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    High-performance initial Control Tower command posture endpoint.
    Aggregates active campaigns, mission rollups, active incidents, critical constraints,
    pending replans/approvals, and offline sync in <=8 batched queries without deep recursive sweeps.
    """
    service = ControlTowerService(db)
    overview = service.get_fast_overview(expedition_id=expedition_id)
    return create_success_response(
        data=overview,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/overview", response_model=ApiResponse[ControlTowerOverview])
def get_control_tower_overview(
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter overview to a single expedition"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Returns global operational posture across campaigns:
    readiness distributions, active incidents, critical violated constraints,
    pending replans/approvals, sync status, and recent events.
    """
    service = ControlTowerService(db)
    overview = service.get_overview(expedition_id=expedition_id)
    return create_success_response(
        data=overview,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/expeditions/{expedition_id}", response_model=ApiResponse[ExpeditionControlSummary])
def get_expedition_control_summary(
    expedition_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Returns expedition-specific operational posture, readiness rollup, and blocker summaries."""
    service = ControlTowerService(db)
    summary = service.get_expedition_summary(expedition_id=expedition_id)
    return create_success_response(
        data=summary,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/expeditions/{expedition_id}/runways", response_model=ApiResponse[ResourceRunwaySummary])
def get_expedition_runways(
    expedition_id: uuid.UUID,
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by storage location"),
    category: Optional[str] = Query(None, description="Filter by category (FUEL, RATIONS, etc.)"),
    criticality: Optional[str] = Query(None, description="Filter by criticality tier"),
    lookback_days: int = Query(default=14, ge=1, le=90, description="Observation window in days"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Evaluates consumable resource runways, daily burn rates, and resupply deficit gaps
    for an expedition campaign without simulating SCADA or telemetry.
    """
    service = ControlTowerService(db)
    summary = service.get_expedition_runways(
        expedition_id=expedition_id,
        location_id=location_id,
        category=category,
        criticality=criticality,
        lookback_days=lookback_days,
    )
    return create_success_response(
        data=summary,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/expeditions/{expedition_id}/personnel-safety", response_model=ApiResponse[PersonnelPostureSummary])
def get_expedition_personnel_safety(
    expedition_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Evaluates personnel deployment safety, team staffing compliance, and medical clearance posture
    for an expedition campaign using deterministic domain invariants.
    """
    service = ControlTowerService(db)
    summary = service.get_personnel_safety(expedition_id=expedition_id)
    return create_success_response(
        data=summary,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/expeditions/{expedition_id}/missions", response_model=ApiResponse[List[MissionOperationsItem]])
def get_mission_operations_view(
    expedition_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter missions by lifecycle status"),
    readiness: Optional[str] = Query(None, description="Filter missions by derived readiness (READY, AT_RISK, BLOCKED, UNKNOWN)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Provides mission-level operational context, derived readiness, blockers, warnings, and violated constraints."""
    service = ControlTowerService(db)
    items, total = service.get_mission_operations_view(
        expedition_id=expedition_id,
        status=status,
        readiness=readiness,
        page=page,
        page_size=page_size,
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
    )
    return create_success_response(
        data=items,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination,
    )


@router.get("/expeditions/{expedition_id}/events", response_model=ApiResponse[List[OperationalEventFeedItem]])
def get_operational_events_feed(
    expedition_id: uuid.UUID,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    from_time: Optional[datetime] = Query(None, description="Filter events occurred on or after"),
    to_time: Optional[datetime] = Query(None, description="Filter events occurred on or before"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Provides an immutable chronological operational event timeline for an expedition."""
    service = ControlTowerService(db)
    items, total = service.get_events_feed(
        expedition_id=expedition_id,
        entity_type=entity_type,
        event_type=event_type,
        from_time=from_time,
        to_time=to_time,
        page=page,
        page_size=page_size,
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
    )
    return create_success_response(
        data=items,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination,
    )


@router.get("/expeditions/{expedition_id}/constraints", response_model=ApiResponse[List[ControlTowerConstraintItem]])
def get_active_constraints_view(
    expedition_id: uuid.UUID,
    state: Optional[str] = Query(None, description="Filter by evaluation state (SATISFIED, VIOLATED, NOT_EVALUABLE)"),
    hard_or_soft: Optional[str] = Query(None, description="Filter by HARD or SOFT"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Exposes active operational constraints with explicit deterministic tri-state evaluation outcomes."""
    service = ControlTowerService(db)
    items, total = service.get_active_constraints(
        expedition_id=expedition_id,
        state=state,
        hard_or_soft=hard_or_soft,
        page=page,
        page_size=page_size,
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
    )
    return create_success_response(
        data=items,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination,
    )


@router.get("/expeditions/{expedition_id}/decisions", response_model=ApiResponse[DecisionQueueSummary])
def get_decision_queue_view(
    expedition_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Unified operator decision queue: pending replans, candidate recommendations, and pending approvals."""
    service = ControlTowerService(db)
    decisions = service.get_decision_queue(expedition_id=expedition_id)
    return create_success_response(
        data=decisions,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/expeditions/{expedition_id}/audit", response_model=ApiResponse[List[ConsequentialActionItem]])
def get_consequential_actions_audit(
    expedition_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Provides an auditable timeline of recent human approval decisions and operational applications."""
    service = ControlTowerService(db)
    items, total = service.get_recent_actions(
        expedition_id=expedition_id,
        page=page,
        page_size=page_size,
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
    )
    return create_success_response(
        data=items,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination,
    )


@router.post("/scenarios/inject", response_model=ApiResponse[ScenarioInjectResult])
def inject_operational_scenario(
    payload: ScenarioInjectRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Injects a deterministic benchmark disruption scenario (FLIGHT_GROUNDING, GENERATOR_FAILURE, COLD_CHAIN_EXCURSION).
    Enforces dynamic entity discovery, expedition isolation, safe idempotency, and strict human-in-the-loop control.
    Does NOT autonomously create replans or apply mutations.
    """
    service = ScenarioInjectionService(db)
    result = service.inject(payload)
    return create_success_response(
        data=result,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


# ---------------------------------------------------------------------------
# Incident Escalation Bridge Endpoints (A7)
# ---------------------------------------------------------------------------

@router.post("/incidents/{incident_id}/escalate", response_model=ApiResponse[IncidentEscalationResult])
def escalate_incident_to_replan(
    incident_id: uuid.UUID,
    payload: Optional[IncidentEscalationRequest] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Escalates an active operational incident to Control Tower replanning.
    Calculates downstream blast-radius, identifies impacted missions and violated constraints,
    and idempotently creates or retrieves an incident-linked replan (REQUESTED state).
    Strictly preserves human governance: does NOT approve or apply.
    """
    service = IncidentEscalationService(db)
    cid_header = request.headers.get("X-Request-ID") if request else None
    actor_header = request.headers.get("X-Actor-ID") if request else None
    cid = None
    if payload and payload.correlation_id:
        cid = payload.correlation_id
    elif cid_header:
        try:
            cid = uuid.UUID(cid_header)
        except ValueError:
            cid = None

    actor_id = None
    if payload and payload.requested_by:
        actor_id = payload.requested_by
    elif actor_header:
        try:
            actor_id = uuid.UUID(actor_header)
        except ValueError:
            actor_id = None

    expedition_id = payload.expedition_id if payload else None
    depth = payload.depth if payload else 3

    result = service.escalate_incident(
        incident_id=incident_id,
        expedition_id=expedition_id,
        requested_by=actor_id,
        depth=depth,
        correlation_id=cid,
    )
    return create_success_response(
        data=result,
        correlation_id=result.correlation_id or cid_header,
    )


@router.get("/incidents/{incident_id}/context", response_model=ApiResponse[IncidentContextView])
def get_incident_escalation_context(
    incident_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Returns rich operational context for an escalated incident to display
    in the Control Tower escalation context banner.
    """
    service = IncidentEscalationService(db)
    context = service.get_incident_context(incident_id)
    return create_success_response(
        data=context,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )

