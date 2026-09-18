"""Person B Operations API Router (Operational Timeline)."""

import uuid
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Request, Query, Path
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.domains.operations.timeline import OperationalTimelineService
from backend.app.domains.operations.schemas import (
    TimelineResponse,
    TimelineEntityType,
)
from backend.app.shared.schemas.envelope import ApiResponse, create_success_response
from backend.app.core.errors import DomainValidationError

router = APIRouter(prefix="/operations", tags=["Operations - Timeline"])


@router.get(
    "/timeline/{entity_type}/{entity_id}",
    response_model=ApiResponse,
    summary="Retrieve operational timeline for a Person B entity",
)
def get_entity_timeline(
    request: Request,
    entity_type: str = Path(..., description="Entity type or alias (e.g. LOCATION, CARGO_CONSIGNMENT, ASSET, INCIDENT)"),
    entity_id: uuid.UUID = Path(..., description="Technical UUID of the entity"),
    include_related: bool = Query(False, description="Include 1-hop related Person B entities (e.g. packages, maintenance, propagations)"),
    order: Literal["desc", "asc"] = Query("desc", description="Chronological ordering (desc = newest first, asc = oldest first)"),
    page: int = Query(1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Page size (1-200)"),
    entry_type: Optional[str] = Query(None, description="Filter by entry type (OPERATIONAL_EVENT, AUDIT_RECORD, PROPAGATION_RECORD, OFFLINE_SYNC)"),
    occurred_from: Optional[datetime] = Query(None, description="Lower bound timestamp (ISO 8601)"),
    occurred_to: Optional[datetime] = Query(None, description="Upper bound timestamp (ISO 8601)"),
    session: Session = Depends(get_db),
):
    """
    Retrieves a deterministic, aggregated operational timeline for an authoritative Person B resource.
    Aggregates immutable operational events, audit records, B8 incident propagations, and B5 offline sync operations.
    Strictly read-only; never mutates domain state.
    """
    service = OperationalTimelineService(session)
    timeline: TimelineResponse = service.get_timeline(
        entity_type=entity_type,
        entity_id=entity_id,
        include_related=include_related,
        order=order,
        page=page,
        page_size=page_size,
        entry_type=entry_type,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )

    return create_success_response(
        data=timeline.model_dump(mode="json"),
        correlation_id=request.headers.get("X-Request-ID"),
    )
