"""Operational Event Service (Shared Domain Event Foundation)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.events.repository import EventRepository
from backend.app.platform.events.schemas import (
    OperationalEventCreate,
    OperationalEventRead,
    OperationalEventFilter,
)
from backend.app.shared.types.provenance import DataProvenance
from backend.app.core.errors import EntityNotFoundError, DomainValidationError


class EventService:
    """
    Central domain service for appending and reading operational events.
    Guarantees transactional consistency by operating within the caller's session.
    """
    def __init__(self, session: Session):
        self.session = session
        self.repository = EventRepository(session)

    def append_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        new_state: str,
        previous_state: Optional[str] = None,
        source: str = "API",
        actor_type: str = "SYSTEM",
        actor_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
        evidence: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        data_provenance: DataProvenance = DataProvenance.SYNTHETIC_DEMO,
        occurred_at: Optional[datetime] = None
    ) -> OperationalEventModel:
        """
        Appends an immutable event to the journal within the current database transaction.
        Does NOT commit; caller service controls the transaction commit/rollback boundary.
        """
        if not event_type or not entity_type or not entity_id:
            raise DomainValidationError("event_type, entity_type, and entity_id are required for all operational events.")

        event_model = OperationalEventModel(
            event_id=uuid.uuid4(),
            event_type=event_type,
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            previous_state=previous_state,
            new_state=new_state,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            source=source,
            actor_type=actor_type,
            actor_id=actor_id,
            location_id=location_id,
            evidence=evidence or {},
            correlation_id=correlation_id or uuid.uuid4(),
            data_provenance=data_provenance.value if hasattr(data_provenance, "value") else str(data_provenance),
        )

        return self.repository.append(event_model)

    def get_event(self, event_id: uuid.UUID) -> OperationalEventModel:
        """Retrieves an event by UUID or raises EntityNotFoundError."""
        event = self.repository.get_by_id(event_id)
        if not event:
            raise EntityNotFoundError("OperationalEvent", event_id)
        return event

    def list_events(
        self,
        filters: Optional[OperationalEventFilter] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[OperationalEventModel], int]:
        """Lists events with pagination and filters."""
        return self.repository.list_events(filters=filters, page=page, page_size=page_size)

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[OperationalEventModel], int]:
        """Retrieves chronological event history for a given entity."""
        return self.repository.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size
        )
