"""SQLAlchemy ORM Models for Transport Legs and Cargo Assignments."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, UniqueConstraint
from backend.app.db.base import Base, PG_UUID, PG_JSON


class TransportLegModel(Base):
    """
    Transport Leg Entity mapping to public.transport_legs.
    First-class movement segment across polar transit corridors.
    """
    __tablename__ = "transport_legs"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    expedition_id = Column(PG_UUID, nullable=False)
    mode = Column(String(50), nullable=False)
    origin_location_id = Column(PG_UUID, nullable=False)
    destination_location_id = Column(PG_UUID, nullable=False)
    departure_window_open = Column(DateTime(timezone=True), nullable=True)
    departure_window_close = Column(DateTime(timezone=True), nullable=True)
    arrival_window_open = Column(DateTime(timezone=True), nullable=True)
    arrival_window_close = Column(DateTime(timezone=True), nullable=True)
    planned_departure_at = Column(DateTime(timezone=True), nullable=True)
    planned_arrival_at = Column(DateTime(timezone=True), nullable=True)
    estimated_departure_at = Column(DateTime(timezone=True), nullable=True)
    estimated_arrival_at = Column(DateTime(timezone=True), nullable=True)
    actual_departure_at = Column(DateTime(timezone=True), nullable=True)
    actual_arrival_at = Column(DateTime(timezone=True), nullable=True)
    capacity = Column(Numeric(12, 2), nullable=True)
    capacity_unit = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="PLANNED")
    delay_reason = Column(Text, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class TransportCargoAssignmentModel(Base):
    """
    Physical manifest linkage mapping to public.transport_cargo_assignments.
    Realizes the 'Cargo MOVES_VIA Transport Leg' semantic relationship.
    """
    __tablename__ = "transport_cargo_assignments"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    transport_leg_id = Column(PG_UUID, ForeignKey("transport_legs.id", ondelete="CASCADE"), nullable=False)
    cargo_consignment_id = Column(PG_UUID, ForeignKey("cargo_consignments.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    released_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="APPROVED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("transport_leg_id", "cargo_consignment_id", name="uq_transport_cargo"),
    )
