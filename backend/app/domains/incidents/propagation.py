"""Incident Propagation Domain Service Orchestrator.

Cross-domain operational impact propagation for active Incidents.
Coordinates authoritative domain services (Locations, Assets, Inventory, Cargo, Transport)
without duplicating their internal state machines or violating architectural boundaries.
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.domains.incidents.models import (
    IncidentModel,
    IncidentReferenceModel,
    IncidentPropagationModel,
)
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
    PropagationStatus,
    PropagationAction,
)
from backend.app.domains.incidents.schemas import (
    PropagationResult,
    IncidentPropagationSummary,
    IncidentPropagationRead,
)
from backend.app.domains.incidents.repository import IncidentRepository
from backend.app.domains.incidents.service import IncidentService

from backend.app.domains.locations.service import LocationService
from backend.app.domains.locations.transitions import ALLOWED_LOCATION_TRANSITIONS
from backend.app.shared.types.states import LocationStatus

from backend.app.domains.assets.service import AssetService
from backend.app.domains.assets.transitions import ALLOWED_ASSET_TRANSITIONS
from backend.app.domains.assets.schemas import AssetStatusTransitionRequest
from backend.app.domains.assets.states import AssetStatus

from backend.app.domains.inventory.service import (
    InventoryService,
    calculate_lot_availability,
)
from backend.app.domains.inventory.schemas import StockQuarantineRequest
from backend.app.shared.types.states import InventoryStatus

from backend.app.domains.cargo.service import CargoService
from backend.app.domains.transport.service import TransportService
from backend.app.domains.transport.transitions import (
    ALLOWED_TRANSPORT_TRANSITIONS,
    validate_transport_transition,
)
from backend.app.domains.transport.schemas import TransportLegDelayRequest
from backend.app.shared.types.states import TransportStatus

from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import (
    EntityNotFoundError,
    ConflictError,
    DomainValidationError,
    InvalidStateTransitionError,
)

ACTIVE_PROPAGATION_STATUSES = {
    IncidentStatus.OPEN.value,
    IncidentStatus.ACKNOWLEDGED.value,
    IncidentStatus.MITIGATING.value,
}

TERMINAL_TRANSPORT_STATES = {
    TransportStatus.CLOSED.value,
    TransportStatus.CANCELLED.value,
    TransportStatus.ARRIVED.value,
}


class IncidentPropagationService:
    """
    Dedicated orchestration service for propagating operational impacts from active incidents.
    Calls existing authoritative domain services and records deterministic, auditable results.
    """

    def __init__(self, session: Session):
        self.session = session
        self.incident_service = IncidentService(session)
        self.repo = IncidentRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

        # Authoritative domain services
        self.location_service = LocationService(session)
        self.asset_service = AssetService(session)
        self.inventory_service = InventoryService(session)
        self.cargo_service = CargoService(session)
        self.transport_service = TransportService(session)

    def propagate_incident_impact(
        self,
        incident_id: uuid.UUID,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
    ) -> IncidentPropagationSummary:
        """
        Explicitly propagates operational impact of an active incident across referenced resources.
        Enforces incident lifecycle status, respects domain state machines, and guarantees idempotency.
        """
        cid = correlation_id or uuid.uuid4()
        incident = self.incident_service.get_incident(incident_id)

        # Enforce lifecycle status rule: CLOSED incidents must strictly reject propagation
        if incident.status == IncidentStatus.CLOSED.value:
            raise ConflictError(
                f"Cannot propagate impact for CLOSED incident '{incident.incident_code}'.",
                field="status",
                details={"status": incident.status},
            )

        if incident.status not in ACTIVE_PROPAGATION_STATUSES:
            raise ConflictError(
                f"Cannot propagate impact for incident '{incident.incident_code}' in '{incident.status}' status. Incident must be active (OPEN, ACKNOWLEDGED, MITIGATING).",
                field="status",
                details={"status": incident.status},
            )

        actor_context = {
            "source": "INCIDENT_PROPAGATION",
            "actor_type": "USER" if actor_person_id else "SYSTEM",
            "actor_id": actor_person_id,
        }

        references = self.incident_service.list_references(incident.id)
        results: List[PropagationResult] = []

        for ref in references:
            res = self._propagate_single_reference(
                incident=incident,
                reference=ref,
                correlation_id=cid,
                actor_person_id=actor_person_id,
                actor_context=actor_context,
            )
            results.append(res)

        # Record audit log entry for the overall propagation batch
        audit_entry = self.audit_service.record_audit(
            action="PROPAGATE_INCIDENT_IMPACT",
            entity_type="INCIDENT",
            entity_id=incident.id,
            before_snapshot={"incident_code": incident.incident_code, "status": incident.status},
            after_snapshot={
                "total_references": len(results),
                "applied_count": sum(1 for r in results if r.status == PropagationStatus.APPLIED),
                "skipped_count": sum(1 for r in results if r.status == PropagationStatus.SKIPPED),
                "rejected_count": sum(1 for r in results if r.status == PropagationStatus.REJECTED),
                "requires_action_count": sum(1 for r in results if r.status == PropagationStatus.REQUIRES_OPERATOR_ACTION),
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )
        audit_id = audit_entry.id if hasattr(audit_entry, "id") else None

        # Persist propagation records and update with audit_id
        for res in results:
            res.audit_id = audit_id
            self._persist_propagation_record(incident.id, res)

        self.session.commit()

        return IncidentPropagationSummary(
            incident_id=incident.id,
            incident_code=incident.incident_code,
            total_references=len(results),
            applied_count=sum(1 for r in results if r.status == PropagationStatus.APPLIED),
            skipped_count=sum(1 for r in results if r.status == PropagationStatus.SKIPPED),
            rejected_count=sum(1 for r in results if r.status == PropagationStatus.REJECTED),
            requires_action_count=sum(1 for r in results if r.status == PropagationStatus.REQUIRES_OPERATOR_ACTION),
            results=results,
        )

    def list_propagations(self, incident_id: uuid.UUID) -> List[IncidentPropagationRead]:
        """Lists historical propagation records for an incident."""
        self.incident_service.get_incident(incident_id)  # Validate incident exists
        models = self.repo.list_propagations_by_incident(incident_id)
        return [IncidentPropagationRead.model_validate(m) for m in models]

    # ============================================================
    # PER-REFERENCE PROPAGATION ROUTERS
    # ============================================================

    def _propagate_single_reference(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
        correlation_id: uuid.UUID,
        actor_person_id: Optional[uuid.UUID],
        actor_context: Dict[str, Any],
    ) -> PropagationResult:
        """Routes a single incident reference to its authoritative domain handler."""
        ref_type = reference.reference_type
        ref_id = reference.reference_id

        if ref_type == IncidentReferenceType.LOCATION.value:
            return self._propagate_location(incident, reference, correlation_id, actor_context)
        elif ref_type == IncidentReferenceType.ASSET.value:
            return self._propagate_asset(incident, reference, correlation_id, actor_person_id)
        elif ref_type == IncidentReferenceType.INVENTORY_STOCK_LOT.value:
            return self._propagate_inventory(incident, reference, correlation_id, actor_person_id)
        elif ref_type == IncidentReferenceType.CARGO_CONSIGNMENT.value:
            return self._propagate_cargo(incident, reference)
        elif ref_type == IncidentReferenceType.TRANSPORT_LEG.value:
            return self._propagate_transport(incident, reference, correlation_id, actor_context)
        else:
            return PropagationResult(
                reference_id=ref_id,
                reference_type=ref_type,
                action=PropagationAction.NONE.value,
                status=PropagationStatus.NOT_SUPPORTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Reference type '{ref_type}' does not support automatic incident propagation",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

    # 1. LOCATION PROPAGATION
    def _propagate_location(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
        correlation_id: uuid.UUID,
        actor_context: Dict[str, Any],
    ) -> PropagationResult:
        loc_id = reference.reference_id
        try:
            loc = self.location_service.get_location(loc_id)
        except EntityNotFoundError:
            return PropagationResult(
                reference_id=loc_id,
                reference_type=reference.reference_type,
                action=PropagationAction.RESTRICT_LOCATION.value,
                status=PropagationStatus.REJECTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Referenced Location '{loc_id}' was not found",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Severity mapping
        if incident.severity in {IncidentSeverity.LOW.value, IncidentSeverity.MEDIUM.value}:
            return PropagationResult(
                reference_id=loc_id,
                reference_type=reference.reference_type,
                action=PropagationAction.RESTRICT_LOCATION.value,
                status=PropagationStatus.SKIPPED,
                previous_state=loc.status,
                resulting_state=loc.status,
                reason=f"Incident severity {incident.severity} does not trigger automatic location restriction",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        if incident.severity == IncidentSeverity.HIGH.value:
            target_status = LocationStatus.RESTRICTED.value
            action = PropagationAction.RESTRICT_LOCATION.value
        else:  # CRITICAL
            target_status = LocationStatus.INACCESSIBLE.value
            action = PropagationAction.ISOLATE_LOCATION.value

        # Idempotency check: already at target
        if loc.status == target_status:
            return PropagationResult(
                reference_id=loc_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=loc.status,
                resulting_state=loc.status,
                reason=f"Location is already {loc.status}",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Validate against authoritative Location state machine
        try:
            curr_enum = LocationStatus(loc.status)
        except ValueError:
            curr_enum = None

        allowed = [s.value for s in ALLOWED_LOCATION_TRANSITIONS.get(curr_enum, set())] if curr_enum else []
        if target_status not in allowed:
            return PropagationResult(
                reference_id=loc_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=loc.status,
                resulting_state=None,
                reason=f"Transition from {loc.status} to {target_status} is not allowed by Location state machine",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Call authoritative LocationService
        prev_state = loc.status
        updated_loc = self.location_service.update_location_state(
            location_id=loc.id,
            new_status=target_status,
            reason=f"Propagated from incident {incident.incident_code} ({incident.severity}): {incident.title}",
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

        # Emit operational event
        event = self._emit_impact_event(
            incident=incident,
            reference_type=reference.reference_type,
            reference_id=loc_id,
            action=action,
            previous_state=prev_state,
            resulting_state=updated_loc.status,
            reason=f"Location status transitioned to {updated_loc.status} due to {incident.severity} incident",
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

        return PropagationResult(
            reference_id=loc_id,
            reference_type=reference.reference_type,
            action=action,
            status=PropagationStatus.APPLIED,
            previous_state=prev_state,
            resulting_state=updated_loc.status,
            reason=f"Location status transitioned to {updated_loc.status} due to {incident.severity} incident",
            event_id=event.event_id if event else None,
            operational_metadata=reference.operational_metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    # 2. ASSET PROPAGATION
    def _propagate_asset(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
        correlation_id: uuid.UUID,
        actor_person_id: Optional[uuid.UUID],
    ) -> PropagationResult:
        asset_id = reference.reference_id
        try:
            asset = self.asset_service.get_asset(asset_id)
        except EntityNotFoundError:
            return PropagationResult(
                reference_id=asset_id,
                reference_type=reference.reference_type,
                action=PropagationAction.MAINTENANCE_ASSET.value,
                status=PropagationStatus.REJECTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Referenced Asset '{asset_id}' was not found",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Terminal state protection: RETIRED cannot be modified
        if asset.status == AssetStatus.RETIRED.value:
            return PropagationResult(
                reference_id=asset_id,
                reference_type=reference.reference_type,
                action=PropagationAction.MAINTENANCE_ASSET.value,
                status=PropagationStatus.REJECTED,
                previous_state=asset.status,
                resulting_state=None,
                reason="Cannot transition retired asset. RETIRED is a terminal lifecycle state.",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Severity mapping
        if incident.severity in {IncidentSeverity.LOW.value, IncidentSeverity.MEDIUM.value}:
            return PropagationResult(
                reference_id=asset_id,
                reference_type=reference.reference_type,
                action=PropagationAction.MAINTENANCE_ASSET.value,
                status=PropagationStatus.SKIPPED,
                previous_state=asset.status,
                resulting_state=asset.status,
                reason=f"Incident severity {incident.severity} does not trigger automatic asset transition",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Deterministic single action per severity
        if incident.severity == IncidentSeverity.HIGH.value:
            target_status = AssetStatus.MAINTENANCE
            action = PropagationAction.MAINTENANCE_ASSET.value
        else:  # CRITICAL
            target_status = AssetStatus.QUARANTINED
            action = PropagationAction.QUARANTINE_ASSET.value

        # Idempotency / active maintenance collision protection
        if asset.status == target_status.value:
            return PropagationResult(
                reference_id=asset_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=asset.status,
                resulting_state=asset.status,
                reason=f"Asset is already {asset.status}",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Check legality against authoritative Asset state machine
        try:
            curr_enum = AssetStatus(asset.status)
        except ValueError:
            curr_enum = None

        allowed = ALLOWED_ASSET_TRANSITIONS.get(curr_enum, set()) if curr_enum else set()
        if target_status not in allowed:
            return PropagationResult(
                reference_id=asset_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=asset.status,
                resulting_state=None,
                reason=f"Transition from {asset.status} to {target_status.value} not permitted by Asset state machine",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Call authoritative AssetService
        prev_state = asset.status
        updated_asset = self.asset_service.transition_asset_status(
            asset_id=asset.id,
            req=AssetStatusTransitionRequest(
                target_status=target_status,
                reason=f"Propagated from incident {incident.incident_code} ({incident.severity}): {incident.title}",
            ),
            correlation_id=correlation_id,
            actor_person_id=actor_person_id,
        )

        event = self._emit_impact_event(
            incident=incident,
            reference_type=reference.reference_type,
            reference_id=asset_id,
            action=action,
            previous_state=prev_state,
            resulting_state=updated_asset.status,
            reason=f"Asset status transitioned to {updated_asset.status} due to {incident.severity} incident",
            correlation_id=correlation_id,
            actor_context={"actor_id": actor_person_id, "actor_type": "USER" if actor_person_id else "SYSTEM", "source": "INCIDENT_PROPAGATION"},
        )

        return PropagationResult(
            reference_id=asset_id,
            reference_type=reference.reference_type,
            action=action,
            status=PropagationStatus.APPLIED,
            previous_state=prev_state,
            resulting_state=updated_asset.status,
            reason=f"Asset status transitioned to {updated_asset.status} due to {incident.severity} incident",
            event_id=event.event_id if event else None,
            operational_metadata=reference.operational_metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    # 3. INVENTORY PROPAGATION
    def _propagate_inventory(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
        correlation_id: uuid.UUID,
        actor_person_id: Optional[uuid.UUID],
    ) -> PropagationResult:
        lot_id = reference.reference_id
        action = PropagationAction.QUARANTINE_STOCK.value

        try:
            lot = self.inventory_service.get_stock_lot(lot_id)
        except EntityNotFoundError:
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Referenced Inventory Stock Lot '{lot_id}' was not found",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Check idempotency: did this incident already apply quarantine to this stock lot?
        existing_applied = self.repo.get_applied_propagation(
            incident_id=incident.id,
            reference_type=reference.reference_type,
            reference_id=lot_id,
        )
        if existing_applied:
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=lot.status,
                resulting_state=lot.status,
                reason="Stock lot has already been quarantined by this incident",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # If already completely quarantined
        if lot.status == InventoryStatus.QUARANTINED.value:
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=lot.status,
                resulting_state=lot.status,
                reason="Stock lot is already in QUARANTINED status",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Severity check
        if incident.severity in {IncidentSeverity.LOW.value, IncidentSeverity.MEDIUM.value}:
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=lot.status,
                resulting_state=lot.status,
                reason=f"Incident severity {incident.severity} does not trigger automatic stock quarantine",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Authoritative inventory availability calculation
        on_hand = Decimal(str(lot.on_hand_quantity))
        reserved = Decimal(str(lot.reserved_quantity))
        quarantined = Decimal(str(lot.quarantined_quantity))
        damaged = Decimal(str(lot.damaged_quantity))
        available, _ = calculate_lot_availability(on_hand, reserved, quarantined, damaged)

        if available <= Decimal("0"):
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=lot.status,
                resulting_state=lot.status,
                reason=f"Stock lot has no unreserved available quantity to quarantine (status: {lot.status})",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Determine quantity to quarantine (default to all unreserved available stock)
        req_qty = reference.operational_metadata.get("quantity")
        if req_qty is not None:
            try:
                qty_to_quarantine = min(Decimal(str(req_qty)), available)
            except Exception:
                qty_to_quarantine = available
        else:
            qty_to_quarantine = available

        if qty_to_quarantine <= Decimal("0"):
            return PropagationResult(
                reference_id=lot_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.SKIPPED,
                previous_state=lot.status,
                resulting_state=lot.status,
                reason="No quantity safely available for quarantine",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Authoritative quarantine operation
        prev_state = lot.status
        updated_lot = self.inventory_service.quarantine_stock(
            lot_id=lot.id,
            req=StockQuarantineRequest(
                quantity=qty_to_quarantine,
                reason=f"Propagated from incident {incident.incident_code}: {incident.title}",
                performed_by_person_id=actor_person_id,
                operational_metadata={"incident_id": str(incident.id)},
            ),
            correlation_id=correlation_id,
        )

        event = self._emit_impact_event(
            incident=incident,
            reference_type=reference.reference_type,
            reference_id=lot_id,
            action=action,
            previous_state=prev_state,
            resulting_state=updated_lot.status,
            reason=f"Quarantined {qty_to_quarantine} units due to incident",
            correlation_id=correlation_id,
            actor_context={"actor_id": actor_person_id, "actor_type": "USER" if actor_person_id else "SYSTEM", "source": "INCIDENT_PROPAGATION"},
        )

        return PropagationResult(
            reference_id=lot_id,
            reference_type=reference.reference_type,
            action=action,
            status=PropagationStatus.APPLIED,
            previous_state=prev_state,
            resulting_state=updated_lot.status,
            reason=f"Quarantined {qty_to_quarantine} units due to incident",
            event_id=event.event_id if event else None,
            operational_metadata=reference.operational_metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    # 4. CARGO PROPAGATION
    def _propagate_cargo(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
    ) -> PropagationResult:
        consignment_id = reference.reference_id
        action = PropagationAction.REVIEW_CARGO.value

        try:
            consignment = self.cargo_service.get_consignment(consignment_id)
        except EntityNotFoundError:
            return PropagationResult(
                reference_id=consignment_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Referenced Cargo Consignment '{consignment_id}' was not found",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Default canonical behavior per Section 12:
        # Do not invent statuses or mutate cargo unprompted; require human operator action.
        return PropagationResult(
            reference_id=consignment_id,
            reference_type=reference.reference_type,
            action=action,
            status=PropagationStatus.REQUIRES_OPERATOR_ACTION,
            previous_state=consignment.status,
            resulting_state=consignment.status,
            reason="Cargo impact requires explicit operator action.",
            operational_metadata=reference.operational_metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    # 5. TRANSPORT PROPAGATION
    def _propagate_transport(
        self,
        incident: IncidentModel,
        reference: IncidentReferenceModel,
        correlation_id: uuid.UUID,
        actor_context: Dict[str, Any],
    ) -> PropagationResult:
        leg_id = reference.reference_id
        action = PropagationAction.DELAY_TRANSPORT.value

        try:
            leg = self.transport_service.get_transport_leg(leg_id)
        except EntityNotFoundError:
            return PropagationResult(
                reference_id=leg_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=None,
                resulting_state=None,
                reason=f"Referenced Transport Leg '{leg_id}' was not found",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Terminal state protection
        if leg.status in TERMINAL_TRANSPORT_STATES:
            return PropagationResult(
                reference_id=leg_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=leg.status,
                resulting_state=None,
                reason=f"Cannot delay transport leg in terminal '{leg.status}' state",
                operational_metadata=reference.operational_metadata or {},
                created_at=datetime.now(timezone.utc),
            )

        # Check explicit delay parameters
        meta = reference.operational_metadata or {}
        new_eta_str = meta.get("new_estimated_arrival_at")
        delay_hours = meta.get("delay_hours")

        if not new_eta_str and delay_hours is None:
            return PropagationResult(
                reference_id=leg_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REQUIRES_OPERATOR_ACTION,
                previous_state=leg.status,
                resulting_state=leg.status,
                reason="Transport leg delay requires explicit new ETA or delay duration",
                operational_metadata=meta,
                created_at=datetime.now(timezone.utc),
            )

        # Parse / calculate new ETA
        if new_eta_str:
            try:
                new_eta = datetime.fromisoformat(str(new_eta_str))
            except Exception:
                return PropagationResult(
                    reference_id=leg_id,
                    reference_type=reference.reference_type,
                    action=action,
                    status=PropagationStatus.REJECTED,
                    previous_state=leg.status,
                    resulting_state=None,
                    reason=f"Invalid new_estimated_arrival_at format: '{new_eta_str}'",
                    operational_metadata=meta,
                    created_at=datetime.now(timezone.utc),
                )
        else:
            base_time = leg.estimated_arrival_at or leg.planned_arrival_at or datetime.now(timezone.utc)
            new_eta = base_time + timedelta(hours=float(delay_hours))

        # Validate transition to DELAYED per Transport state machine
        try:
            validate_transport_transition(leg.status, TransportStatus.DELAYED.value)
        except InvalidStateTransitionError as e:
            return PropagationResult(
                reference_id=leg_id,
                reference_type=reference.reference_type,
                action=action,
                status=PropagationStatus.REJECTED,
                previous_state=leg.status,
                resulting_state=None,
                reason=str(e),
                operational_metadata=meta,
                created_at=datetime.now(timezone.utc),
            )

        # Call authoritative TransportService
        prev_state = leg.status
        updated_leg, affected_consignments = self.transport_service.record_transport_delay(
            leg_id=leg.id,
            delay_data=TransportLegDelayRequest(
                new_estimated_arrival_at=new_eta,
                delay_reason=f"Propagated from incident {incident.incident_code}: {incident.title}",
                operational_metadata={"incident_id": str(incident.id)},
            ),
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

        event = self._emit_impact_event(
            incident=incident,
            reference_type=reference.reference_type,
            reference_id=leg_id,
            action=action,
            previous_state=prev_state,
            resulting_state=updated_leg.status,
            reason=f"Transport leg delayed to {new_eta.isoformat()} affecting {len(affected_consignments)} consignments",
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

        return PropagationResult(
            reference_id=leg_id,
            reference_type=reference.reference_type,
            action=action,
            status=PropagationStatus.APPLIED,
            previous_state=prev_state,
            resulting_state=updated_leg.status,
            reason=f"Transport leg delayed to {new_eta.isoformat()} affecting {len(affected_consignments)} consignments",
            event_id=event.event_id if event else None,
            operational_metadata=meta,
            created_at=datetime.now(timezone.utc),
        )

    # ============================================================
    # PERSISTENCE & EVENT HELPERS
    # ============================================================

    def _emit_impact_event(
        self,
        incident: IncidentModel,
        reference_type: str,
        reference_id: uuid.UUID,
        action: str,
        previous_state: Optional[str],
        resulting_state: Optional[str],
        reason: str,
        correlation_id: uuid.UUID,
        actor_context: Dict[str, Any],
    ) -> Any:
        """Emits an immutable OperationalEvent capturing the downstream impact."""
        return self.event_service.append_event(
            event_type="IncidentImpactPropagated",
            entity_type="INCIDENT",
            entity_id=incident.id,
            new_state=resulting_state or "APPLIED",
            previous_state=previous_state,
            source=actor_context.get("source", "INCIDENT_PROPAGATION"),
            actor_type=actor_context.get("actor_type", "SYSTEM"),
            actor_id=actor_context.get("actor_id"),
            evidence={
                "reference_type": reference_type,
                "reference_id": str(reference_id),
                "action": action,
                "reason": reason,
                "status": "APPLIED",
            },
            correlation_id=correlation_id,
        )

    def _persist_propagation_record(
        self,
        incident_id: uuid.UUID,
        result: PropagationResult,
    ) -> IncidentPropagationModel:
        """Persists or updates an incident propagation record for idempotency and auditability."""
        existing = self.repo.get_propagation_by_target(
            incident_id=incident_id,
            reference_type=result.reference_type,
            reference_id=result.reference_id,
            action=result.action,
        )
        if existing:
            existing.status = result.status.value
            existing.previous_state = result.previous_state
            existing.resulting_state = result.resulting_state
            existing.reason = result.reason
            existing.event_id = result.event_id
            existing.audit_id = result.audit_id
            existing.operational_metadata = result.operational_metadata
            return existing

        record = IncidentPropagationModel(
            id=uuid.uuid4(),
            incident_id=incident_id,
            reference_id=result.reference_id,
            reference_type=result.reference_type,
            action=result.action,
            status=result.status.value,
            previous_state=result.previous_state,
            resulting_state=result.resulting_state,
            reason=result.reason,
            event_id=result.event_id,
            audit_id=result.audit_id,
            operational_metadata=result.operational_metadata,
            created_at=datetime.now(timezone.utc),
        )
        return self.repo.create_propagation(record)
