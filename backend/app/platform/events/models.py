"""SQLAlchemy ORM Model for Operational Events (Event Journal)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text
from backend.app.db.base import Base, PG_UUID, PG_JSON


class OperationalEventModel(Base):
    """
    Immutable Operational Event Journal mapping to public.operational_events.
    Enforced append-only via database trigger trg_operational_events_immutable.
    """
    __tablename__ = "operational_events"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    event_id = Column(PG_UUID, unique=True, nullable=False, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(PG_UUID, nullable=False)
    previous_state = Column(Text, nullable=True)
    new_state = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    source = Column(String(100), nullable=False, default="API")
    actor_type = Column(String(50), nullable=True, default="SYSTEM")
    actor_id = Column(PG_UUID, nullable=True)
    location_id = Column(PG_UUID, nullable=True)
    evidence = Column(PG_JSON, nullable=False, default=dict)
    correlation_id = Column(PG_UUID, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
