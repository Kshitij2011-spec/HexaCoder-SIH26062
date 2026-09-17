"""SQLAlchemy ORM Model for Application Audit Log."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.db.base import Base, PG_UUID, PG_JSON


class AuditLogModel(Base):
    """
    Immutable Application Audit Trail mapping to public.audit_log.
    Records administrative/user actions causing operational mutations.
    """
    __tablename__ = "audit_log"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(PG_UUID, nullable=True)
    actor_person_id = Column(PG_UUID, nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(PG_UUID, nullable=True)
    before_snapshot = Column(PG_JSON, nullable=True)
    after_snapshot = Column(PG_JSON, nullable=True)
    correlation_id = Column(PG_UUID, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    metadata_ = Column("metadata", PG_JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
