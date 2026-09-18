"""Operational Event Repository (Append-Only Persistence Layer)."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.events.schemas import OperationalEventFilter


class EventRepository:
    """
    Append-only repository for Operational Events.
    Strictly forbids update and delete operations.
    """
    def __init__(self, session: Session):
        self.session = session

    def append(self, event_model: OperationalEventModel) -> OperationalEventModel:
        """Persists a new immutable operational event within the active session."""
        self.session.add(event_model)
        # Flush to populate default IDs without committing parent transaction
        self.session.flush()
        return event_model

    def get_by_id(self, event_id: uuid.UUID) -> Optional[OperationalEventModel]:
        """Retrieves an event by technical ID or event_id UUID."""
        stmt = select(OperationalEventModel).where(
            (OperationalEventModel.id == event_id) | (OperationalEventModel.event_id == event_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_events(
        self,
        filters: Optional[OperationalEventFilter] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[OperationalEventModel], int]:
        """Lists events with filtering and pagination."""
        conditions = []
        if filters:
            if filters.entity_type:
                conditions.append(OperationalEventModel.entity_type == filters.entity_type.upper())
            if filters.entity_id:
                conditions.append(OperationalEventModel.entity_id == filters.entity_id)
            if filters.event_type:
                conditions.append(OperationalEventModel.event_type == filters.event_type)
            if filters.correlation_id:
                conditions.append(OperationalEventModel.correlation_id == filters.correlation_id)
            if filters.occurred_from:
                conditions.append(OperationalEventModel.occurred_at >= filters.occurred_from)
            if filters.occurred_to:
                conditions.append(OperationalEventModel.occurred_at <= filters.occurred_to)

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(OperationalEventModel.id)).where(where_clause)
        total_items = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(OperationalEventModel)
            .where(where_clause)
            .order_by(OperationalEventModel.occurred_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total_items

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[OperationalEventModel], int]:
        """Retrieves the complete audit trail for a specific domain entity."""
        filters = OperationalEventFilter(
            entity_type=entity_type,
            entity_id=entity_id
        )
        return self.list_events(filters=filters, page=page, page_size=page_size)
