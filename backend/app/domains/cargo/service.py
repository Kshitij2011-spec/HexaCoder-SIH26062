"""Cargo Application Service (Domain-Authoritative Risk Engine, Events, Audit)."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.cargo.repository import CargoRepository
from backend.app.domains.cargo.schemas import (
    CargoConsignmentCreate,
    CargoConsignmentUpdate,
    CargoPackageCreate,
    CargoPackageUpdate,
    CargoTimelineRead,
)
from backend.app.domains.cargo.transitions import (
    validate_cargo_consignment_transition,
    validate_cargo_package_transition,
)
from backend.app.shared.types.states import CargoStatus, CargoPackageStatus, CargoRiskLevel
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime object is timezone-aware and normalized to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_cargo_risk(
    status: str,
    estimated_arrival_at: Optional[datetime],
    required_by_at: datetime
) -> str:
    """
    Domain-Authoritative Deterministic Cargo Risk Calculation.

    Rules:
    - DAMAGED / LOST / REJECTED -> CRITICAL
    - If estimated_arrival_at is None -> MODERATE (unconfirmed ETA)
    - If ETA > required_by -> CRITICAL (deadline missed / late delivery)
    - buffer = required_by - ETA:
        - buffer < 48 hours -> ELEVATED
        - buffer < 120 hours (5 days) -> MODERATE
        - otherwise -> NOMINAL
    """
    if status in [CargoStatus.DAMAGED.value, CargoStatus.LOST.value, CargoStatus.REJECTED.value]:
        return CargoRiskLevel.CRITICAL.value

    if estimated_arrival_at is None:
        return CargoRiskLevel.MODERATE.value

    utc_eta = ensure_utc(estimated_arrival_at)
    utc_req = ensure_utc(required_by_at)

    if utc_eta > utc_req:
        return CargoRiskLevel.CRITICAL.value

    buffer = utc_req - utc_eta

    if buffer < timedelta(hours=48):
        return CargoRiskLevel.ELEVATED.value
    elif buffer < timedelta(hours=120):
        return CargoRiskLevel.MODERATE.value
    else:
        return CargoRiskLevel.NOMINAL.value


class CargoService:
    """Domain service for Cargo Consignments and Packages."""

    def __init__(self, session: Session):
        self.session = session
        self.repository = CargoRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    # ------------------------------------------------------------
    # Consignment Methods
    # ------------------------------------------------------------

    def create_consignment(
        self,
        data: CargoConsignmentCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> CargoConsignmentModel:
        """Registers a cargo consignment, evaluates initial risk, and emits CargoConsignmentCreated."""
        existing = self.repository.get_by_code(data.code)
        if existing:
            raise ConflictError(
                f"A cargo consignment with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        initial_risk = calculate_cargo_risk(
            status=data.status.value,
            estimated_arrival_at=data.estimated_arrival_at or data.planned_arrival_at,
            required_by_at=data.required_by_at
        )

        model = CargoConsignmentModel(
            code=data.code,
            expedition_id=data.expedition_id,
            origin_location_id=data.origin_location_id,
            destination_location_id=data.destination_location_id,
            priority=data.priority,
            required_by_at=data.required_by_at,
            planned_arrival_at=data.planned_arrival_at,
            estimated_arrival_at=data.estimated_arrival_at or data.planned_arrival_at,
            transport_plan_summary=data.transport_plan_summary,
            compliance_status=data.compliance_status,
            status=data.status.value,
            risk_level=initial_risk,
            handling_classification=data.handling_classification,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            self.event_service.append_event(
                event_type="CargoConsignmentCreated",
                entity_type="CARGO_CONSIGNMENT",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={
                    "code": created.code,
                    "priority": created.priority,
                    "risk_level": created.risk_level,
                    "required_by_at": created.required_by_at.isoformat()
                },
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            self.audit_service.record_audit(
                action="CREATE_CARGO_CONSIGNMENT",
                entity_type="CARGO_CONSIGNMENT",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "status": created.status,
                    "risk_level": created.risk_level,
                    "required_by_at": created.required_by_at.isoformat()
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_consignment(self, consignment_id: uuid.UUID) -> CargoConsignmentModel:
        consignment = self.repository.get_by_id(consignment_id)
        if not consignment:
            raise EntityNotFoundError("CargoConsignment", consignment_id)
        return consignment

    def list_consignments(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        origin_location_id: Optional[uuid.UUID] = None,
        destination_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CargoConsignmentModel], int]:
        return self.repository.list_consignments(
            expedition_id=expedition_id,
            status=status,
            risk_level=risk_level,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            page=page,
            page_size=page_size
        )

    def update_consignment(
        self,
        consignment_id: uuid.UUID,
        data: CargoConsignmentUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> CargoConsignmentModel:
        """Updates consignment attributes, recalculates deterministic risk, and validates transitions."""
        consignment = self.get_consignment(consignment_id)
        previous_status = consignment.status
        previous_risk = consignment.risk_level

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "status": consignment.status,
            "risk_level": consignment.risk_level,
            "estimated_arrival_at": consignment.estimated_arrival_at.isoformat() if consignment.estimated_arrival_at else None,
            "required_by_at": consignment.required_by_at.isoformat()
        }

        status_changed = False
        if data.status and data.status.value != consignment.status:
            validate_cargo_consignment_transition(consignment.status, data.status.value)
            consignment.status = data.status.value
            status_changed = True

        if data.priority is not None:
            consignment.priority = data.priority
        if data.origin_location_id is not None:
            consignment.origin_location_id = data.origin_location_id
        if data.destination_location_id is not None:
            consignment.destination_location_id = data.destination_location_id
        if data.required_by_at is not None:
            consignment.required_by_at = data.required_by_at
        if data.planned_arrival_at is not None:
            consignment.planned_arrival_at = data.planned_arrival_at
        if data.estimated_arrival_at is not None:
            consignment.estimated_arrival_at = data.estimated_arrival_at
        if data.transport_plan_summary is not None:
            consignment.transport_plan_summary = data.transport_plan_summary
        if data.compliance_status is not None:
            consignment.compliance_status = data.compliance_status
        if data.handling_classification is not None:
            consignment.handling_classification = data.handling_classification
        if data.exception_reason is not None:
            consignment.exception_reason = data.exception_reason

        # Recalculate deterministic risk
        consignment.risk_level = calculate_cargo_risk(
            status=consignment.status,
            estimated_arrival_at=consignment.estimated_arrival_at,
            required_by_at=consignment.required_by_at
        )

        consignment.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(consignment)

            if status_changed:
                self.event_service.append_event(
                    event_type="CargoConsignmentStatusChanged",
                    entity_type="CARGO_CONSIGNMENT",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"risk_level": updated.risk_level},
                    correlation_id=cid
                )

            if data.estimated_arrival_at is not None:
                self.event_service.append_event(
                    event_type="CargoConsignmentETAUpdated",
                    entity_type="CARGO_CONSIGNMENT",
                    entity_id=updated.id,
                    new_state=updated.risk_level,
                    previous_state=previous_risk,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={
                        "estimated_arrival_at": updated.estimated_arrival_at.isoformat() if updated.estimated_arrival_at else None,
                        "risk_level": updated.risk_level
                    },
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_CARGO_CONSIGNMENT",
                entity_type="CARGO_CONSIGNMENT",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "status": updated.status,
                    "risk_level": updated.risk_level,
                    "estimated_arrival_at": updated.estimated_arrival_at.isoformat() if updated.estimated_arrival_at else None,
                    "required_by_at": updated.required_by_at.isoformat()
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def apply_transport_delay(
        self,
        consignment_id: uuid.UUID,
        transport_leg_code: str,
        new_estimated_arrival: datetime,
        delay_reason: str,
        correlation_id: uuid.UUID,
        actor_context: Dict[str, Any]
    ) -> CargoConsignmentModel:
        """
        Invoked by TransportService to propagate transport delay to affected cargo.
        Updates estimated arrival, recalculates domain-authoritative risk,
        and emits operational events under the shared operational correlation ID.
        """
        consignment = self.get_consignment(consignment_id)
        previous_status = consignment.status
        previous_risk = consignment.risk_level

        consignment.estimated_arrival_at = new_estimated_arrival
        consignment.exception_reason = f"Transport leg {transport_leg_code} delayed: {delay_reason}"

        # Authoritative deterministic risk
        new_risk = calculate_cargo_risk(
            status=consignment.status,
            estimated_arrival_at=new_estimated_arrival,
            required_by_at=consignment.required_by_at
        )
        consignment.risk_level = new_risk

        # If deadline is breached or risk becomes CRITICAL, transition status to DELAYED if not already terminal
        status_transitioned_to_delayed = False
        if new_risk == CargoRiskLevel.CRITICAL.value or ensure_utc(new_estimated_arrival) > ensure_utc(consignment.required_by_at):
            if consignment.status in [CargoStatus.IN_TRANSIT.value, CargoStatus.READY.value, CargoStatus.DISPATCHED.value]:
                consignment.status = CargoStatus.DELAYED.value
                status_transitioned_to_delayed = True

        consignment.updated_at = datetime.now(timezone.utc)
        updated = self.repository.update(consignment)

        # Emit operational event: CargoConsignmentETAUpdated
        self.event_service.append_event(
            event_type="CargoConsignmentETAUpdated",
            entity_type="CARGO_CONSIGNMENT",
            entity_id=updated.id,
            new_state=updated.risk_level,
            previous_state=previous_risk,
            source=actor_context.get("source", "API"),
            actor_type=actor_context.get("actor_type", "SYSTEM"),
            actor_id=actor_context.get("actor_id"),
            evidence={
                "transport_leg_code": transport_leg_code,
                "new_estimated_arrival_at": updated.estimated_arrival_at.isoformat() if updated.estimated_arrival_at else None,
                "required_by_at": updated.required_by_at.isoformat(),
                "delay_reason": delay_reason,
                "risk_level": updated.risk_level
            },
            correlation_id=correlation_id
        )

        # Emit operational event: CargoConsignmentDelayed if status changed to DELAYED
        if status_transitioned_to_delayed:
            self.event_service.append_event(
                event_type="CargoConsignmentDelayed",
                entity_type="CARGO_CONSIGNMENT",
                entity_id=updated.id,
                new_state=CargoStatus.DELAYED.value,
                previous_state=previous_status,
                source=actor_context.get("source", "API"),
                actor_type=actor_context.get("actor_type", "SYSTEM"),
                actor_id=actor_context.get("actor_id"),
                evidence={
                    "transport_leg_code": transport_leg_code,
                    "delay_reason": delay_reason,
                    "risk_level": updated.risk_level
                },
                correlation_id=correlation_id
            )

        return updated

    def get_timeline(self, consignment_id: uuid.UUID) -> CargoTimelineRead:
        """Calculates timeline, remaining buffer hours, and delivery health."""
        consignment = self.get_consignment(consignment_id)
        buffer_hours: Optional[float] = None
        if consignment.estimated_arrival_at:
            utc_eta = ensure_utc(consignment.estimated_arrival_at)
            utc_req = ensure_utc(consignment.required_by_at)
            delta = utc_req - utc_eta
            buffer_hours = round(delta.total_seconds() / 3600.0, 1)

        is_delayed = (
            consignment.status == CargoStatus.DELAYED.value
            or (consignment.estimated_arrival_at is not None and ensure_utc(consignment.estimated_arrival_at) > ensure_utc(consignment.required_by_at))
        )

        return CargoTimelineRead(
            consignment_id=consignment.id,
            code=consignment.code,
            required_by_at=consignment.required_by_at,
            planned_arrival_at=consignment.planned_arrival_at,
            estimated_arrival_at=consignment.estimated_arrival_at,
            buffer_hours=buffer_hours,
            status=CargoStatus(consignment.status),
            risk_level=CargoRiskLevel(consignment.risk_level),
            is_delayed=is_delayed,
            exception_reason=consignment.exception_reason
        )

    # ------------------------------------------------------------
    # Package Methods
    # ------------------------------------------------------------

    def create_package(
        self,
        consignment_id: uuid.UUID,
        data: CargoPackageCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> CargoPackageModel:
        """Adds a physical package to a consignment and emits CargoPackageCreated."""
        # Ensure parent consignment exists
        consignment = self.get_consignment(consignment_id)

        existing = self.repository.get_package_by_code(data.code)
        if existing:
            raise ConflictError(
                f"A cargo package with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        package = CargoPackageModel(
            code=data.code,
            consignment_id=consignment.id,
            contents_summary=data.contents_summary,
            quantity=data.quantity,
            weight_kg=data.weight_kg,
            length_cm=data.length_cm,
            width_cm=data.width_cm,
            height_cm=data.height_cm,
            handling_classification=data.handling_classification,
            current_location_id=data.current_location_id or consignment.origin_location_id,
            current_transport_leg_id=data.current_transport_leg_id,
            condition=data.condition,
            status=data.status.value,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create_package(package)

            self.event_service.append_event(
                event_type="CargoPackageCreated",
                entity_type="CARGO_PACKAGE",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=created.current_location_id,
                evidence={"code": created.code, "consignment_code": consignment.code},
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            self.audit_service.record_audit(
                action="CREATE_CARGO_PACKAGE",
                entity_type="CARGO_PACKAGE",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "consignment_id": str(consignment.id),
                    "status": created.status
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_package(self, package_id: uuid.UUID) -> CargoPackageModel:
        pkg = self.repository.get_package_by_id(package_id)
        if not pkg:
            raise EntityNotFoundError("CargoPackage", package_id)
        return pkg

    def list_packages_by_consignment(self, consignment_id: uuid.UUID) -> List[CargoPackageModel]:
        self.get_consignment(consignment_id)
        return self.repository.list_packages_by_consignment(consignment_id)

    def update_package(
        self,
        package_id: uuid.UUID,
        data: CargoPackageUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> CargoPackageModel:
        """Updates package status or physical location/transport assignment."""
        pkg = self.get_package(package_id)
        previous_status = pkg.status

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "status": pkg.status,
            "condition": pkg.condition,
            "current_location_id": str(pkg.current_location_id) if pkg.current_location_id else None,
            "current_transport_leg_id": str(pkg.current_transport_leg_id) if pkg.current_transport_leg_id else None
        }

        status_changed = False
        if data.status and data.status.value != pkg.status:
            validate_cargo_package_transition(pkg.status, data.status.value)
            pkg.status = data.status.value
            status_changed = True

        if data.contents_summary is not None:
            pkg.contents_summary = data.contents_summary
        if data.quantity is not None:
            pkg.quantity = data.quantity
        if data.weight_kg is not None:
            pkg.weight_kg = data.weight_kg
        if data.length_cm is not None:
            pkg.length_cm = data.length_cm
        if data.width_cm is not None:
            pkg.width_cm = data.width_cm
        if data.height_cm is not None:
            pkg.height_cm = data.height_cm
        if data.handling_classification is not None:
            pkg.handling_classification = data.handling_classification
        if data.current_location_id is not None:
            pkg.current_location_id = data.current_location_id
        if data.current_transport_leg_id is not None:
            pkg.current_transport_leg_id = data.current_transport_leg_id
        if data.condition is not None:
            pkg.condition = data.condition

        pkg.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update_package(pkg)

            if status_changed:
                self.event_service.append_event(
                    event_type="CargoPackageStatusChanged",
                    entity_type="CARGO_PACKAGE",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    location_id=updated.current_location_id,
                    evidence={"code": updated.code},
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_CARGO_PACKAGE",
                entity_type="CARGO_PACKAGE",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "status": updated.status,
                    "condition": updated.condition,
                    "current_location_id": str(updated.current_location_id) if updated.current_location_id else None,
                    "current_transport_leg_id": str(updated.current_transport_leg_id) if updated.current_transport_leg_id else None
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated
