"""Personnel API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.people.service import PersonService
from backend.app.domains.people.schemas import (
    PersonCreate,
    PersonUpdate,
    PersonRead,
    PersonReadinessUpdate,
    PersonMovementUpdate,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/people", tags=["People"])


@router.get("", response_model=ApiResponse)
def list_people(
    request: Request,
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by expedition ID"),
    team_id: Optional[uuid.UUID] = Query(None, description="Filter by team ID"),
    readiness_state: Optional[str] = Query(None, description="Filter by qualification state (e.g. READY, NOMINATED)"),
    movement_state: Optional[str] = Query(None, description="Filter by transit state (e.g. AT_STATION, FIELD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists expedition personnel with optional team, expedition, and state filters."""
    service = PersonService(session)
    people, total = service.list_people(
        expedition_id=expedition_id,
        team_id=team_id,
        readiness_state=readiness_state,
        movement_state=movement_state,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [PersonRead.model_validate(p).model_dump() for p in people]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    data: PersonCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Enrolls personnel into an expedition and emits a PersonNominated event."""
    service = PersonService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_person(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=PersonRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{person_id}", response_model=ApiResponse)
def get_person(
    person_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves personnel record by ID."""
    service = PersonService(session)
    person = service.get_person(person_id)
    return create_success_response(
        data=PersonRead.model_validate(person).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{person_id}", response_model=ApiResponse)
def update_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates general personnel attributes or performs readiness/movement state transitions."""
    service = PersonService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_person(
        person_id=person_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=PersonRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{person_id}/readiness", response_model=ApiResponse)
def update_person_readiness(
    person_id: uuid.UUID,
    data: PersonReadinessUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Executes a dedicated readiness/clearance state transition (e.g. NOMINATED -> READY)."""
    service = PersonService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_readiness(
        person_id=person_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=PersonRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{person_id}/movement", response_model=ApiResponse)
def update_person_movement(
    person_id: uuid.UUID,
    data: PersonMovementUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Executes a dedicated movement/transit transition (e.g. AT_STATION -> FIELD)."""
    service = PersonService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_movement(
        person_id=person_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=PersonRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
