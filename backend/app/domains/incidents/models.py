"""SQLAlchemy ORM Models for Incidents and Incident References."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.db.base import Base, PG_UUID, PG_JSON


class IncidentModel(Base):
    """
    Incident Entity mapping to public.incidents.
    Captures operational anomalies, equipment failures, logistics blockages, and field hazards.
    """
    __tablename__ = "incidents"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    incident_code = Column(String(50), unique=True, nullable=False)
    expedition_id = Column(PG_UUID, nullable=True)
    title = Column(String(255), nullable=False, default="Operational Incident")
    type = Column("type", String(100), nullable=False)
    severity = Column(String(50), nullable=False, default="MEDIUM")
    priority = Column(Integer, nullable=False, default=3)
    location_id = Column(PG_UUID, nullable=True)
    asset_id = Column(PG_UUID, nullable=True)
    commander_person_id = Column(PG_UUID, nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    declared_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    references = relationship(
        "IncidentReferenceModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    propagations = relationship(
        "IncidentPropagationModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def incident_type(self) -> str:
        return self.type

    @incident_type.setter
    def incident_type(self, val: str) -> None:
        self.type = val


class IncidentReferenceModel(Base):
    """
    Incident Resource Reference mapping to public.incident_references.
    Loosely links incidents to operational entities across domains without tight coupling.
    """
    __tablename__ = "incident_references"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    incident_id = Column(PG_UUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    reference_type = Column(String(50), nullable=False)
    reference_id = Column(PG_UUID, nullable=False)
    notes = Column(Text, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    incident = relationship("IncidentModel", back_populates="references")

    __table_args__ = (
        UniqueConstraint("incident_id", "reference_type", "reference_id", name="uq_incident_reference_target"),
    )


class IncidentPropagationModel(Base):
    """
    Incident Propagation Record mapping to public.incident_propagations.
    Records cross-domain operational impact propagation attempts and outcomes.
    """
    __tablename__ = "incident_propagations"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    incident_id = Column(PG_UUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    reference_id = Column(PG_UUID, nullable=False)
    reference_type = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    previous_state = Column(String(100), nullable=True)
    resulting_state = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    event_id = Column(PG_UUID, nullable=True)
    audit_id = Column(PG_UUID, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    incident = relationship("IncidentModel", back_populates="propagations")

    __table_args__ = (
        UniqueConstraint("incident_id", "reference_type", "reference_id", "action", name="uq_incident_propagation_action"),
    )
