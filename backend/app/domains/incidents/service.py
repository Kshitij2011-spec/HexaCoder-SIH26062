"""Incident Response Domain Service Orchestrator."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.domains.incidents.models import IncidentModel, IncidentReferenceModel
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
)
from backend.app.domains.incidents.transitions import (
    validate_incident_transition,
    is_terminal_incident_status,
)
from backend.app.domains.incidents.schemas import (
    IncidentCreate,
    IncidentUpdate,
    IncidentReferenceCreate,
    IncidentTimelineRead,
    IncidentTimelineEntry,
)
from backend.app.domains.incidents.repository import IncidentRepository
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.assets.models import AssetModel
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import (
    EntityNotFoundError,
    ConflictError,
    DomainValidationError,
    InvalidStateTransitionError,
)


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime object is timezone-aware and normalized to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class IncidentService:
    """
    Authoritative domain service for operational Incident Response.
    Enforces the lifecycle state machine, loose resource references,
    terminal closed behavior, attributable audit trails, and immutable operational events.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = IncidentRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    # ============================================================
    # 1. INCIDENT CRUD
    # ============================================================

    def create_incident(
        self,
        data: IncidentCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Registers a new operational incident in OPEN status."""
        cid = correlation_id or uuid.uuid4()

        # Enforce unique incident_code
        if self.repo.get_by_code(data.incident_code):
            raise ConflictError(
                f"Incident with code '{data.incident_code}' already exists.",
                field="incident_code",
                details={"incident_code": data.incident_code},
            )

        # Validate priority bounds
        if data.priority < 1 or data.priority > 5:
            raise DomainValidationError(
                f"Priority must be between 1 and 5, received {data.priority}.",
                field="priority",
                details={"priority": data.priority},
            )

        # Validate location if provided
        if data.location_id:
            loc = self.session.execute(
                select(LocationModel).where(LocationModel.id == data.location_id)
            ).scalar_one_or_none()
            if not loc:
                raise EntityNotFoundError("Location", data.location_id)

        # Validate asset if provided
        if data.asset_id:
            asset = self.session.execute(
                select(AssetModel).where(AssetModel.id == data.asset_id)
            ).scalar_one_or_none()
            if not asset:
                raise EntityNotFoundError("Asset", data.asset_id)

        now = datetime.now(timezone.utc)
        detected_at = ensure_utc(data.detected_at) if data.detected_at else now

        incident = IncidentModel(
            id=uuid.uuid4(),
            incident_code=data.incident_code,
            expedition_id=data.expedition_id,
            title=data.title,
            type=data.incident_type,
            severity=data.severity.value,
            priority=data.priority,
            location_id=data.location_id,
            asset_id=data.asset_id,
            status=IncidentStatus.OPEN.value,
            description=data.description,
            detected_at=detected_at,
            operational_metadata=data.operational_metadata,
            data_provenance=data.data_provenance.value,
            created_at=now,
            updated_at=now,
        )
        created = self.repo.create_incident(incident)

        self.audit_service.record_audit(
            action="CREATE_INCIDENT",
            entity_type="INCIDENT",
            entity_id=created.id,
            after_snapshot={
                "incident_code": created.incident_code,
                "title": created.title,
                "type": created.type,
                "severity": created.severity,
                "priority": created.priority,
                "status": created.status,
                "location_id": str(created.location_id) if created.location_id else None,
                "asset_id": str(created.asset_id) if created.asset_id else None,
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="IncidentCreated",
            entity_type="INCIDENT",
            entity_id=created.id,
            new_state=created.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=created.location_id,
            correlation_id=cid,
            evidence={
                "incident_code": created.incident_code,
                "title": created.title,
                "severity": created.severity,
                "priority": created.priority,
            },
        )

        self.session.commit()
        return created

    def get_incident(self, incident_id: uuid.UUID) -> IncidentModel:
        """Retrieves incident by UUID or raises EntityNotFoundError."""
        incident = self.repo.get_by_id(incident_id)
        if not incident:
            raise EntityNotFoundError("Incident", incident_id)
        return incident

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[int] = None,
        location_id: Optional[uuid.UUID] = None,
        asset_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[IncidentModel], int]:
        """Lists incidents with optional filtering and pagination."""
        return self.repo.list_incidents(
            status=status,
            severity=severity,
            priority=priority,
            location_id=location_id,
            asset_id=asset_id,
            page=page,
            page_size=page_size,
        )

    def update_incident(
        self,
        incident_id: uuid.UUID,
        data: IncidentUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Updates mutable incident metadata. Strictly blocked on CLOSED incidents."""
        cid = correlation_id or uuid.uuid4()
        incident = self.get_incident(incident_id)

        # Enforce terminal CLOSED immutability
        if incident.status == IncidentStatus.CLOSED.value:
            raise InvalidStateTransitionError(
                entity_type="Incident",
                current_state=incident.status,
                target_state="UPDATE",
                allowed_transitions=[],
            )

        before_snapshot = {
            "title": incident.title,
            "type": incident.type,
            "severity": incident.severity,
            "priority": incident.priority,
            "description": incident.description,
        }

        if data.title is not None:
            incident.title = data.title
        if data.description is not None:
            incident.description = data.description
        if data.incident_type is not None:
            incident.type = data.incident_type
        if data.severity is not None:
            incident.severity = data.severity.value
        if data.priority is not None:
            if data.priority < 1 or data.priority > 5:
                raise DomainValidationError(f"Priority must be between 1 and 5, received {data.priority}.")
            incident.priority = data.priority
        if data.location_id is not None:
            loc = self.session.execute(select(LocationModel).where(LocationModel.id == data.location_id)).scalar_one_or_none()
            if not loc:
                raise EntityNotFoundError("Location", data.location_id)
            incident.location_id = data.location_id
        if data.asset_id is not None:
            asset = self.session.execute(select(AssetModel).where(AssetModel.id == data.asset_id)).scalar_one_or_none()
            if not asset:
                raise EntityNotFoundError("Asset", data.asset_id)
            incident.asset_id = data.asset_id
        if data.operational_metadata is not None:
            merged = dict(incident.operational_metadata or {})
            merged.update(data.operational_metadata)
            incident.operational_metadata = merged

        incident.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update_incident(incident)

        self.audit_service.record_audit(
            action="UPDATE_INCIDENT",
            entity_type="INCIDENT",
            entity_id=updated.id,
            before_snapshot=before_snapshot,
            after_snapshot={
                "title": updated.title,
                "type": updated.type,
                "severity": updated.severity,
                "priority": updated.priority,
                "description": updated.description,
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="IncidentUpdated",
            entity_type="INCIDENT",
            entity_id=updated.id,
            previous_state=updated.status,
            new_state=updated.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=updated.location_id,
            correlation_id=cid,
            evidence={"title": updated.title, "severity": updated.severity},
        )

        self.session.commit()
        return updated

    # ============================================================
    # 2. LIFECYCLE STATE TRANSITIONS
    # ============================================================

    def transition_incident_status(
        self,
        incident_id: uuid.UUID,
        target_status: IncidentStatus,
        reason: Optional[str] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """
        Executes a validated lifecycle transition, updates lifecycle timestamps,
        emits domain events, and creates audit records.
        """
        cid = correlation_id or uuid.uuid4()
        incident = self.get_incident(incident_id)
        current_status = IncidentStatus(incident.status)

        # Validate transition using authoritative state machine
        validate_incident_transition(current_status, target_status)

        prev_state = incident.status
        now = datetime.now(timezone.utc)

        # Lifecycle timestamp population (never overwrite existing timestamps unnecessarily)
        if target_status == IncidentStatus.ACKNOWLEDGED and not incident.acknowledged_at:
            incident.acknowledged_at = now
        elif target_status == IncidentStatus.RESOLVED and not incident.resolved_at:
            incident.resolved_at = now
        elif target_status == IncidentStatus.CLOSED and not incident.closed_at:
            incident.closed_at = now

        incident.status = target_status.value
        incident.updated_at = now

        if operational_metadata:
            merged = dict(incident.operational_metadata or {})
            merged.update(operational_metadata)
            incident.operational_metadata = merged

        updated = self.repo.update_incident(incident)

        # Map event type and audit action to target status
        event_map = {
            IncidentStatus.ACKNOWLEDGED: "IncidentAcknowledged",
            IncidentStatus.MITIGATING: "IncidentMitigationStarted",
            IncidentStatus.RESOLVED: "IncidentResolved",
            IncidentStatus.CLOSED: "IncidentClosed",
        }
        event_type = event_map.get(target_status, "IncidentStatusChanged")

        audit_map = {
            IncidentStatus.ACKNOWLEDGED: "ACKNOWLEDGE_INCIDENT",
            IncidentStatus.MITIGATING: "START_INCIDENT_MITIGATION",
            IncidentStatus.RESOLVED: "RESOLVE_INCIDENT",
            IncidentStatus.CLOSED: "CLOSE_INCIDENT",
        }
        audit_action = audit_map.get(target_status, "TRANSITION_INCIDENT_STATUS")

        self.audit_service.record_audit(
            action=audit_action,
            entity_type="INCIDENT",
            entity_id=updated.id,
            before_snapshot={"status": prev_state},
            after_snapshot={
                "status": updated.status,
                "reason": reason,
                "acknowledged_at": updated.acknowledged_at.isoformat() if updated.acknowledged_at else None,
                "resolved_at": updated.resolved_at.isoformat() if updated.resolved_at else None,
                "closed_at": updated.closed_at.isoformat() if updated.closed_at else None,
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type=event_type,
            entity_type="INCIDENT",
            entity_id=updated.id,
            previous_state=prev_state,
            new_state=updated.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=updated.location_id,
            correlation_id=cid,
            evidence={
                "incident_code": updated.incident_code,
                "reason": reason,
                "acknowledged_at": updated.acknowledged_at.isoformat() if updated.acknowledged_at else None,
                "resolved_at": updated.resolved_at.isoformat() if updated.resolved_at else None,
                "closed_at": updated.closed_at.isoformat() if updated.closed_at else None,
            },
        )

        self.session.commit()
        return updated

    def acknowledge_incident(
        self,
        incident_id: uuid.UUID,
        reason: Optional[str] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Transitions incident status to ACKNOWLEDGED."""
        return self.transition_incident_status(
            incident_id=incident_id,
            target_status=IncidentStatus.ACKNOWLEDGED,
            reason=reason,
            operational_metadata=operational_metadata,
            correlation_id=correlation_id,
            actor_person_id=actor_person_id,
        )

    def mitigate_incident(
        self,
        incident_id: uuid.UUID,
        reason: Optional[str] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Transitions incident status to MITIGATING."""
        return self.transition_incident_status(
            incident_id=incident_id,
            target_status=IncidentStatus.MITIGATING,
            reason=reason,
            operational_metadata=operational_metadata,
            correlation_id=correlation_id,
            actor_person_id=actor_person_id,
        )

    def resolve_incident(
        self,
        incident_id: uuid.UUID,
        reason: Optional[str] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Transitions incident status to RESOLVED."""
        return self.transition_incident_status(
            incident_id=incident_id,
            target_status=IncidentStatus.RESOLVED,
            reason=reason,
            operational_metadata=operational_metadata,
            correlation_id=correlation_id,
            actor_person_id=actor_person_id,
        )

    def close_incident(
        self,
        incident_id: uuid.UUID,
        reason: Optional[str] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentModel:
        """Transitions incident status to terminal CLOSED."""
        return self.transition_incident_status(
            incident_id=incident_id,
            target_status=IncidentStatus.CLOSED,
            reason=reason,
            operational_metadata=operational_metadata,
            correlation_id=correlation_id,
            actor_person_id=actor_person_id,
        )

    # ============================================================
    # 3. AFFECTED RESOURCE REFERENCES (LOOSE COUPLING & ISOLATION)
    # ============================================================

    def add_reference(
        self,
        incident_id: uuid.UUID,
        data: IncidentReferenceCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentReferenceModel:
        """
        Attaches a reference to an operational entity (Location, Asset, StockLot, Consignment, Leg).
        STRICT ISOLATION: Does NOT mutate the referenced entity state.
        """
        cid = correlation_id or uuid.uuid4()
        incident = self.get_incident(incident_id)

        # Enforce terminal CLOSED immutability
        if incident.status == IncidentStatus.CLOSED.value:
            raise ConflictError(
                f"Cannot add references to closed incident '{incident.incident_code}'.",
                field="status",
                details={"status": incident.status},
            )

        # Validate supported reference types
        if data.reference_type not in IncidentReferenceType:
            raise DomainValidationError(
                f"Unsupported reference type '{data.reference_type}'. Must be one of {[t.value for t in IncidentReferenceType]}."
            )

        # Validate UUID syntax
        if not isinstance(data.reference_id, uuid.UUID):
            try:
                ref_uuid = uuid.UUID(str(data.reference_id))
            except (ValueError, AttributeError):
                raise DomainValidationError(f"Invalid reference_id '{data.reference_id}', must be a valid UUID.")
        else:
            ref_uuid = data.reference_id

        # Collision protection: duplicate reference target check
        existing = self.repo.get_reference_by_target(
            incident_id=incident.id,
            reference_type=data.reference_type.value,
            reference_id=ref_uuid,
        )
        if existing:
            raise ConflictError(
                f"Incident already references {data.reference_type.value} '{ref_uuid}'.",
                field="reference_id",
            )

        ref = IncidentReferenceModel(
            id=uuid.uuid4(),
            incident_id=incident.id,
            reference_type=data.reference_type.value,
            reference_id=ref_uuid,
            notes=data.notes,
            operational_metadata=data.operational_metadata,
            created_at=datetime.now(timezone.utc),
        )
        created_ref = self.repo.create_reference(ref)

        self.audit_service.record_audit(
            action="ADD_INCIDENT_REFERENCE",
            entity_type="INCIDENT",
            entity_id=incident.id,
            after_snapshot={
                "reference_id": str(created_ref.id),
                "target_type": created_ref.reference_type,
                "target_id": str(created_ref.reference_id),
                "notes": created_ref.notes,
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.session.commit()
        return created_ref

    def list_references(self, incident_id: uuid.UUID) -> List[IncidentReferenceModel]:
        """Lists all resource references for an incident."""
        self.get_incident(incident_id)  # Validate incident exists
        return self.repo.list_references_by_incident(incident_id)

    # ============================================================
    # 4. TIMELINE AGGREGATION
    # ============================================================

    def get_incident_timeline(self, incident_id: uuid.UUID) -> IncidentTimelineRead:
        """
        Builds a deterministic, chronological timeline of the incident
        combining operational events, status transitions, and attached references.
        """
        incident = self.get_incident(incident_id)

        entries: List[IncidentTimelineEntry] = []

        # Pull immutable operational events from EventService
        events, _ = self.event_service.get_entity_history(
            entity_type="INCIDENT",
            entity_id=incident.id,
            page_size=100,
        )
        for ev in events:
            entries.append(
                IncidentTimelineEntry(
                    timestamp=ev.occurred_at,
                    entry_type="EVENT",
                    action_or_event=ev.event_type,
                    actor=str(ev.actor_id) if ev.actor_id else ev.actor_type,
                    description=f"Status: {ev.previous_state} -> {ev.new_state}" if ev.previous_state else f"State: {ev.new_state}",
                    correlation_id=str(ev.correlation_id) if ev.correlation_id else None,
                    details=ev.evidence or {},
                )
            )

        # Pull attached references
        refs = self.repo.list_references_by_incident(incident.id)
        for ref in refs:
            entries.append(
                IncidentTimelineEntry(
                    timestamp=ref.created_at,
                    entry_type="REFERENCE",
                    action_or_event="ReferenceAdded",
                    actor=None,
                    description=f"Linked {ref.reference_type}: {ref.reference_id}",
                    correlation_id=None,
                    details={"reference_type": ref.reference_type, "reference_id": str(ref.reference_id), "notes": ref.notes},
                )
            )

        # Sort deterministically: chronological timestamp ascending, with action_or_event as secondary key
        entries.sort(key=lambda x: (x.timestamp, x.action_or_event))

        return IncidentTimelineRead(
            incident_id=incident.id,
            incident_code=incident.incident_code,
            current_status=IncidentStatus(incident.status),
            entries=entries,
            total_entries=len(entries),
        )
