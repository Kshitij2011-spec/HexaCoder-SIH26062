"""SQLAlchemy ORM Model for Expeditions."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text
from backend.app.db.base import Base, PG_UUID


class ExpeditionModel(Base):
    """
    Expedition Campaign Table mapping to public.expeditions.
    Root operational campaign governing all polar missions and logistics.
    """
    __tablename__ = "expeditions"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    season = Column(String(50), nullable=False)
    objective = Column(Text, nullable=True)
    planned_start_at = Column(DateTime(timezone=True), nullable=True)
    planned_end_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="DRAFT")
    priority = Column(Integer, nullable=False, default=3)
    notes = Column(Text, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
