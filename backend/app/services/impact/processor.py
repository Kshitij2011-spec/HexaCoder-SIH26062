"""Operational Impact Processor for Event-Driven Reasoning."""

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.platform.events.service import EventService
from backend.app.services.impact.service import ImpactService
from backend.app.services.impact.schemas import ImpactResult
from backend.app.core.errors import EntityNotFoundError


class OperationalImpactProcessor:
    """
    Orchestrates derived impact propagation and constraint checking
    triggered by an immutable operational event.
    Operates strictly in derived computation mode; does not modify primary tables.
    """

    def __init__(self, session: Session):
        self.session = session
        self.event_service = EventService(session)
        self.impact_service = ImpactService(session)

    def process_operational_event(
        self,
        event_id: uuid.UUID,
        depth: int = 3
    ) -> ImpactResult:
        """
        Loads an operational event from the immutable journal,
        propagates impact across semantic dependencies, and checks candidate constraints.
        """
        event = self.event_service.get_event(event_id)
        if not event:
            raise EntityNotFoundError("OperationalEvent", event_id)

        prev = event.previous_state or "INITIAL"
        curr = event.new_state or "UNKNOWN"
        summary = f"{event.event_type}: status changed from '{prev}' to '{curr}'"

        return self.impact_service.calculate_impact(
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            change_summary=summary,
            depth=depth,
            correlation_id=event.correlation_id
        )
