"""SQLAlchemy ORM Model for Time Windows."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, CheckConstraint
from backend.app.db.base import Base, PG_UUID


class TimeWindowModel(Base):
    """
    Time Windows Table mapping to public.time_windows.
    Represents hard and soft temporal constraints (flight weather windows,
    sea ice clearance, cargo offload windows) for missions, expeditions, and transports.
    """
    __tablename__ = "time_windows"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)
    open_at = Column(DateTime(timezone=True), nullable=False)
    close_at = Column(DateTime(timezone=True), nullable=False)
    hard_or_soft = Column(String(20), nullable=False, default="HARD")
    subject_type = Column(String(50), nullable=False)
    subject_id = Column(PG_UUID, nullable=False)
    status = Column(String(50), nullable=False, default="OPEN")
    description = Column(Text, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("close_at > open_at", name="chk_time_window_bounds"),
    )
