"""SQLAlchemy ORM Model for Teams."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.db.base import Base, PG_UUID


class TeamModel(Base):
    """
    Expedition Teams Table mapping to public.teams.
    Represents organized functional teams (e.g. Science, Logistics, Medical)
    within an expedition campaign.
    """
    __tablename__ = "teams"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    expedition_id = Column(PG_UUID, nullable=False)
    leader_person_id = Column(PG_UUID, nullable=True)
    mission_id = Column(PG_UUID, nullable=True)
    location_id = Column(PG_UUID, nullable=True)
    status = Column(String(50), nullable=False, default="FORMING")
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
