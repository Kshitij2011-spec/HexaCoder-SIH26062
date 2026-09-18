"""Cargo API Router (Consignments, Packages, Timelines)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.cargo.service import CargoService
from backend.app.domains.cargo.schemas import (
    CargoConsignmentCreate,
    CargoConsignmentUpdate,
    CargoConsignmentRead,
    CargoConsignmentDetailRead,
    CargoPackageCreate,
    CargoPackageUpdate,
    CargoPackageRead,
    CargoTimelineRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)
from backend.app.core.security import get_current_actor

router = APIRouter(prefix="/cargo", tags=["Cargo"])


# ------------------------------------------------------------
# Consignment Endpoints
# ------------------------------------------------------------

@router.get("/consignments", response_model=ApiResponse)
def list_consignments(
    request: Request,
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by expedition"),
    status: Optional[str] = Query(None, description="Filter by cargo status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    origin_location_id: Optional[uuid.UUID] = Query(None, description="Filter by origin location"),
    destination_location_id: Optional[uuid.UUID] = Query(None, description="Filter by destination location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists cargo consignments with optional operational filters and pagination."""
    service = CargoService(session)
    items, total = service.list_consignments(
        expedition_id=expedition_id,
        status=status,
        risk_level=risk_level,
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
    data = [CargoConsignmentRead.model_validate(c).model_dump() for c in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("/consignments", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_consignment(
    data: CargoConsignmentCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Manifests a new cargo consignment shipment and emits CargoConsignmentCreated."""
    service = CargoService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_consignment(data=data, correlation_id=cid, actor_context=actor)
    return create_success_response(
        data=CargoConsignmentRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/consignments/{consignment_id}", response_model=ApiResponse)
def get_consignment(
    consignment_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves full cargo consignment details including child packages and risk profile."""
    service = CargoService(session)
    consignment = service.get_consignment(consignment_id)
    return create_success_response(
        data=CargoConsignmentDetailRead.model_validate(consignment).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/consignments/{consignment_id}", response_model=ApiResponse)
def update_consignment(
    consignment_id: uuid.UUID,
    data: CargoConsignmentUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates cargo consignment metadata or lifecycle status with deterministic risk recalculation."""
    service = CargoService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_consignment(
        consignment_id=consignment_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=CargoConsignmentRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/consignments/{consignment_id}/timeline", response_model=ApiResponse)
def get_consignment_timeline(
    consignment_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves operational timeline, remaining delivery buffer hours, and delivery health."""
    service = CargoService(session)
    timeline = service.get_timeline(consignment_id)
    return create_success_response(
        data=timeline.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


# ------------------------------------------------------------
# Package Endpoints
# ------------------------------------------------------------

@router.post("/consignments/{consignment_id}/packages", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_package(
    consignment_id: uuid.UUID,
    data: CargoPackageCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Adds a physical item/package to an existing cargo consignment."""
    service = CargoService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    created = service.create_package(
        consignment_id=consignment_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=CargoPackageRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/consignments/{consignment_id}/packages", response_model=ApiResponse)
def list_consignment_packages(
    consignment_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Lists all physical packages manifested within a cargo consignment."""
    service = CargoService(session)
    packages = service.list_packages_by_consignment(consignment_id)
    data = [CargoPackageRead.model_validate(p).model_dump() for p in packages]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/packages/{package_id}", response_model=ApiResponse)
def get_package(
    package_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves physical package details."""
    service = CargoService(session)
    pkg = service.get_package(package_id)
    return create_success_response(
        data=CargoPackageRead.model_validate(pkg).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/packages/{package_id}", response_model=ApiResponse)
def update_package(
    package_id: uuid.UUID,
    data: CargoPackageUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates physical package state, condition, or location assignment."""
    service = CargoService(session)
    actor = get_current_actor(request)
    cid_header = request.headers.get("X-Request-ID")
    cid = uuid.UUID(cid_header) if cid_header else None

    updated = service.update_package(
        package_id=package_id,
        data=data,
        correlation_id=cid,
        actor_context=actor
    )
    return create_success_response(
        data=CargoPackageRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
