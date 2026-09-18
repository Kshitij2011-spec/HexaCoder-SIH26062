"""SQLAlchemy ORM Model for Operational Constraints."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text
from backend.app.db.base import Base, PG_UUID, PG_JSON


class ConstraintModel(Base):
    """
    Operational Constraint Definition mapping to public.constraints.
    Stores declarative invariants and rules evaluated deterministically by the constraint engine.
    """
    __tablename__ = "constraints"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False, default="CRITICAL")
    hard_or_soft = Column(String(50), nullable=False, default="HARD")
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(PG_UUID, nullable=True)
    rule_code = Column(String(100), nullable=False)
    parameters = Column(PG_JSON, nullable=False, default=dict)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
