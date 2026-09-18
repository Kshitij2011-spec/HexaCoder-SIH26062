"""SQLAlchemy ORM Models for Cargo Consignments and Packages."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base, PG_UUID


class CargoConsignmentModel(Base):
    """
    Cargo Consignment Entity mapping to public.cargo_consignments.
    Logical polar shipment containing multiple physical packages.
    """
    __tablename__ = "cargo_consignments"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    expedition_id = Column(PG_UUID, nullable=False)
    origin_location_id = Column(PG_UUID, nullable=False)
    destination_location_id = Column(PG_UUID, nullable=False)
    priority = Column(Integer, nullable=False, default=3)
    required_by_at = Column(DateTime(timezone=True), nullable=False)
    planned_arrival_at = Column(DateTime(timezone=True), nullable=True)
    estimated_arrival_at = Column(DateTime(timezone=True), nullable=True)
    transport_plan_summary = Column(Text, nullable=True)
    compliance_status = Column(String(50), nullable=False, default="REQUIRED")
    status = Column(String(50), nullable=False, default="REQUESTED")
    risk_level = Column(String(50), nullable=False, default="NOMINAL")
    handling_classification = Column(String(100), nullable=True)
    exception_reason = Column(Text, nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to physical packages
    packages = relationship("CargoPackageModel", back_populates="consignment", cascade="all, delete-orphan")


class CargoPackageModel(Base):
    """
    Cargo Package Entity mapping to public.cargo_packages.
    Physical container, pallet, crate, or unit manifesting within a consignment.
    """
    __tablename__ = "cargo_packages"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    consignment_id = Column(PG_UUID, ForeignKey("cargo_consignments.id", ondelete="CASCADE"), nullable=False)
    contents_summary = Column(Text, nullable=True)
    quantity = Column(Numeric(12, 2), nullable=False, default=1)
    weight_kg = Column(Numeric(10, 2), nullable=True)
    length_cm = Column(Numeric(10, 2), nullable=True)
    width_cm = Column(Numeric(10, 2), nullable=True)
    height_cm = Column(Numeric(10, 2), nullable=True)
    handling_classification = Column(String(100), nullable=True)
    current_location_id = Column(PG_UUID, nullable=True)
    current_transport_leg_id = Column(PG_UUID, nullable=True)
    condition = Column(String(100), nullable=False, default="GOOD")
    status = Column(String(50), nullable=False, default="PACKED")
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    consignment = relationship("CargoConsignmentModel", back_populates="packages")
