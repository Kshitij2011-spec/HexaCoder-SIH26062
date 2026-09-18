"""SQLAlchemy ORM Models for Assets and Maintenance Records."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base, PG_UUID, PG_JSON


class AssetModel(Base):
    """
    Asset Entity mapping to public.assets.
    Physical capital assets, scientific instruments, vehicles, power generation, and field gear.
    """
    __tablename__ = "assets"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    asset_code = Column(String(50), unique=True, nullable=False)
    serial_number = Column(String(100), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    model = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    condition = Column(String(100), nullable=False, default="OPERATIONAL")
    criticality = Column(String(50), nullable=False, default="STANDARD")
    location_id = Column(PG_UUID, nullable=True)
    custodian_person_id = Column(PG_UUID, nullable=True)
    assigned_mission_id = Column(PG_UUID, nullable=True)
    maintenance_state = Column(String(50), nullable=True, default="SERVICEABLE")
    status = Column(String(50), nullable=False, default="AVAILABLE")
    required_spare_item_id = Column(PG_UUID, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    commissioned_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    maintenance_records = relationship(
        "MaintenanceRecordModel",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="desc(MaintenanceRecordModel.created_at)"
    )


class MaintenanceRecordModel(Base):
    """
    Maintenance Record Entity mapping to public.maintenance_records.
    Scheduled, preventative, and corrective maintenance work orders executed on assets.
    """
    __tablename__ = "maintenance_records"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    asset_id = Column(PG_UUID, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    maintenance_type = Column(String(100), nullable=False)
    priority = Column(Integer, nullable=False, default=3)
    status = Column(String(50), nullable=False, default="SCHEDULED")
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    performed_by = Column(String(150), nullable=True)
    technician_reference = Column(String(150), nullable=True)
    findings = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    required_spare_item_id = Column(PG_UUID, nullable=True)
    notes = Column(Text, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    asset = relationship("AssetModel", back_populates="maintenance_records")
