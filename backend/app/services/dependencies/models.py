"""SQLAlchemy ORM Model for Semantic Dependencies."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.db.base import Base, PG_UUID, PG_JSON


class DependencyModel(Base):
    """
    Semantic Dependency Table mapping to public.dependencies.
    Maintains directional semantic linkages across all operational domain entities.
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
