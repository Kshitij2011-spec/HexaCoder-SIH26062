"""Location API Router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.locations.service import LocationService
from backend.app.domains.locations.schemas import (
    LocationCreate,
    LocationUpdate,
    LocationStatusUpdate,
    LocationRead,
    LocationHierarchyRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("", response_model=ApiResponse)
def list_locations(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by location type (e.g. PORT, STATION)"),
    status: Optional[str] = Query(None, description="Filter by operational status (e.g. AVAILABLE)"),
    parent_location_id: Optional[uuid.UUID] = Query(None, description="Filter by parent location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists operational facilities and locations with optional filters."""
    service = LocationService(session)
    items, total = service.list_locations(
        type_=type,
        status=status,
        parent_location_id=parent_location_id,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [LocationRead.model_validate(loc).model_dump() for loc in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    data: LocationCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Registers a new operational facility or logistics node and emits LocationCreated event."""
    service = LocationService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_location(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=LocationRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{location_id}", response_model=ApiResponse)
def get_location(
    location_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves detailed operational location record by ID."""
    service = LocationService(session)
    loc = service.get_location(location_id)
    return create_success_response(
        data=LocationRead.model_validate(loc).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{location_id}", response_model=ApiResponse)
def update_location(
    location_id: uuid.UUID,
    data: LocationUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates location attributes or executes validated operational lifecycle state transition."""
    service = LocationService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_location(
        location_id=location_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=LocationRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{location_id}/state", response_model=ApiResponse)
def update_location_state(
    location_id: uuid.UUID,
    data: LocationStatusUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Executes a validated operational status transition (e.g. AVAILABLE -> RESTRICTED/INACCESSIBLE)."""
    service = LocationService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_location_state(
        location_id=location_id,
        new_status=data.status.value,
        reason=data.reason,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=LocationRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{location_id}/hierarchy", response_model=ApiResponse)
def get_location_hierarchy(
    location_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves operational facility hierarchy including full ancestral lineage and child sub-locations."""
    service = LocationService(session)
    hierarchy = service.get_hierarchy(location_id)
    return create_success_response(
        data=hierarchy.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
