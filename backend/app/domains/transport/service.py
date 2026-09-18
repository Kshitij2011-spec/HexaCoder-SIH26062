"""Transport Application Service (Delay Propagation, Cargo Integration, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.transport.models import TransportLegModel, TransportCargoAssignmentModel
from backend.app.domains.transport.repository import TransportRepository
from backend.app.domains.transport.schemas import (
    TransportLegCreate,
    TransportLegUpdate,
    TransportLegDelayRequest,
    TransportDelayImpactResponse,
    TransportLegRead,
)
from backend.app.domains.transport.transitions import validate_transport_transition
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.cargo.service import CargoService
from backend.app.domains.cargo.schemas import CargoConsignmentRead
from backend.app.shared.types.states import TransportStatus, AssignmentStatus
from backend.app.shared.types.provenance import DataProvenance
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError, DomainValidationError


class TransportService:
    """
    Domain service for Transport Legs and Manifest Cargo Assignments.
    Note: Direction of dependency is strictly TransportService -> CargoService (never reverse).
    """

    def __init__(self, session: Session):
        self.session = session
        self.repository = TransportRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_transport_leg(
        self,
        data: TransportLegCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TransportLegModel:
        """Creates a transport leg and emits an immutable TransportLegCreated event."""
        existing = self.repository.get_by_code(data.code)
        if existing:
            raise ConflictError(
                f"A transport leg with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = TransportLegModel(
            code=data.code,
            expedition_id=data.expedition_id,
            mode=data.mode,
            origin_location_id=data.origin_location_id,
            destination_location_id=data.destination_location_id,
            departure_window_open=data.departure_window_open,
            departure_window_close=data.departure_window_close,
            arrival_window_open=data.arrival_window_open,
            arrival_window_close=data.arrival_window_close,
            planned_departure_at=data.planned_departure_at,
            planned_arrival_at=data.planned_arrival_at,
            estimated_departure_at=data.estimated_departure_at or data.planned_departure_at,
            estimated_arrival_at=data.estimated_arrival_at or data.planned_arrival_at,
            capacity=data.capacity,
            capacity_unit=data.capacity_unit,
            status=data.status.value,
            delay_reason=data.delay_reason,
            operational_metadata=data.operational_metadata,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            self.event_service.append_event(
                event_type="TransportLegCreated",
                entity_type="TRANSPORT_LEG",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=created.origin_location_id,
                evidence={
                    "code": created.code,
                    "mode": created.mode,
                    "origin": str(created.origin_location_id),
                    "destination": str(created.destination_location_id)
                },
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            self.audit_service.record_audit(
                action="CREATE_TRANSPORT_LEG",
                entity_type="TRANSPORT_LEG",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "mode": created.mode,
                    "status": created.status,
                    "planned_arrival_at": created.planned_arrival_at.isoformat() if created.planned_arrival_at else None
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_transport_leg(self, leg_id: uuid.UUID) -> TransportLegModel:
        leg = self.repository.get_by_id(leg_id)
        if not leg:
            raise EntityNotFoundError("TransportLeg", leg_id)
        return leg

    def list_transport_legs(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        origin_location_id: Optional[uuid.UUID] = None,
        destination_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TransportLegModel], int]:
        return self.repository.list_legs(
            expedition_id=expedition_id,
            mode=mode,
            status=status,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            page=page,
            page_size=page_size
        )

    def update_transport_leg(
        self,
        leg_id: uuid.UUID,
        data: TransportLegUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TransportLegModel:
        """Updates transport leg attributes or executes validated lifecycle transition."""
        leg = self.get_transport_leg(leg_id)
        previous_status = leg.status

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "status": leg.status,
            "estimated_arrival_at": leg.estimated_arrival_at.isoformat() if leg.estimated_arrival_at else None,
            "delay_reason": leg.delay_reason
        }

        status_changed = False
        if data.status and data.status.value != leg.status:
            validate_transport_transition(leg.status, data.status.value)
            leg.status = data.status.value
            status_changed = True

        if data.mode is not None:
            leg.mode = data.mode
        if data.origin_location_id is not None:
            leg.origin_location_id = data.origin_location_id
        if data.destination_location_id is not None:
            leg.destination_location_id = data.destination_location_id
        if data.departure_window_open is not None:
            leg.departure_window_open = data.departure_window_open
        if data.departure_window_close is not None:
            leg.departure_window_close = data.departure_window_close
        if data.arrival_window_open is not None:
            leg.arrival_window_open = data.arrival_window_open
        if data.arrival_window_close is not None:
            leg.arrival_window_close = data.arrival_window_close
        if data.planned_departure_at is not None:
            leg.planned_departure_at = data.planned_departure_at
        if data.planned_arrival_at is not None:
            leg.planned_arrival_at = data.planned_arrival_at
        if data.estimated_departure_at is not None:
            leg.estimated_departure_at = data.estimated_departure_at
        if data.estimated_arrival_at is not None:
            leg.estimated_arrival_at = data.estimated_arrival_at
        if data.actual_departure_at is not None:
            leg.actual_departure_at = data.actual_departure_at
        if data.actual_arrival_at is not None:
            leg.actual_arrival_at = data.actual_arrival_at
        if data.capacity is not None:
            leg.capacity = data.capacity
        if data.capacity_unit is not None:
            leg.capacity_unit = data.capacity_unit
        if data.delay_reason is not None:
            leg.delay_reason = data.delay_reason
        if data.operational_metadata is not None:
            leg.operational_metadata = data.operational_metadata

        leg.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(leg)

            if status_changed:
                self.event_service.append_event(
                    event_type="TransportLegStatusChanged",
                    entity_type="TRANSPORT_LEG",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"code": updated.code},
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_TRANSPORT_LEG",
                entity_type="TRANSPORT_LEG",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "status": updated.status,
                    "estimated_arrival_at": updated.estimated_arrival_at.isoformat() if updated.estimated_arrival_at else None,
                    "delay_reason": updated.delay_reason
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def record_transport_delay(
        self,
        leg_id: uuid.UUID,
        delay_data: TransportLegDelayRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[TransportLegModel, List[CargoConsignmentModel]]:
        """
        Executes operational transport delay and deterministically propagates ETA/risk to all assigned cargo.

        Causal Chain:
        API Action -> DELAY_TRANSPORT_LEG (Single audit record with unified correlation ID)
        -> TransportLeg delayed & updated
        -> TransportLegDelayed operational event emitted
        -> CargoService invoked to update cargo ETA & calculate domain-authoritative risk
        -> CargoConsignmentETAUpdated & CargoConsignmentDelayed events emitted
        """
        leg = self.get_transport_leg(leg_id)
        previous_status = leg.status
        previous_eta = leg.estimated_arrival_at

        # Validate transition to DELAYED (allows direct READY -> DELAYED, DEPARTED -> DELAYED, IN_TRANSIT -> DELAYED)
        validate_transport_transition(leg.status, TransportStatus.DELAYED.value)

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        # Update transport leg state
        leg.status = TransportStatus.DELAYED.value
        leg.estimated_arrival_at = delay_data.new_estimated_arrival_at
        leg.delay_reason = delay_data.delay_reason
        if delay_data.operational_metadata:
            leg.operational_metadata = {**leg.operational_metadata, **delay_data.operational_metadata}
        leg.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated_leg = self.repository.update(leg)

            # Retrieve active cargo consignments manifesting on this transport leg
            affected_cargo = self.repository.list_active_cargo_consignments_for_leg(updated_leg.id)

            # Emit operational event for the transport leg delay
            self.event_service.append_event(
                event_type="TransportLegDelayed",
                entity_type="TRANSPORT_LEG",
                entity_id=updated_leg.id,
                new_state=updated_leg.status,
                previous_state=previous_status,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=updated_leg.origin_location_id,
                evidence={
                    "code": updated_leg.code,
                    "previous_estimated_arrival_at": previous_eta.isoformat() if previous_eta else None,
                    "new_estimated_arrival_at": updated_leg.estimated_arrival_at.isoformat(),
                    "delay_reason": updated_leg.delay_reason,
                    "affected_consignments_count": len(affected_cargo),
                    "affected_consignments": [str(c.id) for c in affected_cargo]
                },
                correlation_id=cid,
                data_provenance=DataProvenance.SYNTHETIC_DEMO
            )

            # Single authoritative audit entry capturing causal operation
            self.audit_service.record_audit(
                action="DELAY_TRANSPORT_LEG",
                entity_type="TRANSPORT_LEG",
                entity_id=updated_leg.id,
                before_snapshot={
                    "status": previous_status,
                    "estimated_arrival_at": previous_eta.isoformat() if previous_eta else None
                },
                after_snapshot={
                    "status": updated_leg.status,
                    "estimated_arrival_at": updated_leg.estimated_arrival_at.isoformat(),
                    "delay_reason": updated_leg.delay_reason,
                    "affected_consignments_count": len(affected_cargo)
                },
                correlation_id=cid
            )

            # One-directional call to CargoService for deterministic risk & ETA propagation
            cargo_service = CargoService(self.session)
            updated_consignments = []
            for cargo in affected_cargo:
                updated_c = cargo_service.apply_transport_delay(
                    consignment_id=cargo.id,
                    transport_leg_code=updated_leg.code,
                    new_estimated_arrival=delay_data.new_estimated_arrival_at,
                    delay_reason=delay_data.delay_reason,
                    correlation_id=cid,
                    actor_context=actor
                )
                updated_consignments.append(updated_c)

        self.session.commit()
        return updated_leg, updated_consignments

    # ------------------------------------------------------------
    # Cargo Assignment Methods
    # ------------------------------------------------------------

    def assign_cargo_to_transport(
        self,
        transport_leg_id: uuid.UUID,
        cargo_consignment_id: uuid.UUID,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TransportCargoAssignmentModel:
        """Associates a cargo consignment with a transport leg (Cargo MOVES_VIA Transport Leg)."""
        leg = self.get_transport_leg(transport_leg_id)
        cargo_service = CargoService(self.session)
        consignment = cargo_service.get_consignment(cargo_consignment_id)

        existing = self.repository.get_assignment(transport_leg_id, cargo_consignment_id)
        if existing and existing.released_at is None:
            raise ConflictError(
                f"Cargo consignment '{consignment.code}' is already actively assigned to transport leg '{leg.code}'.",
                field="cargo_consignment_id"
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        assignment = TransportCargoAssignmentModel(
            transport_leg_id=leg.id,
            cargo_consignment_id=consignment.id,
            status=AssignmentStatus.APPROVED.value,
        )

        with self.session.begin_nested():
            created = self.repository.create_cargo_assignment(assignment)

            self.event_service.append_event(
                event_type="CargoAssignedToTransport",
                entity_type="TRANSPORT_LEG",
                entity_id=leg.id,
                new_state=AssignmentStatus.APPROVED.value,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={
                    "transport_leg_code": leg.code,
                    "cargo_consignment_code": consignment.code,
                    "consignment_id": str(consignment.id)
                },
                correlation_id=cid
            )

            self.audit_service.record_audit(
                action="ASSIGN_CARGO_TO_TRANSPORT",
                entity_type="TRANSPORT_CARGO_ASSIGNMENT",
                entity_id=created.id,
                after_snapshot={
                    "transport_leg_id": str(leg.id),
                    "cargo_consignment_id": str(consignment.id),
                    "status": created.status
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def list_cargo_for_transport_leg(self, transport_leg_id: uuid.UUID) -> List[CargoConsignmentModel]:
        """Lists all active cargo consignments manifesting on a transport leg."""
        self.get_transport_leg(transport_leg_id)
        return self.repository.list_active_cargo_consignments_for_leg(transport_leg_id)
