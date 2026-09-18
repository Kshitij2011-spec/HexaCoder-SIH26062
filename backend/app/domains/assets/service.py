"""Assets and Maintenance Application Service."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.domains.assets.models import AssetModel, MaintenanceRecordModel
from backend.app.domains.assets.repository import AssetRepository
from backend.app.domains.assets.states import AssetStatus, MaintenanceStatus
from backend.app.domains.assets.transitions import (
    validate_asset_transition,
    validate_maintenance_transition,
)
from backend.app.domains.assets.schemas import (
    AssetCreate,
    AssetUpdate,
    AssetStatusTransitionRequest,
    AssetMoveRequest,
    MaintenanceScheduleRequest,
    MaintenanceStartRequest,
    MaintenanceCompleteRequest,
    MaintenanceCancelRequest,
    MaintenanceRecordRead,
    AssetTimelineRead,
    AssetTimelineEvent,
)
from backend.app.domains.locations.models import LocationModel
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import (
    EntityNotFoundError,
    ConflictError,
    DomainValidationError,
)


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime object is timezone-aware and normalized to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AssetService:
    """
    Central domain service for physical expedition asset lifecycle, relocation,
    preventative/corrective maintenance orders, collision prevention, events, and audit logs.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = AssetRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    # ============================================================
    # 1. ASSET CRUD & LIFECYCLE
    # ============================================================

    def create_asset(
        self,
        data: AssetCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> AssetModel:
        """Registers a new polar expedition asset."""
        cid = correlation_id or uuid.uuid4()

        # Check unique asset_code
        if self.repo.get_by_code(data.asset_code):
            raise ConflictError(f"Asset with code '{data.asset_code}' already exists.")

        # Check unique serial_number if provided
        if data.serial_number and self.repo.get_by_serial(data.serial_number):
            raise ConflictError(f"Asset with serial number '{data.serial_number}' already exists.")

        # Validate location if specified
        if data.location_id:
            loc = self.session.execute(select(LocationModel).where(LocationModel.id == data.location_id)).scalar_one_or_none()
            if not loc:
                raise EntityNotFoundError("Location", data.location_id)

        asset = AssetModel(
            id=uuid.uuid4(),
            asset_code=data.asset_code,
            serial_number=data.serial_number,
            name=data.name,
            type=data.type,
            model=data.model,
            description=data.description,
            condition=data.condition.value,
            criticality=data.criticality.value,
            location_id=data.location_id,
            status=data.status.value,
            operational_metadata=data.operational_metadata,
            commissioned_at=ensure_utc(data.commissioned_at) if data.commissioned_at else None,
            data_provenance=data.data_provenance.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = self.repo.create(asset)

        self.audit_service.record_audit(
            action="CREATE_ASSET",
            entity_type="ASSET",
            entity_id=created.id,
            after_snapshot={
                "asset_code": created.asset_code,
                "name": created.name,
                "type": created.type,
                "status": created.status,
                "location_id": str(created.location_id) if created.location_id else None
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="AssetCreated",
            entity_type="ASSET",
            entity_id=created.id,
            new_state=created.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=created.location_id,
            correlation_id=cid,
            evidence={
                "asset_code": created.asset_code,
                "type": created.type,
                "serial_number": created.serial_number
            },
        )

        self.session.commit()
        return created

    def get_asset(self, asset_id: uuid.UUID) -> AssetModel:
        """Retrieves asset by UUID or raises EntityNotFoundError."""
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            raise EntityNotFoundError("Asset", asset_id)
        return asset

    def list_assets(
        self,
        type_: Optional[str] = None,
        status: Optional[str] = None,
        location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[AssetModel], int]:
        """Lists assets with optional filtering and pagination."""
        return self.repo.list_assets(
            type_=type_,
            status=status,
            location_id=location_id,
            page=page,
            page_size=page_size
        )

    def update_asset(
        self,
        asset_id: uuid.UUID,
        data: AssetUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> AssetModel:
        """Updates asset metadata. Retired assets cannot be modified."""
        cid = correlation_id or uuid.uuid4()
        asset = self.get_asset(asset_id)

        if asset.status == AssetStatus.RETIRED.value:
            raise DomainValidationError("Cannot update retired asset. RETIRED is a terminal lifecycle state.")

        before_snapshot = {
            "name": asset.name,
            "condition": asset.condition,
            "criticality": asset.criticality
        }

        if data.name is not None:
            asset.name = data.name
        if data.type is not None:
            asset.type = data.type
        if data.model is not None:
            asset.model = data.model
        if data.description is not None:
            asset.description = data.description
        if data.condition is not None:
            asset.condition = data.condition.value
        if data.criticality is not None:
            asset.criticality = data.criticality.value
        if data.operational_metadata is not None:
            asset.operational_metadata = {**asset.operational_metadata, **data.operational_metadata}

        asset.updated_at = datetime.now(timezone.utc)
        self.repo.update(asset)

        self.audit_service.record_audit(
            action="UPDATE_ASSET",
            entity_type="ASSET",
            entity_id=asset.id,
            before_snapshot=before_snapshot,
            after_snapshot={
                "name": asset.name,
                "condition": asset.condition,
                "criticality": asset.criticality
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.session.commit()
        return asset

    def transition_asset_status(
        self,
        asset_id: uuid.UUID,
        req: AssetStatusTransitionRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> AssetModel:
        """Validates and applies lifecycle status transition for asset."""
        cid = correlation_id or uuid.uuid4()
        asset = self.get_asset(asset_id)
        prev_status = asset.status

        if prev_status == AssetStatus.RETIRED.value:
            raise DomainValidationError("Cannot transition retired asset. RETIRED is a terminal lifecycle state.")

        validate_asset_transition(current_state_str=prev_status, target_state_str=req.target_status.value)

        asset.status = req.target_status.value
        if req.target_status == AssetStatus.RETIRED:
            asset.retired_at = datetime.now(timezone.utc)
        asset.updated_at = datetime.now(timezone.utc)
        self.repo.update(asset)

        self.audit_service.record_audit(
            action="TRANSITION_ASSET_STATUS",
            entity_type="ASSET",
            entity_id=asset.id,
            before_snapshot={"status": prev_status},
            after_snapshot={"status": asset.status, "reason": req.reason},
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="AssetStatusChanged",
            entity_type="ASSET",
            entity_id=asset.id,
            previous_state=prev_status,
            new_state=asset.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={"reason": req.reason},
        )

        self.session.commit()
        return asset

    def move_asset(
        self,
        asset_id: uuid.UUID,
        req: AssetMoveRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> AssetModel:
        """Relocates asset to destination operational location. Retired assets cannot be moved."""
        cid = correlation_id or uuid.uuid4()
        asset = self.get_asset(asset_id)

        if asset.status == AssetStatus.RETIRED.value:
            raise DomainValidationError("Cannot move retired asset.")

        # Verify destination location exists
        dest_loc = self.session.execute(
            select(LocationModel).where(LocationModel.id == req.destination_location_id)
        ).scalar_one_or_none()
        if not dest_loc:
            raise EntityNotFoundError("Location", req.destination_location_id)

        prev_loc_id = asset.location_id
        asset.location_id = req.destination_location_id
        asset.updated_at = datetime.now(timezone.utc)
        self.repo.update(asset)

        self.audit_service.record_audit(
            action="MOVE_ASSET",
            entity_type="ASSET",
            entity_id=asset.id,
            before_snapshot={"location_id": str(prev_loc_id) if prev_loc_id else None},
            after_snapshot={
                "location_id": str(asset.location_id),
                "destination_name": dest_loc.name,
                "reason": req.reason
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="AssetMoved",
            entity_type="ASSET",
            entity_id=asset.id,
            previous_state=str(prev_loc_id) if prev_loc_id else None,
            new_state=str(asset.location_id),
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={
                "from_location_id": str(prev_loc_id) if prev_loc_id else None,
                "to_location_id": str(asset.location_id),
                "reason": req.reason
            },
        )

        self.session.commit()
        return asset

    def get_asset_timeline(self, asset_id: uuid.UUID) -> AssetTimelineRead:
        """Builds operational asset timeline including active/past maintenance and events."""
        asset = self.get_asset(asset_id)

        # Get maintenance records
        maintenance_records, total_maint = self.repo.list_maintenance_by_asset(asset_id, page=1, page_size=100)
        active_rec = next(
            (m for m in maintenance_records if m.status in [MaintenanceStatus.SCHEDULED.value, MaintenanceStatus.IN_PROGRESS.value]),
            None
        )

        # Get operational events for this asset
        events, _ = self.event_service.get_entity_history(entity_type="ASSET", entity_id=asset.id, page_size=100)

        timeline_events = []
        for e in events:
            timeline_events.append(AssetTimelineEvent(
                timestamp=ensure_utc(e.occurred_at),
                event_type=e.event_type,
                summary=f"Asset {e.event_type} (Status: {e.new_state})",
                correlation_id=str(e.correlation_id) if e.correlation_id else None,
                details=e.evidence or {}
            ))

        # Add maintenance events to timeline
        for m in maintenance_records:
            if m.completed_at:
                timeline_events.append(AssetTimelineEvent(
                    timestamp=ensure_utc(m.completed_at),
                    event_type="MaintenanceCompleted",
                    summary=f"Maintenance {m.maintenance_type} completed",
                    details={"findings": m.findings, "corrective_action": m.corrective_action}
                ))
            elif m.started_at:
                timeline_events.append(AssetTimelineEvent(
                    timestamp=ensure_utc(m.started_at),
                    event_type="MaintenanceStarted",
                    summary=f"Maintenance {m.maintenance_type} started",
                    details={"performed_by": m.performed_by}
                ))
            elif m.scheduled_at:
                timeline_events.append(AssetTimelineEvent(
                    timestamp=ensure_utc(m.scheduled_at),
                    event_type="MaintenanceScheduled",
                    summary=f"Maintenance {m.maintenance_type} scheduled",
                    details={"priority": m.priority}
                ))

        timeline_events.sort(key=lambda x: x.timestamp, reverse=True)

        return AssetTimelineRead(
            asset_id=asset.id,
            asset_code=asset.asset_code,
            name=asset.name,
            status=AssetStatus(asset.status),
            current_location_id=asset.location_id,
            active_maintenance=MaintenanceRecordRead.model_validate(active_rec) if active_rec else None,
            maintenance_history_count=total_maint,
            timeline=timeline_events
        )

    # ============================================================
    # 2. MAINTENANCE OPERATIONS
    # ============================================================

    def schedule_maintenance(
        self,
        asset_id: uuid.UUID,
        req: MaintenanceScheduleRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> MaintenanceRecordModel:
        """
        Schedules preventative or corrective maintenance for an asset.
        Prevents overlapping active maintenance and rejects retired assets.
        """
        cid = correlation_id or uuid.uuid4()
        asset = self.get_asset(asset_id)

        # Retired asset check
        if asset.status == AssetStatus.RETIRED.value:
            raise DomainValidationError("Cannot schedule maintenance for retired asset.")

        # Overlapping active maintenance check
        active = self.repo.get_active_maintenance_for_asset(asset_id, for_update=True)
        if active:
            raise ConflictError(
                f"Asset '{asset.asset_code}' already has an active maintenance order (ID: {active.id}, Status: {active.status})."
            )

        sched_time = ensure_utc(req.scheduled_at) if req.scheduled_at else datetime.now(timezone.utc)
        record = MaintenanceRecordModel(
            id=uuid.uuid4(),
            asset_id=asset.id,
            maintenance_type=req.maintenance_type,
            priority=req.priority,
            status=MaintenanceStatus.SCHEDULED.value,
            scheduled_at=sched_time,
            description=req.description,
            performed_by=req.performed_by,
            technician_reference=req.technician_reference,
            notes=req.notes,
            operational_metadata=req.operational_metadata,
            data_provenance=asset.data_provenance,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = self.repo.create_maintenance(record)

        self.audit_service.record_audit(
            action="SCHEDULE_MAINTENANCE",
            entity_type="MAINTENANCE_RECORD",
            entity_id=created.id,
            after_snapshot={
                "asset_id": str(created.asset_id),
                "maintenance_type": created.maintenance_type,
                "priority": created.priority,
                "scheduled_at": created.scheduled_at.isoformat() if created.scheduled_at else None
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="MaintenanceScheduled",
            entity_type="MAINTENANCE_RECORD",
            entity_id=created.id,
            new_state=created.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={
                "asset_id": str(asset.id),
                "asset_code": asset.asset_code,
                "maintenance_type": created.maintenance_type,
                "priority": created.priority
            },
        )

        self.session.commit()
        return created

    def start_maintenance(
        self,
        record_id: uuid.UUID,
        req: MaintenanceStartRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> MaintenanceRecordModel:
        """Starts scheduled or overdue maintenance, transitioning status to IN_PROGRESS."""
        cid = correlation_id or uuid.uuid4()
        record = self.get_maintenance(record_id)
        asset = self.get_asset(record.asset_id)

        if asset.status == AssetStatus.RETIRED.value:
            raise DomainValidationError("Cannot perform maintenance on retired asset.")

        prev_status = record.status
        validate_maintenance_transition(current_state_str=prev_status, target_state_str=MaintenanceStatus.IN_PROGRESS.value)

        record.status = MaintenanceStatus.IN_PROGRESS.value
        record.started_at = ensure_utc(req.started_at) if req.started_at else datetime.now(timezone.utc)
        if req.technician_reference:
            record.technician_reference = req.technician_reference
        if req.notes:
            record.notes = f"{record.notes or ''}\n{req.notes}".strip()
        record.updated_at = datetime.now(timezone.utc)
        self.repo.update_maintenance(record)

        # Optional explicit transition of asset to MAINTENANCE
        if req.transition_asset_to_maintenance and asset.status != AssetStatus.MAINTENANCE.value:
            validate_asset_transition(asset.status, AssetStatus.MAINTENANCE.value)
            asset_prev = asset.status
            asset.status = AssetStatus.MAINTENANCE.value
            asset.updated_at = datetime.now(timezone.utc)
            self.repo.update(asset)

            self.audit_service.record_audit(
                action="TRANSITION_ASSET_STATUS",
                entity_type="ASSET",
                entity_id=asset.id,
                before_snapshot={"status": asset_prev},
                after_snapshot={"status": asset.status, "reason": "Maintenance work initiated"},
                correlation_id=cid,
                actor_person_id=actor_person_id,
            )

            self.event_service.append_event(
                event_type="AssetStatusChanged",
                entity_type="ASSET",
                entity_id=asset.id,
                previous_state=asset_prev,
                new_state=asset.status,
                actor_type="USER" if actor_person_id else "SYSTEM",
                actor_id=actor_person_id,
                location_id=asset.location_id,
                correlation_id=cid,
                evidence={"trigger": "MaintenanceStarted", "maintenance_id": str(record.id)},
            )

        self.audit_service.record_audit(
            action="START_MAINTENANCE",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            before_snapshot={"status": prev_status},
            after_snapshot={"status": record.status, "started_at": record.started_at.isoformat() if record.started_at else None},
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="MaintenanceStarted",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            previous_state=prev_status,
            new_state=record.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={"asset_id": str(asset.id), "started_at": record.started_at.isoformat() if record.started_at else None},
        )

        self.session.commit()
        return record

    def complete_maintenance(
        self,
        record_id: uuid.UUID,
        req: MaintenanceCompleteRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> MaintenanceRecordModel:
        """
        Completes maintenance order, recording findings and corrective action.
        Does NOT silently modify asset status unless target_asset_status is explicitly specified.
        """
        cid = correlation_id or uuid.uuid4()
        record = self.get_maintenance(record_id)
        asset = self.get_asset(record.asset_id)
        prev_status = record.status

        validate_maintenance_transition(current_state_str=prev_status, target_state_str=MaintenanceStatus.COMPLETED.value)

        record.status = MaintenanceStatus.COMPLETED.value
        record.completed_at = ensure_utc(req.completed_at) if req.completed_at else datetime.now(timezone.utc)
        if req.findings is not None:
            record.findings = req.findings
        if req.corrective_action is not None:
            record.corrective_action = req.corrective_action
        if req.notes is not None:
            record.notes = f"{record.notes or ''}\n{req.notes}".strip()
        record.updated_at = datetime.now(timezone.utc)
        self.repo.update_maintenance(record)

        # Rule: Explicit target_asset_status handling without silent mutation
        if req.target_asset_status:
            validate_asset_transition(asset.status, req.target_asset_status.value)
            asset_prev = asset.status
            asset.status = req.target_asset_status.value
            asset.updated_at = datetime.now(timezone.utc)
            self.repo.update(asset)

            self.audit_service.record_audit(
                action="TRANSITION_ASSET_STATUS",
                entity_type="ASSET",
                entity_id=asset.id,
                before_snapshot={"status": asset_prev},
                after_snapshot={"status": asset.status, "reason": "Maintenance work completed"},
                correlation_id=cid,
                actor_person_id=actor_person_id,
            )

            self.event_service.append_event(
                event_type="AssetStatusChanged",
                entity_type="ASSET",
                entity_id=asset.id,
                previous_state=asset_prev,
                new_state=asset.status,
                actor_type="USER" if actor_person_id else "SYSTEM",
                actor_id=actor_person_id,
                location_id=asset.location_id,
                correlation_id=cid,
                evidence={"trigger": "MaintenanceCompleted", "maintenance_id": str(record.id)},
            )

        self.audit_service.record_audit(
            action="COMPLETE_MAINTENANCE",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            before_snapshot={"status": prev_status},
            after_snapshot={
                "status": record.status,
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                "findings": record.findings,
                "corrective_action": record.corrective_action
            },
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="MaintenanceCompleted",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            previous_state=prev_status,
            new_state=record.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={
                "asset_id": str(asset.id),
                "completed_at": record.completed_at.isoformat() if record.completed_at else None
            },
        )

        self.session.commit()
        return record

    def cancel_maintenance(
        self,
        record_id: uuid.UUID,
        req: MaintenanceCancelRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None
    ) -> MaintenanceRecordModel:
        """Cancels a scheduled or in-progress maintenance order."""
        cid = correlation_id or uuid.uuid4()
        record = self.get_maintenance(record_id)
        asset = self.get_asset(record.asset_id)
        prev_status = record.status

        validate_maintenance_transition(current_state_str=prev_status, target_state_str=MaintenanceStatus.CANCELLED.value)

        record.status = MaintenanceStatus.CANCELLED.value
        record.notes = f"{record.notes or ''} [CANCELLED]: {req.reason}".strip()
        record.updated_at = datetime.now(timezone.utc)
        self.repo.update_maintenance(record)

        self.audit_service.record_audit(
            action="CANCEL_MAINTENANCE",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            before_snapshot={"status": prev_status},
            after_snapshot={"status": record.status, "reason": req.reason},
            correlation_id=cid,
            actor_person_id=actor_person_id,
        )

        self.event_service.append_event(
            event_type="MaintenanceCancelled",
            entity_type="MAINTENANCE_RECORD",
            entity_id=record.id,
            previous_state=prev_status,
            new_state=record.status,
            actor_type="USER" if actor_person_id else "SYSTEM",
            actor_id=actor_person_id,
            location_id=asset.location_id,
            correlation_id=cid,
            evidence={"reason": req.reason, "asset_id": str(asset.id)},
        )

        self.session.commit()
        return record

    def get_maintenance(self, record_id: uuid.UUID) -> MaintenanceRecordModel:
        """Retrieves maintenance record by UUID or raises EntityNotFoundError."""
        record = self.repo.get_maintenance_by_id(record_id)
        if not record:
            raise EntityNotFoundError("MaintenanceRecord", record_id)
        return record

    def list_maintenance_for_asset(
        self,
        asset_id: uuid.UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[MaintenanceRecordModel], int]:
        """Lists maintenance history for an asset."""
        self.get_asset(asset_id)  # Validate asset exists
        return self.repo.list_maintenance_by_asset(asset_id=asset_id, status=status, page=page, page_size=page_size)
