"""Inventory API Router."""

import uuid
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.inventory.service import InventoryService, calculate_lot_availability
from backend.app.domains.inventory.schemas import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryStockLotCreate,
    InventoryStockLotRead,
    StockAvailabilityRead,
    InventoryTransactionRead,
    StockReceiptRequest,
    StockReservationRequest,
    StockReleaseRequest,
    StockIssueRequest,
    StockQuarantineRequest,
    StockStatusTransitionRequest,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _extract_cid(request: Request) -> Optional[uuid.UUID]:
    cid_header = request.headers.get("X-Request-ID")
    if cid_header:
        try:
            return uuid.UUID(cid_header)
        except ValueError:
            return None
    return None


def _format_lot_read(lot) -> dict:
    available, is_deficit = calculate_lot_availability(
        on_hand=Decimal(str(lot.on_hand_quantity)),
        reserved=Decimal(str(lot.reserved_quantity)),
        quarantined=Decimal(str(lot.quarantined_quantity)),
        damaged=Decimal(str(lot.damaged_quantity)),
        reorder_point=Decimal(str(lot.reorder_point)) if lot.reorder_point is not None else None
    )
    data = InventoryStockLotRead.model_validate(lot).model_dump()
    data["available_quantity"] = available
    data["is_deficit"] = is_deficit
    return data


# ============================================================
# 1. CATALOG ITEMS
# ============================================================

@router.get("/items", response_model=ApiResponse)
def list_items(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by item category e.g. RATIONS, FUEL"),
    criticality: Optional[str] = Query(None, description="Filter by criticality tier"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists inventory catalog items with optional filtering and pagination."""
    service = InventoryService(session)
    items, total = service.list_items(category=category, criticality=criticality, page=page, page_size=page_size)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [InventoryItemRead.model_validate(i).model_dump() for i in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("/items", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    data: InventoryItemCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Registers a new standard catalog item."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    created = service.create_item(data=data, correlation_id=cid)
    return create_success_response(
        data=InventoryItemRead.model_validate(created).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/items/{item_id}", response_model=ApiResponse)
def get_item(
    item_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves standard catalog item by UUID."""
    service = InventoryService(session)
    item = service.get_item(item_id)
    return create_success_response(
        data=InventoryItemRead.model_validate(item).model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


# ============================================================
# 2. STOCK LOTS
# ============================================================

@router.get("/stock-lots", response_model=ApiResponse)
def list_stock_lots(
    request: Request,
    inventory_item_id: Optional[uuid.UUID] = Query(None, description="Filter by catalog item"),
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by storage location"),
    status: Optional[str] = Query(None, description="Filter by status (AVAILABLE, RESERVED, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Lists stock lots with computed available stock and deficit indicators."""
    service = InventoryService(session)
    lots, total = service.list_stock_lots(
        inventory_item_id=inventory_item_id,
        location_id=location_id,
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
    data = [_format_lot_read(lot) for lot in lots]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )


@router.post("/stock-lots", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def create_stock_lot(
    data: InventoryStockLotCreate,
    request: Request,
    session: Session = Depends(get_db)
):
    """Registers a physical stock lot at an operational location."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    created = service.create_stock_lot(data=data, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(created),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/stock-lots/{lot_id}", response_model=ApiResponse)
def get_stock_lot(
    lot_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves stock lot with computed availability and reorder indicators."""
    service = InventoryService(session)
    lot = service.get_stock_lot(lot_id)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/stock-lots/{lot_id}/availability", response_model=ApiResponse)
def get_stock_availability(
    lot_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db)
):
    """Retrieves detailed domain-authoritative availability calculation for a stock lot."""
    service = InventoryService(session)
    avail = service.get_stock_availability(lot_id)
    return create_success_response(
        data=avail.model_dump(),
        correlation_id=request.headers.get("X-Request-ID")
    )


# ============================================================
# 3. STOCK MUTATIONS & OPERATIONAL LEDGER
# ============================================================

@router.post("/stock-lots/{lot_id}/receive", response_model=ApiResponse)
def receive_stock(
    lot_id: uuid.UUID,
    body: StockReceiptRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Receives physical stock into a lot and appends an immutable RECEIPT ledger record."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.receive_stock(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/stock-lots/{lot_id}/reserve", response_model=ApiResponse)
def reserve_stock(
    lot_id: uuid.UUID,
    body: StockReservationRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Reserves uncommitted available stock and appends an immutable RESERVATION ledger record."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.reserve_stock(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/stock-lots/{lot_id}/release", response_model=ApiResponse)
def release_reservation(
    lot_id: uuid.UUID,
    body: StockReleaseRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Releases reservation back to available stock and appends a RELEASE ledger record."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.release_reservation(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/stock-lots/{lot_id}/issue", response_model=ApiResponse)
def issue_stock(
    lot_id: uuid.UUID,
    body: StockIssueRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Issues physical stock to field/consumers, deducting from on-hand and logging an ISSUE record."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.issue_stock(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/stock-lots/{lot_id}/quarantine", response_model=ApiResponse)
def quarantine_stock(
    lot_id: uuid.UUID,
    body: StockQuarantineRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Quarantines available stock for safety or inspection and logs a QUARANTINE record."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.quarantine_stock(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.post("/stock-lots/{lot_id}/transition", response_model=ApiResponse)
def transition_stock_status(
    lot_id: uuid.UUID,
    body: StockStatusTransitionRequest,
    request: Request,
    session: Session = Depends(get_db)
):
    """Applies valid state machine transition to stock lot."""
    service = InventoryService(session)
    cid = _extract_cid(request)
    lot = service.transition_status(lot_id=lot_id, req=body, correlation_id=cid)
    return create_success_response(
        data=_format_lot_read(lot),
        correlation_id=request.headers.get("X-Request-ID")
    )


@router.get("/stock-lots/{lot_id}/transactions", response_model=ApiResponse)
def list_lot_transactions(
    lot_id: uuid.UUID,
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_db)
):
    """Retrieves immutable operational transaction ledger history for a stock lot."""
    service = InventoryService(session)
    txs, total = service.list_transactions(lot_id=lot_id, page=page, page_size=page_size)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [InventoryTransactionRead.model_validate(tx).model_dump() for tx in txs]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID"),
        pagination=pagination
    )
