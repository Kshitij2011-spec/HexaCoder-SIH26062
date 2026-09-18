"""FastAPI Router for Operational Replanning, Recommendations, and Approvals."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.domains.replanning.service import ReplanService, ApprovalService
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ReplanRead,
    ReplanOptionRead,
    RecommendationRead,
    ApprovalDecisionRequest,
    ApprovalRead,
    ReplanApplyRequest,
    ReplanApplyResult,
)
from backend.app.domains.replanning.states import ApprovalDecision
from backend.app.platform.audit.service import AuditService
from backend.app.platform.audit.schemas import AuditLogRead
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    PaginationMeta,
    create_success_response,
)

router = APIRouter(tags=["Replanning & Operational Decisions"])


# ---------------------------------------------------------------------------
# 1. REPLANS
# ---------------------------------------------------------------------------

@router.post("/replans", response_model=ApiResponse[ReplanRead], status_code=status.HTTP_201_CREATED)
def create_replan(
    payload: ReplanTriggerRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Creates an operational replan cycle.
    Supports 'OPERATOR_REQUESTED' (authorized manual request)
    or 'EVENT_TRIGGERED' (state mutation with operational impact and constraint violation).
    """
    service = ReplanService(db)
    actor_context = {
        "actor_type": "OPERATOR",
        "actor_id": payload.requested_by,
        "source": "API",
    }
    replan = service.create_replan_request(payload, actor_context=actor_context)
    return create_success_response(
        data=replan,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/replans", response_model=ApiResponse)
def list_replans(
    expedition_id: Optional[uuid.UUID] = Query(None, description="Filter by expedition"),
    mission_id: Optional[uuid.UUID] = Query(None, description="Filter by mission"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Lists operational replans with optional filtering."""
    service = ReplanService(db)
    items, total = service.list_replans(
        expedition_id=expedition_id,
        mission_id=mission_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [ReplanRead.model_validate(item).model_dump() for item in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination
    )


@router.get("/replans/{id}", response_model=ApiResponse[ReplanRead])
def get_replan(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves full details for a single replan, including options and recommendations."""
    service = ReplanService(db)
    replan = service.get_replan(id)
    return create_success_response(
        data=replan,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.post("/replans/{id}/generate-options", response_model=ApiResponse[List[ReplanOptionRead]])
def generate_replan_options(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Deterministically discovers candidate mitigation options and generates explainable recommendations.
    Evaluates each candidate against ConstraintService for tri-state feasibility.
    """
    service = ReplanService(db)
    options, recommendations = service.generate_options(id)
    return create_success_response(
        data=options,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/replans/{id}/options", response_model=ApiResponse[List[ReplanOptionRead]])
def get_replan_options(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Lists candidate mitigation options generated for a replan."""
    service = ReplanService(db)
    replan = service.get_replan(id)
    options = service.repo.list_options_by_replan(replan.id)
    return create_success_response(
        data=options,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/replans/{id}/recommendations", response_model=ApiResponse[List[RecommendationRead]])
def get_replan_recommendations(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Lists explainable operational recommendations generated for a replan."""
    service = ReplanService(db)
    replan = service.get_replan(id)
    recs = service.repo.list_recommendations_by_replan(replan.id)
    return create_success_response(
        data=recs,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.get("/replans/{id}/audit", response_model=ApiResponse)
def get_replan_audit(
    id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves immutable audit trail for a replan."""
    service = ReplanService(db)
    service.get_replan(id)
    audit_service = AuditService(db)
    items, total = audit_service.get_entity_audit_trail("REPLAN", id, page=page, page_size=page_size)
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1
    )
    data = [AuditLogRead.model_validate(item).model_dump() for item in items]
    return create_success_response(
        data=data,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
        pagination=pagination
    )


# ---------------------------------------------------------------------------
# 2. RECOMMENDATIONS & HUMAN APPROVALS
# ---------------------------------------------------------------------------

@router.get("/recommendations/{id}", response_model=ApiResponse[RecommendationRead])
def get_recommendation(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves full details of an operational recommendation."""
    service = ReplanService(db)
    rec = service.repo.get_recommendation_by_id(id)
    if not rec:
        from backend.app.core.errors import EntityNotFoundError
        raise EntityNotFoundError("Recommendation", id)
    return create_success_response(
        data=rec,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.post("/recommendations/{id}/approve", response_model=ApiResponse[ApprovalRead])
def approve_recommendation(
    id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Submits an APPROVED human decision for a recommendation.
    Enforces explicit human control boundary before consequential application.
    """
    service = ApprovalService(db)
    # Ensure approval request exists
    approval = service.request_approval(id, actor_context={"actor_id": payload.approver_person_id})
    # Apply approval decision
    payload.decision = ApprovalDecision.APPROVED
    decided = service.decide(approval.id, payload)
    return create_success_response(
        data=decided,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.post("/recommendations/{id}/reject", response_model=ApiResponse[ApprovalRead])
def reject_recommendation(
    id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Submits a REJECTED decision for a recommendation. Prevents its application."""
    service = ApprovalService(db)
    approval = service.request_approval(id, actor_context={"actor_id": payload.approver_person_id})
    payload.decision = ApprovalDecision.REJECTED
    decided = service.decide(approval.id, payload)
    return create_success_response(
        data=decided,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )


@router.post("/recommendations/{id}/apply", response_model=ApiResponse[ReplanApplyResult])
def apply_recommendation(
    id: uuid.UUID,
    payload: ReplanApplyRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Applies an approved recommendation through verified domain services.
    Requires prior human approval (APPROVED). Idempotent if called repeatedly.
    """
    service = ApprovalService(db)
    result = service.apply(id, payload)
    return create_success_response(
        data=result,
        correlation_id=request.headers.get("X-Request-ID") if request else None,
    )
