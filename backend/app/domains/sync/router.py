"""FastAPI REST Router for Offline Queue / Sync domain (B5)."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.domains.sync.service import SyncService
from backend.app.domains.sync.schemas import (
    OfflineOperationEnqueue,
    OfflineOperationRead,
    SyncBatchRequest,
    SyncBatchResult,
    OperationApplyRequest,
    SyncQueueSummary,
)
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    ApiErrorItem,
    create_success_response,
    create_error_response,
)
from backend.app.core.errors import (
    DomainException,
    EntityNotFoundError,
)

router = APIRouter(prefix="/sync", tags=["Offline Sync"])


def _extract_cid(request: Request) -> Optional[uuid.UUID]:
    cid = request.headers.get("X-Request-ID")
    if cid:
        try:
            return uuid.UUID(cid)
        except ValueError:
            return None
    return None


def _extract_actor(request: Request) -> Optional[uuid.UUID]:
    actor = request.headers.get("X-Actor-ID")
    if actor:
        try:
            return uuid.UUID(actor)
        except ValueError:
            return None
    return None


# ============================================================
# 1. QUEUE SUMMARY
# ============================================================

@router.get("/summary", response_model=ApiResponse, summary="Offline queue summary")
def queue_summary(request: Request, session: Session = Depends(get_db)):
    """Returns counts of offline operations grouped by status."""
    svc = SyncService(session)
    summary = svc.get_queue_summary()
    return create_success_response(
        data=summary.model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 2. LIST OPERATIONS
# ============================================================

@router.get("", response_model=ApiResponse, summary="List offline operations")
def list_operations(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPLIED, FAILED, REJECTED"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type e.g. INVENTORY_ITEM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_db),
):
    """Lists queued offline operations with optional filtering."""
    svc = SyncService(session)
    items, total = svc.list_operations(
        status=status, entity_type=entity_type, page=page, page_size=page_size
    )
    data = [OfflineOperationRead.model_validate(op).model_dump() for op in items]
    return create_success_response(
        data=data,
        pagination=PaginationMeta(page=page, page_size=page_size, total_items=total),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 3. ENQUEUE — single
# ============================================================

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED, summary="Enqueue an offline operation")
def enqueue_operation(
    request: Request,
    body: OfflineOperationEnqueue,
    session: Session = Depends(get_db),
):
    """
    Enqueue a single offline operation. Idempotent — re-submitting with
    the same operation_id returns the existing record with HTTP 200 (not 201).
    """
    svc = SyncService(session)
    try:
        op, created = svc.enqueue(
            body,
            correlation_id=_extract_cid(request),
            actor_id=_extract_actor(request),
        )
    except DomainException as exc:
        return create_error_response(
            errors=[ApiErrorItem(code=exc.code, message=exc.message, field=exc.field)],
            correlation_id=request.headers.get("X-Request-ID"),
        )

    return create_success_response(
        data={
            **OfflineOperationRead.model_validate(op).model_dump(),
            "created": created,
        },
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 4. BATCH ENQUEUE
# ============================================================

@router.post("/batch", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED, summary="Batch enqueue offline operations")
def enqueue_batch(
    request: Request,
    body: SyncBatchRequest,
    session: Session = Depends(get_db),
):
    """
    Batch-enqueue up to 100 offline operations in one request.
    Each operation is handled idempotently — the response includes per-operation outcomes.
    """
    svc = SyncService(session)
    result = svc.enqueue_batch(
        body,
        correlation_id=_extract_cid(request),
        actor_id=_extract_actor(request),
    )
    return create_success_response(
        data=result.model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 5. GET SINGLE OPERATION
# ============================================================

@router.get("/{record_id}", response_model=ApiResponse, summary="Get offline operation by ID")
def get_operation(
    request: Request,
    record_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """Retrieve a single offline operation by its internal UUID."""
    svc = SyncService(session)
    try:
        op = svc.get_operation(record_id)
    except EntityNotFoundError as exc:
        return create_error_response(
            errors=[ApiErrorItem(code=exc.code, message=exc.message)],
            correlation_id=request.headers.get("X-Request-ID"),
        )
    return create_success_response(
        data=OfflineOperationRead.model_validate(op).model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 6. APPLY / MARK FAILED / REJECT
# ============================================================

@router.patch("/{record_id}/apply", response_model=ApiResponse, summary="Apply or reject an offline operation")
def apply_operation(
    request: Request,
    record_id: uuid.UUID,
    body: OperationApplyRequest,
    session: Session = Depends(get_db),
):
    """
    Transition a PENDING operation to APPLIED, FAILED, or REJECTED.
    APPLIED and REJECTED are terminal states.
    FAILED operations can be retried (transitioned back to PENDING or REJECTED).
    """
    svc = SyncService(session)
    try:
        op = svc.apply_operation(
            record_id,
            body,
            actor_id=_extract_actor(request),
            correlation_id=_extract_cid(request),
        )
    except DomainException as exc:
        return create_error_response(
            errors=[ApiErrorItem(code=exc.code, message=exc.message, field=getattr(exc, "field", None))],
            correlation_id=request.headers.get("X-Request-ID"),
        )
    return create_success_response(
        data=OfflineOperationRead.model_validate(op).model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )


# ============================================================
# 7. LOOKUP BY CLIENT OPERATION_ID
# ============================================================

@router.get("/by-operation-id/{operation_id}", response_model=ApiResponse, summary="Lookup by client operation_id")
def get_by_operation_id(
    request: Request,
    operation_id: uuid.UUID,
    session: Session = Depends(get_db),
):
    """
    Lookup an offline operation by the client-supplied idempotency key (operation_id).
    Clients can use this to confirm whether their offline operation was received.
    """
    svc = SyncService(session)
    try:
        op = svc.get_by_operation_id(operation_id)
    except EntityNotFoundError as exc:
        return create_error_response(
            errors=[ApiErrorItem(code=exc.code, message=exc.message)],
            correlation_id=request.headers.get("X-Request-ID"),
        )
    return create_success_response(
        data=OfflineOperationRead.model_validate(op).model_dump(),
        correlation_id=request.headers.get("X-Request-ID"),
    )
