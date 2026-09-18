"""FastAPI REST Router for Incidents and Incident References."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.incidents.service import IncidentService
from backend.app.domains.incidents.schemas import (
    IncidentCreate,
    IncidentUpdate,
    IncidentRead,
    IncidentStatusTransitionRequest,
    IncidentReferenceCreate,
    IncidentReferenceRead,
    IncidentTimelineRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def _extract_cid(request: Request) -> Optional[uuid.UUID]:
    cid_header = request.headers.get("X-Request-ID")
    if cid_header:
        try:
            return uuid.UUID(cid_header)
        except ValueError:
            return None
    return None


def _extract_actor(request: Request) -> Optional[uuid.UUID]:
    actor_header = request.headers.get("X-Actor-ID")
    if actor_header:
        try:
            return uuid.UUID(actor_header)
        except ValueError:
            return None
    return None


# ============================================================
# 1. INCIDENT CRUD
# ============================================================

@router.get("", response_model=ApiResponse)
def list_incidents(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status e.g. OPEN, ACKNOWLEDGED"),
    severity: Optional[str] = Query(None, description="Filter by severity e.g. LOW, HIGH, CRITICAL"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority integer 1 to 5"),
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by location UUID"),
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by affected asset UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db),
):
    """Lists operational incidents with optional filtering and pagination."""
    service = IncidentService(session)
    items, total = service.list_incidents(
        status=status,
        severity=severity,
        priority=priority,
        location_id=location_id,
        asset_id=asset_id,
        page=page,
        page_size=page_size,
    )
    data = [IncidentRead.model_validate(item).model_dump() for item in items]
    return create_success_response(
        data=data,
        pagination=PaginationMeta(page=page, page_size=page_size, total_items=total),
        correlation_id=request.headers.get("X-Request-ID"),
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    request: Request,
    payload: IncidentCreate,
    session: Session = Depends(get_db),
):
    """Registers a new operational incident in OPEN status."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    created = service.create_incident(payload, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(created).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


@router.get("/{incident_id}", response_model=ApiResponse)
def get_incident(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Retrieves operational incident details by ID."""
    service = IncidentService(session)
    incident = service.get_incident(incident_id)
    return create_success_response(
        data=IncidentRead.model_validate(incident).model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


@router.patch("/{incident_id}", response_model=ApiResponse)
def update_incident(
    request: Request,
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    session: Session = Depends(get_db),
):
    """Updates mutable incident metadata. Strictly blocked on CLOSED incidents."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.update_incident(incident_id, payload, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


# ============================================================
# 2. LIFECYCLE OPERATIONS
# ============================================================

@router.post("/{incident_id}/transition", response_model=ApiResponse)
def transition_incident(
    request: Request,
    incident_id: uuid.UUID,
    payload: IncidentStatusTransitionRequest,
    session: Session = Depends(get_db),
):
    """Transitions incident status according to the authoritative lifecycle state machine."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.transition_incident_status(
        incident_id=incident_id,
        target_status=payload.status,
        reason=payload.reason,
        operational_metadata=payload.operational_metadata,
        correlation_id=cid,
        actor_person_id=actor_id,
    )
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


@router.post("/{incident_id}/acknowledge", response_model=ApiResponse)
def acknowledge_incident(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Transitions incident from OPEN to ACKNOWLEDGED, populating acknowledged_at timestamp."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.acknowledge_incident(incident_id, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


@router.post("/{incident_id}/mitigate", response_model=ApiResponse)
def mitigate_incident(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Transitions incident from ACKNOWLEDGED to MITIGATING."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.mitigate_incident(incident_id, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


@router.post("/{incident_id}/resolve", response_model=ApiResponse)
def resolve_incident(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Transitions incident to RESOLVED, populating resolved_at timestamp."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.resolve_incident(incident_id, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


@router.post("/{incident_id}/close", response_model=ApiResponse)
def close_incident(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Transitions incident to terminal CLOSED, populating closed_at timestamp."""
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    updated = service.close_incident(incident_id, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentRead.model_validate(updated).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )


# ============================================================
# 3. INCIDENT TIMELINE
# ============================================================

@router.get("/{incident_id}/timeline", response_model=ApiResponse)
def get_incident_timeline(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Retrieves chronological timeline of events, status transitions, and attached references."""
    service = IncidentService(session)
    timeline = service.get_incident_timeline(incident_id)
    return create_success_response(
        data=timeline.model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 4. AFFECTED RESOURCE REFERENCES
# ============================================================

@router.get("/{incident_id}/references", response_model=ApiResponse)
def list_incident_references(
    request: Request,
    incident_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Lists operational resource references attached to an incident."""
    service = IncidentService(session)
    refs = service.list_references(incident_id)
    data = [IncidentReferenceRead.model_validate(r).model_dump() for r in refs]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
    )


@router.post("/{incident_id}/references", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def add_incident_reference(
    request: Request,
    incident_id: uuid.UUID,
    payload: IncidentReferenceCreate,
    session: Session = Depends(get_db),
):
    """
    Attaches an operational resource reference to the incident.
    STRICT ISOLATION: Does NOT mutate the referenced entity state.
    """
    service = IncidentService(session)
    cid = _extract_cid(request)
    actor_id = _extract_actor(request)
    ref = service.add_reference(incident_id, payload, correlation_id=cid, actor_person_id=actor_id)
    return create_success_response(
        data=IncidentReferenceRead.model_validate(ref).model_dump(),
        correlation_id=str(cid) if cid else request.headers.get("X-Request-ID"),
    )
