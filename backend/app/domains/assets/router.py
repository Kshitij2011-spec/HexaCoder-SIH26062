"""FastAPI REST Router for Assets and Maintenance."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.assets.service import AssetService
from backend.app.domains.assets.schemas import (
    AssetCreate,
    AssetUpdate,
    AssetRead,
    AssetStatusTransitionRequest,
    AssetMoveRequest,
    MaintenanceScheduleRequest,
    MaintenanceStartRequest,
    MaintenanceCompleteRequest,
    MaintenanceCancelRequest,
    MaintenanceRecordRead,
    AssetTimelineRead,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


def _extract_cid(request: Request) -> Optional[uuid.UUID]:
    cid_header = request.headers.get("X-Request-ID")
    if cid_header:
        try:
            return uuid.UUID(cid_header)
        except ValueError:
            return None
    return None


# ============================================================
# 1. ASSET CRUD & LIFECYCLE
# ============================================================

@router.get("", response_model=ApiResponse)
def list_assets(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by asset type e.g. VEHICLE"),
    status: Optional[str] = Query(None, description="Filter by status e.g. AVAILABLE"),
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by station or location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists expedition physical assets with optional filtering and pagination."""
    service = AssetService(session)
    items, total = service.list_assets(
        type_=type,
        status=status,
        location_id=location_id,
        page=page,
        page_size=page_size
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [AssetRead.model_validate(a).model_dump() for a in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    data: AssetCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Registers a new expedition physical asset and emits AssetCreated event."""
    service = AssetService(session)
    cid = _extract_cid(request)
    created = service.create_asset(data=data, correlation_id=cid)
    return create_success_response(
        data=AssetRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{asset_id}", response_model=ApiResponse)
def get_asset(
    asset_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves asset detail by UUID."""
    service = AssetService(session)
    asset = service.get_asset(asset_id)
    return create_success_response(
        data=AssetRead.model_validate(asset).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.patch("/{asset_id}", response_model=ApiResponse)
def update_asset(
    asset_id: uuid.UUID,
    data: AssetUpdate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Updates asset metadata. Retired assets cannot be modified."""
    service = AssetService(session)
    cid = _extract_cid(request)
    updated = service.update_asset(asset_id=asset_id, data=data, correlation_id=cid)
    return create_success_response(
        data=AssetRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/{asset_id}/transition", response_model=ApiResponse)
def transition_asset_status(
    asset_id: uuid.UUID,
    body: AssetStatusTransitionRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Validates and transitions asset lifecycle status (RETIRED is terminal)."""
    service = AssetService(session)
    cid = _extract_cid(request)
    updated = service.transition_asset_status(asset_id=asset_id, req=body, correlation_id=cid)
    return create_success_response(
        data=AssetRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/{asset_id}/move", response_model=ApiResponse)
def move_asset(
    asset_id: uuid.UUID,
    body: AssetMoveRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Relocates asset to new destination location and emits AssetMoved event."""
    service = AssetService(session)
    cid = _extract_cid(request)
    updated = service.move_asset(asset_id=asset_id, req=body, correlation_id=cid)
    return create_success_response(
        data=AssetRead.model_validate(updated).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{asset_id}/timeline", response_model=ApiResponse)
def get_asset_timeline(
    asset_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves operational asset timeline including movements, maintenance, and state changes."""
    service = AssetService(session)
    timeline = service.get_asset_timeline(asset_id)
    return create_success_response(
        data=timeline.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


# ============================================================
# 2. MAINTENANCE ORDERS
# ============================================================

@router.post("/{asset_id}/maintenance", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def schedule_maintenance(
    asset_id: uuid.UUID,
    body: MaintenanceScheduleRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Schedules maintenance for an asset. Rejects overlapping active orders and retired assets."""
    service = AssetService(session)
    cid = _extract_cid(request)
    record = service.schedule_maintenance(asset_id=asset_id, req=body, correlation_id=cid)
    return create_success_response(
        data=MaintenanceRecordRead.model_validate(record).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/{asset_id}/maintenance", response_model=ApiResponse)
def list_asset_maintenance(
    asset_id: uuid.UUID,
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status (SCHEDULED, IN_PROGRESS, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists maintenance history for an asset."""
    service = AssetService(session)
    items, total = service.list_maintenance_for_asset(
        asset_id=asset_id,
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
    data = [MaintenanceRecordRead.model_validate(m).model_dump() for m in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.get("/maintenance/{record_id}", response_model=ApiResponse)
def get_maintenance_record(
    record_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves maintenance order details by UUID."""
    service = AssetService(session)
    record = service.get_maintenance(record_id)
    return create_success_response(
        data=MaintenanceRecordRead.model_validate(record).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/maintenance/{record_id}/start", response_model=ApiResponse)
def start_maintenance(
    record_id: uuid.UUID,
    body: MaintenanceStartRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Starts maintenance work order (status becomes IN_PROGRESS)."""
    service = AssetService(session)
    cid = _extract_cid(request)
    record = service.start_maintenance(record_id=record_id, req=body, correlation_id=cid)
    return create_success_response(
        data=MaintenanceRecordRead.model_validate(record).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/maintenance/{record_id}/complete", response_model=ApiResponse)
def complete_maintenance(
    record_id: uuid.UUID,
    body: MaintenanceCompleteRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Completes maintenance work order (does NOT silently change asset status unless target_asset_status is specified)."""
    service = AssetService(session)
    cid = _extract_cid(request)
    record = service.complete_maintenance(record_id=record_id, req=body, correlation_id=cid)
    return create_success_response(
        data=MaintenanceRecordRead.model_validate(record).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/maintenance/{record_id}/cancel", response_model=ApiResponse)
def cancel_maintenance(
    record_id: uuid.UUID,
    body: MaintenanceCancelRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Cancels a scheduled or in-progress maintenance order."""
    service = AssetService(session)
    cid = _extract_cid(request)
    record = service.cancel_maintenance(record_id=record_id, req=body, correlation_id=cid)
    return create_success_response(
        data=MaintenanceRecordRead.model_validate(record).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )
