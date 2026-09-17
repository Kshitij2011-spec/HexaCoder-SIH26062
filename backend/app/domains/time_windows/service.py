"""Time Windows Application Service (Temporal Invariant Enforcement, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.time_windows.models import TimeWindowModel
from backend.app.domains.time_windows.repository import TimeWindowRepository
from backend.app.domains.time_windows.schemas import TimeWindowCreate, TimeWindowUpdate
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, DomainValidationError


class TimeWindowService:
    """Domain service managing operational time windows and enforcing temporal bounds."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = TimeWindowRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_time_window(
        self,
        data: TimeWindowCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TimeWindowModel:
        """Creates a temporal window constraint and emits a TimeWindowCreated event."""
        # Strict temporal validation
        if data.close_at <= data.open_at:
            raise DomainValidationError(
                f"close_at ({data.close_at.isoformat()}) must be strictly after open_at ({data.open_at.isoformat()})",
                field="close_at"
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = TimeWindowModel(
            type=data.type,
            open_at=data.open_at,
            close_at=data.close_at,
            hard_or_soft=data.hard_or_soft.value,
            subject_type=data.subject_type.upper(),
            subject_id=data.subject_id,
            status=data.status,
            description=data.description,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            # Transactional event emission
            self.event_service.append_event(
                event_type="TimeWindowCreated",
                entity_type="TIME_WINDOW",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={
                    "type": created.type,
                    "subject_type": created.subject_type,
                    "subject_id": str(created.subject_id),
                    "open_at": created.open_at.isoformat(),
                    "close_at": created.close_at.isoformat(),
                    "hard_or_soft": created.hard_or_soft,
                },
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            # Transactional audit record
            self.audit_service.record_audit(
                action="CREATE_TIME_WINDOW",
                entity_type="TIME_WINDOW",
                entity_id=created.id,
                after_snapshot={
                    "type": created.type,
                    "subject_type": created.subject_type,
                    "subject_id": str(created.subject_id),
                    "open_at": created.open_at.isoformat(),
                    "close_at": created.close_at.isoformat(),
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_time_window(self, window_id: uuid.UUID) -> TimeWindowModel:
        window = self.repository.get_by_id(window_id)
        if not window:
            raise EntityNotFoundError("TimeWindow", window_id)
        return window

    def list_time_windows(
        self,
        subject_type: Optional[str] = None,
        subject_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TimeWindowModel], int]:
        return self.repository.list_windows(
            subject_type=subject_type,
            subject_id=subject_id,
            status=status,
            page=page,
            page_size=page_size
        )

    def update_time_window(
        self,
        window_id: uuid.UUID,
        data: TimeWindowUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TimeWindowModel:
        """Updates window bounds or status while enforcing open/close validity."""
        window = self.get_time_window(window_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        new_open = data.open_at if data.open_at is not None else window.open_at
        new_close = data.close_at if data.close_at is not None else window.close_at

        if new_close <= new_open:
            raise DomainValidationError(
                f"close_at ({new_close.isoformat()}) must be strictly after open_at ({new_open.isoformat()})",
                field="close_at"
            )

        before_snapshot = {
            "type": window.type,
            "open_at": window.open_at.isoformat(),
            "close_at": window.close_at.isoformat(),
            "status": window.status,
        }

        if data.type is not None:
            window.type = data.type
        if data.open_at is not None:
            window.open_at = data.open_at
        if data.close_at is not None:
            window.close_at = data.close_at
        if data.hard_or_soft is not None:
            window.hard_or_soft = data.hard_or_soft.value
        if data.status is not None:
            window.status = data.status
        if data.description is not None:
            window.description = data.description

        window.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(window)

            self.event_service.append_event(
                event_type="TimeWindowUpdated",
                entity_type="TIME_WINDOW",
                entity_id=updated.id,
                new_state=updated.status,
                previous_state=before_snapshot["status"],
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
                correlation_id=cid
            )

            self.audit_service.record_audit(
                action="UPDATE_TIME_WINDOW",
                entity_type="TIME_WINDOW",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "type": updated.type,
                    "open_at": updated.open_at.isoformat(),
                    "close_at": updated.close_at.isoformat(),
                    "status": updated.status,
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated
