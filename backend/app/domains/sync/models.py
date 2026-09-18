"""SQLAlchemy ORM Model for offline_operations queue table."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, UniqueConstraint
from backend.app.db.base import Base, PG_UUID, PG_JSON


class OfflineOperationModel(Base):
    """
    Offline Operation Entity mapping to public.offline_operations.

    Represents an operation queued by a Track B domain client while
    connectivity was unavailable. The operation_id is the client-supplied
    idempotency key — duplicate submissions with the same operation_id
    are safe and idempotent.

    Data provenance: SYNTHETIC_DEMO — no live connectivity assumed.
    """
    __tablename__ = "offline_operations"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    operation_id = Column(PG_UUID, unique=True, nullable=False)    # client idempotency key
    entity_type = Column(String(100), nullable=False)              # INVENTORY_ITEM, ASSET, etc.
    operation_type = Column(String(100), nullable=False)           # CREATE, UPDATE, STATE_TRANSITION
    payload = Column(PG_JSON, nullable=False, default=dict)        # operation payload snapshot
    status = Column(String(50), nullable=False, default="PENDING")
    queued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    applied_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    actor_id = Column(PG_UUID, nullable=True)
    correlation_id = Column(PG_UUID, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
