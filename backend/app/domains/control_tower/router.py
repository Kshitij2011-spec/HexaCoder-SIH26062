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
)
from backend.app.domains.control_tower.scenarios import ScenarioInjectionService
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(tags=["Operational Control Tower"])


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

