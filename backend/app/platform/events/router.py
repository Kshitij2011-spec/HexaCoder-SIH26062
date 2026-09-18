"""Operational Events API Endpoints."""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.platform.events.service import EventService
from backend.app.platform.events.schemas import (
    OperationalEventRead,
    OperationalEventFilter,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(tags=["Operational Events"])


@router.get("/events", response_model=ApiResponse)
def list_events(
    request: Request,
    entity_type: Optional[str] = Query(None, description="Filter by target entity type"),
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by target entity ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    correlation_id: Optional[uuid.UUID] = Query(None, description="Filter by correlation ID"),
    occurred_from: Optional[datetime] = Query(None, description="Filter events occurred on or after"),
    occurred_to: Optional[datetime] = Query(None, description="Filter events occurred on or before"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    session: Session = Depends(get_db)
):
    """Lists operational events with pagination and filtering."""
    service = EventService(session)
    filters = OperationalEventFilter(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        correlation_id=correlation_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to
    )
    events, total = service.list_events(filters=filters, page=page, page_size=page_size)

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [OperationalEventRead.model_validate(evt).model_dump() for evt in events]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.get("/events/{event_id}", response_model=ApiResponse)
def get_event(
    event_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves an individual immutable operational event by ID."""
    service = EventService(session)
    event = service.get_event(event_id)
    return create_success_response(
        data=OperationalEventRead.model_validate(event).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/entities/{entity_type}/{entity_id}/events", response_model=ApiResponse)
def get_entity_events(
    entity_type: str,
    entity_id: uuid.UUID,
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    session: Session = Depends(get_db)
):
    """Retrieves chronological operational event journal for a specific domain entity."""
    service = EventService(session)
    events, total = service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [OperationalEventRead.model_validate(evt).model_dump() for evt in events]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )
