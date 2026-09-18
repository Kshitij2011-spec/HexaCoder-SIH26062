"""Offline Queue / Sync Domain Service — Track B Milestone B5."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.domains.sync.models import OfflineOperationModel
from backend.app.domains.sync.repository import SyncRepository
from backend.app.domains.sync.states import (
    OfflineOperationStatus,
    TERMINAL_STATUSES,
    OFFLINE_OP_TRANSITIONS,
    ALLOWED_ENTITY_TYPES,
    OfflineOperationType,
)
from backend.app.domains.sync.schemas import (
    OfflineOperationEnqueue,
    SyncBatchRequest,
    SyncBatchResult,
    OperationApplyRequest,
    SyncQueueSummary,
)
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import (
    EntityNotFoundError,
    InvalidStateTransitionError,
    DomainValidationError,
)


class SyncService:
    """
    Authoritative domain service for the offline operation queue.

    Responsibilities:
    - Idempotent enqueue (client-supplied operation_id)
    - Batch enqueue with per-operation outcome reporting
    - Status transitions (PENDING → APPLIED / FAILED / REJECTED)
    - Queue introspection and summary
    - Operational event journaling via EventService
    - Attributable audit logging via AuditService
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = SyncRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    # ============================================================
    # 1. ENQUEUE — single, idempotent
    # ============================================================

    def enqueue(
        self,
        data: OfflineOperationEnqueue,
        correlation_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Tuple[OfflineOperationModel, bool]:
        """
        Enqueue a single offline operation.

        Returns (model, created) — created=False when operation_id already exists (idempotent).
        """
        existing = self.repo.get_by_operation_id(data.operation_id)
        if existing:
            return existing, False  # idempotent — already queued

        entity_type = data.entity_type.upper().strip()
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise DomainValidationError(
                "OfflineOperation", "entity_type", f"Invalid entity_type '{data.entity_type}'. Allowed types: {sorted(ALLOWED_ENTITY_TYPES)}"
            )
        op_type = data.operation_type.upper().strip()
        if op_type not in {t.value for t in OfflineOperationType}:
            raise DomainValidationError(
                "OfflineOperation", "operation_type", f"Invalid operation_type '{data.operation_type}'. Allowed types: {sorted({t.value for t in OfflineOperationType})}"
            )

        queued_at = data.queued_at or datetime.now(timezone.utc)
        op = OfflineOperationModel(
            id=uuid.uuid4(),
            operation_id=data.operation_id,
            entity_type=data.entity_type.upper(),
            operation_type=data.operation_type.upper(),
            entity_type=entity_type,
            operation_type=op_type,
            payload=data.payload,
            status=OfflineOperationStatus.PENDING,
            queued_at=queued_at,
            actor_id=data.actor_id or actor_id,
            correlation_id=correlation_id or uuid.uuid4(),
            data_provenance="SYNTHETIC_DEMO",
        )
        self.repo.create(op)

        self.event_service.append_event(
            event_type="OFFLINE_OP_QUEUED",
            entity_type="OFFLINE_OPERATION",
            entity_id=op.id,
            new_state=OfflineOperationStatus.PENDING,
            source="SYNC_API",
            actor_id=op.actor_id,
            correlation_id=op.correlation_id,
            evidence={
                "operation_id": str(op.operation_id),
                "entity_type": op.entity_type,
                "operation_type": op.operation_type,
            },
        )
        self.audit_service.record_audit(
            action="OFFLINE_OP_ENQUEUED",
            entity_type="OFFLINE_OPERATION",
            entity_id=op.id,
            after_snapshot={"status": OfflineOperationStatus.PENDING, "operation_id": str(op.operation_id)},
            correlation_id=op.correlation_id,
            actor_person_id=op.actor_id,
        )

        self.session.commit()
        self.session.refresh(op)
        return op, True

    # ============================================================
    # 2. BATCH ENQUEUE
    # ============================================================

    def enqueue_batch(
        self,
        batch: SyncBatchRequest,
        correlation_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SyncBatchResult:
        """
        Enqueue a batch of offline operations.
        Per-operation outcomes: ENQUEUED, DUPLICATE, or ERROR.
        Each operation is committed independently to prevent one failure poisoning the batch.
        """
        enqueued_count = 0
        duplicate_count = 0
        failed_count = 0
        results: List[Dict[str, Any]] = []

        for item in batch.operations:
            try:
                _, created = self.enqueue(item, correlation_id=correlation_id, actor_id=actor_id)
                if created:
                    enqueued_count += 1
                    results.append({"operation_id": str(item.operation_id), "outcome": "ENQUEUED"})
                else:
                    duplicate_count += 1
                    results.append({"operation_id": str(item.operation_id), "outcome": "DUPLICATE"})
            except Exception as exc:
                failed_count += 1
                results.append({
                    "operation_id": str(item.operation_id),
                    "outcome": "ERROR",
                    "message": str(exc),
                })

        return SyncBatchResult(
            enqueued=enqueued_count,
            skipped_duplicate=duplicate_count,
            failed=failed_count,
            results=results,
        )

    # ============================================================
    # 3. APPLY / REJECT / MARK FAILED
    # ============================================================

    def apply_operation(
        self,
        record_id: uuid.UUID,
        request: OperationApplyRequest,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> OfflineOperationModel:
        """
        Transition an offline operation to APPLIED, FAILED, or REJECTED.

        Validates the transition against the allowed state machine.
        APPLIED and REJECTED are terminal — no further transitions.
        """
        op = self.repo.get_by_id(record_id)
        if not op:
            raise EntityNotFoundError("OfflineOperation", str(record_id))

        target = request.status.upper()
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS.get(
            OfflineOperationStatus(op.status), []
        )]
        if target not in allowed:
            raise InvalidStateTransitionError(
                "OfflineOperation", op.status, target, allowed
            )

        previous_status = op.status
        op.status = target
        op.updated_at = datetime.now(timezone.utc)

        if target == OfflineOperationStatus.APPLIED:
            op.applied_at = datetime.now(timezone.utc)
        elif target in (OfflineOperationStatus.FAILED, OfflineOperationStatus.REJECTED):
            op.failure_reason = request.failure_reason
            if target == OfflineOperationStatus.FAILED:
                op.retry_count += 1

        self.event_service.append_event(
            event_type=f"OFFLINE_OP_{target}",
            entity_type="OFFLINE_OPERATION",
            entity_id=op.id,
            previous_state=previous_status,
            new_state=target,
            source="SYNC_API",
            actor_id=actor_id,
            correlation_id=correlation_id or op.correlation_id,
            evidence={
                "operation_id": str(op.operation_id),
                "failure_reason": op.failure_reason,
            },
        )
        self.audit_service.record_audit(
            action=f"OFFLINE_OP_{target}",
            entity_type="OFFLINE_OPERATION",
            entity_id=op.id,
            before_snapshot={"status": previous_status},
            after_snapshot={"status": target},
            correlation_id=correlation_id or op.correlation_id,
            actor_person_id=actor_id,
        )

        self.repo.save(op)
        self.session.commit()
        self.session.refresh(op)
        return op

    # ============================================================
    # 4. QUEUE INTROSPECTION
    # ============================================================

    def get_operation(self, record_id: uuid.UUID) -> OfflineOperationModel:
        op = self.repo.get_by_id(record_id)
        if not op:
            raise EntityNotFoundError("OfflineOperation", str(record_id))
        return op

    def get_by_operation_id(self, operation_id: uuid.UUID) -> OfflineOperationModel:
        op = self.repo.get_by_operation_id(operation_id)
        if not op:
            raise EntityNotFoundError("OfflineOperation", str(operation_id))
        return op

    def list_operations(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OfflineOperationModel], int]:
        return self.repo.list_all(
            status=status,
            entity_type=entity_type,
            page=page,
            page_size=page_size,
        )

    def get_queue_summary(self) -> SyncQueueSummary:
        """Returns a high-level count of operations by status."""
        counts = self.repo.count_by_status()
        pending = counts.get("PENDING", 0)
        applied = counts.get("APPLIED", 0)
        failed = counts.get("FAILED", 0)
        rejected = counts.get("REJECTED", 0)
        return SyncQueueSummary(
            pending=pending,
            applied=applied,
            failed=failed,
            rejected=rejected,
            total=pending + applied + failed + rejected,
        )
