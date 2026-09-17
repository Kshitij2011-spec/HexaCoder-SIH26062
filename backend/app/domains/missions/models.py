"""SQLAlchemy ORM Model for Missions and Dependencies."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, UniqueConstraint
from backend.app.db.base import Base, PG_UUID, PG_JSON


class MissionModel(Base):
    """
    Mission Entity mapping to public.missions.
    Discrete operational or scientific undertaking within an expedition campaign.
    """
    __tablename__ = "missions"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    expedition_id = Column(PG_UUID, nullable=False)
    code = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)
    priority = Column(Integer, nullable=False, default=3)
    location_id = Column(PG_UUID, nullable=True)
    required_by_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="PROPOSED")
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("expedition_id", "code", name="uq_mission_expedition_code"),
    )


class DependencyModel(Base):
    """
    Semantic Dependency Table mapping to public.dependencies.
    Maintains semantic linkages (REQUIRES, SUPPORTS, ASSIGNED_TO, CONSTRAINED_BY) across domain entities.
    """
    __tablename__ = "dependencies"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    expedition_id = Column(PG_UUID, nullable=True)
    relationship_type = Column(String(50), nullable=False)
    source_entity_type = Column(String(50), nullable=False)
    source_entity_id = Column(PG_UUID, nullable=False)
    target_entity_type = Column(String(50), nullable=False)
    target_entity_id = Column(PG_UUID, nullable=False)
    criticality = Column(String(50), nullable=True, default="CRITICAL")
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
