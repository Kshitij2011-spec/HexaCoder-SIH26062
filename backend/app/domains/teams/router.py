"""Teams API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.teams.service import TeamService
from backend.app.domains.teams.schemas import TeamCreate, TeamUpdate, TeamRead
from backend.app.domains.people.schemas import PersonRead
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=ApiResponse)
def list_teams(
    request: Request,
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by expedition ID"),
    status: Optional[str] = Query(None, description="Filter by team status (e.g. FORMING, READY)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists functional teams with optional expedition and status filters."""
    service = TeamService(session)
    teams, total = service.list_teams(
        expedition_id=expedition_id,
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
    data = [TeamRead.model_validate(t).model_dump() for t in teams]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Forms a new expedition team and emits a TeamCreated operational event."""
    service = TeamService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_team(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=TeamRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{team_id}", response_model=ApiResponse)
def get_team(
    team_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves team details by ID."""
    service = TeamService(session)
    team = service.get_team(team_id)
    return create_success_response(
        data=TeamRead.model_validate(team).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{team_id}", response_model=ApiResponse)
def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates team attributes or transitions its lifecycle state."""
    service = TeamService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_team(
        team_id=team_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=TeamRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{team_id}/members", response_model=ApiResponse)
def get_team_members(
    team_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves all personnel currently assigned to this team."""
    service = TeamService(session)
    members = service.get_team_members(team_id)
    data = [PersonRead.model_validate(m).model_dump() for m in members]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID")
    )
