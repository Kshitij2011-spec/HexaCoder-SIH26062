"""Transport API Router (Legs, Manifest Assignments, Delay Propagation)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.transport.service import TransportService
from backend.app.domains.transport.schemas import (
    TransportLegCreate,
    TransportLegUpdate,
    TransportLegDelayRequest,
    TransportLegRead,
    TransportCargoAssignmentCreate,
    TransportCargoAssignmentRead,
    TransportDelayImpactResponse,
)
from backend.app.domains.cargo.schemas import CargoConsignmentRead
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/transport", tags=["Transport"])


@router.get("/legs", response_model=ApiResponse)
def list_transport_legs(
    request: Request,
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by expedition"),
    mode: Optional[str] = Query(None, description="Filter by mode e.g. VESSEL, AIR"),
    status: Optional[str] = Query(None, description="Filter by status e.g. IN_TRANSIT, DELAYED"),
    origin_location_id: Optional[uuid.UUID] = Query(None, description="Filter by origin location"),
    destination_location_id: Optional[uuid.UUID] = Query(None, description="Filter by destination location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists transport legs with optional operational filters and pagination."""
    service = TransportService(session)
    items, total = service.list_transport_legs(
        expedition_id=expedition_id,
        mode=mode,
        status=status,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [TransportLegRead.model_validate(leg).model_dump() for leg in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("/legs", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_transport_leg(
    data: TransportLegCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Creates a new transport leg segment and emits TransportLegCreated."""
    service = TransportService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_transport_leg(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=TransportLegRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/legs/{leg_id}", response_model=ApiResponse)
def get_transport_leg(
    leg_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves full transport leg details by ID."""
    service = TransportService(session)
    leg = service.get_transport_leg(leg_id)
    return create_success_response(
        data=TransportLegRead.model_validate(leg).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/legs/{leg_id}", response_model=ApiResponse)
def update_transport_leg(
    leg_id: uuid.UUID,
    data: TransportLegUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates transport leg schedule or executes validated state transition."""
    service = TransportService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_transport_leg(
        leg_id=leg_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=TransportLegRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/legs/{leg_id}/delay", response_model=ApiResponse)
def record_transport_delay(
    leg_id: uuid.UUID,
    data: TransportLegDelayRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """
    Records an operational delay on a transport leg and deterministically propagates ETA
    and risk updates to all manifested cargo consignments.
    """
    service = TransportService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated_leg, affected_consignments = service.record_transport_delay(
        leg_id=leg_id,
        delay_data=data,
        correlation_id=cid,
        actor_context=actor
    )

    impact_response = TransportDelayImpactResponse(
        transport_leg=TransportLegRead.model_validate(updated_leg),
        affected_cargo_consignments=[CargoConsignmentRead.model_validate(c) for c in affected_consignments],
        summary=(
            f"Transport leg {updated_leg.code} delayed until {updated_leg.estimated_arrival_at.isoformat()}. "
            f"Propagated operational impact to {len(affected_consignments)} cargo consignment(s)."
        )
    )

    return create_success_response(
        data=impact_response.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/legs/{leg_id}/cargo", response_model=ApiResponse)
def list_transport_cargo(
    leg_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Lists all cargo consignments actively manifested on this transport leg."""
    service = TransportService(session)
    consignments = service.list_cargo_for_transport_leg(leg_id)
    data = [CargoConsignmentRead.model_validate(c).model_dump() for c in consignments]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/legs/{leg_id}/assign-cargo", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def assign_cargo_to_transport(
    leg_id: uuid.UUID,
    data: TransportCargoAssignmentCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Associates a cargo consignment with a transport leg manifest (Cargo MOVES_VIA Transport)."""
    service = TransportService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    assignment = service.assign_cargo_to_transport(
        transport_leg_id=leg_id,
        cargo_consignment_id=data.cargo_consignment_id,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=TransportCargoAssignmentRead.model_validate(assignment).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
