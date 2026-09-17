"""Mission API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.missions.service import MissionService
from backend.app.domains.missions.schemas import (
    MissionCreate,
    MissionUpdate,
    MissionRead,
    MissionRelationshipRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/missions", tags=["Missions"])


@router.get("", response_model=ApiResponse)
def list_missions(
    request: Request,
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by parent expedition ID"),
    status: Optional[str] = Query(None, description="Filter by mission status"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    session: Session = Depends(get_db)
):
    """Lists missions with filtering and pagination."""
    service = MissionService(session)
    missions, total = service.list_missions(
        expedition_id=expedition_id,
        status=status,
        priority=priority,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [MissionRead.model_validate(m).model_dump() for m in missions]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_mission(
    data: MissionCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Creates a new mission and emits a MissionProposed operational event."""
    service = MissionService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_mission(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=MissionRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{mission_id}", response_model=ApiResponse)
def get_mission(
    mission_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves a mission by ID."""
    service = MissionService(session)
    mission = service.get_mission(mission_id)
    return create_success_response(
        data=MissionRead.model_validate(mission).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{mission_id}", response_model=ApiResponse)
def update_mission(
    mission_id: uuid.UUID,
    data: MissionUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates mission details or executes a validated lifecycle state transition."""
    service = MissionService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_mission(
        mission_id=mission_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=MissionRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{mission_id}/relationships", response_model=ApiResponse)
def get_mission_relationships(
    mission_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """
    Exposes generic semantic dependency relationships involving this mission.
    Used by cross-domain readers and dependency graphs.
    """
    service = MissionService(session)
    relationships = service.get_relationships(mission_id)
    return create_success_response(
        data=relationships,
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{mission_id}/time-windows", response_model=ApiResponse)
def get_mission_time_windows(
    mission_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Exposes time windows associated with this mission."""
    service = MissionService(session)
    windows = service.get_time_windows(mission_id)
    return create_success_response(
        data=windows,
        correlation_id=request.headers.get("X-Request-ID")
    )
