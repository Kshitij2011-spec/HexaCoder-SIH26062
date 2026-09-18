"""SQLAlchemy ORM Models for Replanning, Options, Recommendations, and Approvals."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base, PG_UUID, PG_JSON
from backend.app.domains.replanning.states import (
    ReplanStatus,
    RecommendationStatus,
    ApprovalStatus,
    OptionFeasibility,
    ReplanActionType,
)


class ReplanModel(Base):
    """
    Authoritative record of an operational replanning cycle triggered by an
    operational event or explicitly requested by an authorized human operator.
    """
    __tablename__ = "replans"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    replan_code = Column(String(50), unique=True, nullable=False, index=True)
    expedition_id = Column(PG_UUID, ForeignKey("expeditions.id"), nullable=False, index=True)
    mission_id = Column(PG_UUID, ForeignKey("missions.id"), nullable=True, index=True)
    trigger_event_id = Column(PG_UUID, ForeignKey("operational_events.id"), nullable=True)
    trigger_entity_type = Column(String(50), nullable=True)
    trigger_entity_id = Column(PG_UUID, nullable=True)
    trigger_reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=ReplanStatus.REQUESTED.value, index=True)
    current_state_evidence = Column(PG_JSON, nullable=False, default=dict)
    violated_constraints = Column(PG_JSON, nullable=False, default=list)
    affected_entities = Column(PG_JSON, nullable=False, default=list)
    requested_by = Column(PG_UUID, ForeignKey("people.id"), nullable=True)
    correlation_id = Column(PG_UUID, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    options = relationship("ReplanOptionModel", back_populates="replan", cascade="all, delete-orphan")
    recommendations = relationship("RecommendationModel", back_populates="replan", cascade="all, delete-orphan")


class ReplanOptionModel(Base):
    """
    Deterministic candidate operational mitigation option evaluated against constraints.
    Maps to recommendation_alternatives in database for schema continuity.
    """
    __tablename__ = "recommendation_alternatives"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    replan_id = Column(PG_UUID, ForeignKey("replans.id"), nullable=True, index=True)
    recommendation_id = Column(PG_UUID, ForeignKey("recommendations.id"), nullable=True, index=True)
    option_code = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    action_type = Column(String(50), nullable=False, default=ReplanActionType.MODIFY_TRANSPORT.value)
    affected_entity_type = Column(String(50), nullable=True)
    affected_entity_id = Column(PG_UUID, nullable=True)
    proposed_changes = Column(PG_JSON, nullable=False, default=list)
    proposed_state_change = Column(PG_JSON, nullable=False, default=dict)
    prerequisite_conditions = Column(PG_JSON, nullable=False, default=list)
    expected_impact = Column(PG_JSON, nullable=False, default=dict)
    impact = Column(PG_JSON, nullable=False, default=dict)
    tradeoffs = Column(PG_JSON, nullable=False, default=dict)
    constraints_checked = Column(PG_JSON, nullable=False, default=list)
    constraints_violated = Column(PG_JSON, nullable=False, default=list)
    unknown_requirements = Column(PG_JSON, nullable=False, default=list)
    feasibility_state = Column(String(50), nullable=False, default=OptionFeasibility.FEASIBLE.value, index=True)
    operational_rationale = Column(Text, nullable=True)
    evidence = Column(PG_JSON, nullable=False, default=dict)
    assumptions = Column(PG_JSON, nullable=False, default=list)
    is_selected = Column(Boolean, nullable=False, default=False)
    data_provenance = Column(String(50), nullable=False, default="ADVISORY")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    replan = relationship("ReplanModel", back_populates="options")
    recommendation = relationship("RecommendationModel", back_populates="alternatives", foreign_keys=[recommendation_id])


class RecommendationModel(Base):
    """
    Explainable operational recommendation generated from feasible candidate options.
    Awaiting human operator approval before application.
    """
    __tablename__ = "recommendations"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    replan_id = Column(PG_UUID, ForeignKey("replans.id"), nullable=False, index=True)
    option_id = Column(PG_UUID, ForeignKey("recommendation_alternatives.id"), nullable=True)
    trigger_event_id = Column(PG_UUID, ForeignKey("operational_events.id"), nullable=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    rationale = Column(PG_JSON, nullable=False, default=list)
    supporting_evidence = Column(PG_JSON, nullable=False, default=dict)
    constraint_evaluation_summary = Column(PG_JSON, nullable=False, default=dict)
    affected_entities = Column(PG_JSON, nullable=False, default=list)
    violated_constraints = Column(PG_JSON, nullable=False, default=list)
    proposed_changes = Column(PG_JSON, nullable=False, default=list)
    expected_impact = Column(PG_JSON, nullable=False, default=dict)
    assumptions = Column(PG_JSON, nullable=False, default=list)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    approval_state = Column(String(50), nullable=False, default="PROPOSED")
    status = Column(String(50), nullable=False, default=RecommendationStatus.PROPOSED.value, index=True)
    data_provenance = Column(String(50), nullable=False, default="ADVISORY")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    replan = relationship("ReplanModel", back_populates="recommendations")
    alternatives = relationship("ReplanOptionModel", back_populates="recommendation", foreign_keys=[ReplanOptionModel.recommendation_id])
    approvals = relationship("ApprovalModel", back_populates="recommendation", cascade="all, delete-orphan")


class ApprovalModel(Base):
    """
    Immutable human decision record governing the operational application of a recommendation.
    """
    __tablename__ = "approvals"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    recommendation_id = Column(PG_UUID, ForeignKey("recommendations.id"), nullable=False, index=True)
    approver_user_id = Column(PG_UUID, nullable=True)
    approver_person_id = Column(PG_UUID, ForeignKey("people.id"), nullable=False)
    approver_role = Column(String(100), nullable=True)
    decision = Column(String(50), nullable=True)  # APPROVED, REJECTED, MODIFIED
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    resulting_event_id = Column(PG_UUID, ForeignKey("operational_events.id"), nullable=True)
    status = Column(String(50), nullable=False, default=ApprovalStatus.PENDING.value, index=True)
    correlation_id = Column(PG_UUID, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    recommendation = relationship("RecommendationModel", back_populates="approvals")
