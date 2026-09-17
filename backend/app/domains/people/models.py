"""SQLAlchemy ORM Model for People (Expedition Personnel)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.db.base import Base, PG_UUID


class PersonModel(Base):
    """
    Personnel Table mapping to public.people.
    Tracks expedition participants with dual-state separation:
    - readiness_state (medical/training clearance)
    - movement_state (physical polar transit and field location)
    Contains zero private medical diagnosis/condition fields.
    """
    __tablename__ = "people"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    person_code = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    organization = Column(String(150), nullable=True)
    expedition_id = Column(PG_UUID, nullable=False)
    team_id = Column(PG_UUID, nullable=True)
    readiness_state = Column(String(50), nullable=False, default="NOMINATED")
    movement_state = Column(String(50), nullable=False, default="NOT_DEPLOYED")
    current_location_id = Column(PG_UUID, nullable=True)
    last_confirmed_location_id = Column(PG_UUID, nullable=True)
    emergency_status = Column(String(100), nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
