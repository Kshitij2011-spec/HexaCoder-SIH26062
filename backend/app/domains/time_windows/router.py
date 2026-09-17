"""Time Windows API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.time_windows.service import TimeWindowService
from backend.app.domains.time_windows.schemas import (
    TimeWindowCreate,
    TimeWindowUpdate,
    TimeWindowRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/time-windows", tags=["Time Windows"])


@router.get("", response_model=ApiResponse)
def list_time_windows(
    request: Request,
    subject_type: Optional[str] = Query(None, description="Filter by subject type e.g. MISSION, EXPEDITION"),
    subject_id: Optional[uuid.UUID] = Query(None, description="Filter by subject entity ID"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. OPEN, CLOSED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists temporal constraint windows with optional subject and status filters."""
    service = TimeWindowService(session)
    windows, total = service.list_time_windows(
        subject_type=subject_type,
        subject_id=subject_id,
        status=status,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [TimeWindowRead.model_validate(w).model_dump() for w in windows]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_time_window(
    data: TimeWindowCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Creates a temporal constraint window (flight/weather/cargo) and emits a TimeWindowCreated event."""
    service = TimeWindowService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_time_window(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=TimeWindowRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{window_id}", response_model=ApiResponse)
def get_time_window(
    window_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves time window details by ID."""
    service = TimeWindowService(session)
    window = service.get_time_window(window_id)
    return create_success_response(
        data=TimeWindowRead.model_validate(window).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{window_id}", response_model=ApiResponse)
def update_time_window(
    window_id: uuid.UUID,
    data: TimeWindowUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates time window boundaries or status."""
    service = TimeWindowService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_time_window(
        window_id=window_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=TimeWindowRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
