"""SQLAlchemy ORM Model for Locations."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Text, DateTime
from backend.app.db.base import Base, PG_UUID


class LocationModel(Base):
    """
    Location Entity mapping to public.locations.
    Hierarchical operational and logistics facilities across polar expedition theater.
    """
    __tablename__ = "locations"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    parent_location_id = Column(PG_UUID, nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    status = Column(String(50), nullable=False, default="AVAILABLE")
    description = Column(Text, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
