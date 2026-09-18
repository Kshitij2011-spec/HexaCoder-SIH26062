"""Expedition API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.expeditions.service import ExpeditionService
from backend.app.domains.expeditions.schemas import (
    ExpeditionCreate,
    ExpeditionUpdate,
    ExpeditionRead,
    ExpeditionSummary,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/expeditions", tags=["Expeditions"])


@router.get("", response_model=ApiResponse)
def list_expeditions(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status (e.g. ACTIVE, DRAFT)"),
    season: Optional[str] = Query(None, description="Filter by operational season (e.g. 2026-2027)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists expeditions with optional status and season filters."""
    service = ExpeditionService(session)
    expeditions, total = service.list_expeditions(status=status, season=season, page=page, page_size=page_size)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [ExpeditionRead.model_validate(e).model_dump() for e in expeditions]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_expedition(
    data: ExpeditionCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Creates a new polar expedition campaign and emits an ExpeditionCreated operational event."""
    service = ExpeditionService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_expedition(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=ExpeditionRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{expedition_id}", response_model=ApiResponse)
def get_expedition(
    expedition_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves an expedition by ID."""
    service = ExpeditionService(session)
    expedition = service.get_expedition(expedition_id)
    return create_success_response(
        data=ExpeditionRead.model_validate(expedition).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{expedition_id}", response_model=ApiResponse)
def update_expedition(
    expedition_id: uuid.UUID,
    data: ExpeditionUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates expedition attributes or executes a validated lifecycle state transition."""
    service = ExpeditionService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_expedition(
        expedition_id=expedition_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=ExpeditionRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{expedition_id}/summary", response_model=ApiResponse)
def get_expedition_summary(
    expedition_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Returns an aggregate operational overview of missions, teams, personnel, and events."""
    service = ExpeditionService(session)
    summary = service.get_summary(expedition_id)
    return create_success_response(
        data=summary.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
