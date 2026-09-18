"""API Router for Reasoning, Dependencies, Impact, Readiness, and Constraints."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.services.dependencies.service import DependencyService
from backend.app.services.dependencies.schemas import DependencyEdge
from backend.app.services.impact.service import ImpactService
from backend.app.services.impact.processor import OperationalImpactProcessor
from backend.app.services.impact.schemas import ImpactResult
from backend.app.services.readiness.mission import MissionReadinessService
from backend.app.services.readiness.expedition import ExpeditionReadinessService
from backend.app.services.readiness.schemas import (
    MissionReadinessResult,
    ExpeditionReadinessResult,
)
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.constraints.schemas import (
    ConstraintRead,
    ConstraintEvaluationResult,
    EntityConstraintsSummary,
)
from backend.app.shared.schemas.envelope import ApiResponse, create_success_response

router = APIRouter(tags=["Reasoning & Operational Engine"])


# ---------------------------------------------------------------------------
# 1. Dependency Graph Endpoints
# ---------------------------------------------------------------------------

@router.get("/entities/{entity_type}/{entity_id}/dependencies", response_model=ApiResponse[List[DependencyEdge]])
def get_entity_dependencies(
    entity_type: str,
    entity_id: uuid.UUID,
    relationship_type: Optional[str] = Query(None, description="Optional semantic relationship filter"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves direct outgoing dependencies (entity -> targets)."""
    service = DependencyService(db)
    edges = service.get_outgoing_dependencies(entity_type, entity_id, relationship_type)
    return create_success_response(
        data=[e.model_dump() for e in edges],
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/entities/{entity_type}/{entity_id}/dependents", response_model=ApiResponse[List[DependencyEdge]])
def get_entity_dependents(
    entity_type: str,
    entity_id: uuid.UUID,
    relationship_type: Optional[str] = Query(None, description="Optional semantic relationship filter"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves direct incoming dependents (sources -> entity)."""
    service = DependencyService(db)
    edges = service.get_incoming_dependencies(entity_type, entity_id, relationship_type)
    return create_success_response(
        data=[e.model_dump() for e in edges],
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


# ---------------------------------------------------------------------------
# 2. Impact Propagation Endpoints
# ---------------------------------------------------------------------------

@router.get("/entities/{entity_type}/{entity_id}/impact", response_model=ApiResponse[ImpactResult])
def get_entity_impact(
    entity_type: str,
    entity_id: uuid.UUID,
    depth: int = Query(default=3, ge=1, le=5, description="Bounded graph traversal depth (max 5)"),
    change_summary: str = Query(default="Operational state inquiry", description="Description of change"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Computes deterministic bounded impact propagation for an entity change.
    Traverses semantic dependency chains and identifies affected entities and candidate constraints.
    """
    service = ImpactService(db)
    result = service.calculate_impact(
        entity_type=entity_type,
        entity_id=entity_id,
        change_summary=change_summary,
        depth=depth,
        correlation_id=uuid.UUID(request.headers.get("X-Request-ID")) if request and request.headers.get("X-Request-ID") else None
    )
    return create_success_response(
        data=result.model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/events/{event_id}/impact", response_model=ApiResponse[ImpactResult])
def get_event_impact(
    event_id: uuid.UUID,
    depth: int = Query(default=3, ge=1, le=5, description="Bounded traversal depth (max 5)"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Calculates derived operational impact and constraint violations triggered by an operational event.
    Operates strictly read-only; does not mutate primary tables.
    """
    processor = OperationalImpactProcessor(db)
    result = processor.process_operational_event(event_id, depth=depth)
    return create_success_response(
        data=result.model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


# ---------------------------------------------------------------------------
# 3. Operational Readiness Endpoints
# ---------------------------------------------------------------------------

@router.get("/missions/{id}/readiness", response_model=ApiResponse[MissionReadinessResult])
def get_mission_readiness(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Computes multi-dimensional mission readiness (READY, AT_RISK, BLOCKED)
    derived from assigned personnel, mandatory assets, temporal windows, and constraints.
    """
    service = MissionReadinessService(db)
    result = service.evaluate(id)
    return create_success_response(
        data=result.model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/expeditions/{id}/readiness", response_model=ApiResponse[ExpeditionReadinessResult])
def get_expedition_readiness(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Computes campaign-wide expedition readiness rolling up underlying mission readiness
    and evaluating expedition-level environmental and treaty compliance constraints.
    """
    service = ExpeditionReadinessService(db)
    result = service.evaluate(id)
    return create_success_response(
        data=result.model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


# ---------------------------------------------------------------------------
# 4. Constraints Endpoints
# ---------------------------------------------------------------------------

@router.get("/constraints", response_model=ApiResponse[List[ConstraintRead]])
def list_constraints(
    active_only: bool = Query(default=True, description="Filter to active constraints only"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Lists operational constraints defined in the platform."""
    service = ConstraintService(db)
    models = service.list_constraints(active_only=active_only)
    return create_success_response(
        data=[ConstraintRead.model_validate(m).model_dump() for m in models],
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/constraints/evaluate", response_model=ApiResponse[List[ConstraintEvaluationResult]])
def evaluate_all_constraints(
    active_only: bool = Query(default=True, description="Evaluate active constraints only"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Evaluates all operational constraints deterministically against current database state.
    Strictly read-only evaluation; does not mutate operational state.
    """
    service = ConstraintService(db)
    results = service.evaluate_all(active_only=active_only)
    return create_success_response(
        data=[r.model_dump() for r in results],
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/constraints/{id}", response_model=ApiResponse[ConstraintRead])
def get_constraint(
    id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieves a single operational constraint by ID."""
    service = ConstraintService(db)
    c = service.get_constraint(id)
    return create_success_response(
        data=ConstraintRead.model_validate(c).model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )


@router.get("/entities/{entity_type}/{entity_id}/constraints", response_model=ApiResponse[EntityConstraintsSummary])
def get_entity_constraints(
    entity_type: str,
    entity_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Evaluates and returns all operational constraints bound to an entity subject."""
    service = ConstraintService(db)
    summary = service.evaluate_for_entity(entity_type, entity_id)
    return create_success_response(
        data=summary.model_dump(),
        correlation_id=request.headers.get("X-Request-ID") if request else None
    )
