"""Pydantic schemas for Offline Queue / Sync domain (B5)."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class OfflineOperationEnqueue(BaseModel):
    """Request body for queuing an offline operation."""
    operation_id: uuid.UUID = Field(
        description="Client-supplied idempotency key. Resubmitting with the same key is safe."
    )
    entity_type: str = Field(
        max_length=100,
        description="Domain entity type e.g. INVENTORY_ITEM, ASSET, INCIDENT.",
    )
    operation_type: str = Field(
        max_length=100,
        description="Operation kind: CREATE, UPDATE, STATE_TRANSITION, DELETE.",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Serialised operation payload. Provenance: SYNTHETIC_DEMO.",
    )
    queued_at: Optional[datetime] = Field(
        default=None,
        description="Client-side timestamp of when the operation was queued offline. "
                    "Defaults to server time when omitted.",
    )
    actor_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the person/user who queued this operation.",
    )


class OfflineOperationRead(BaseModel):
    """Read schema for a single queued operation."""
    id: uuid.UUID
    operation_id: uuid.UUID
    entity_type: str
    operation_type: str
    payload: Dict[str, Any]
    status: str
    queued_at: datetime
    applied_at: Optional[datetime]
    failure_reason: Optional[str]
    retry_count: int
    actor_id: Optional[uuid.UUID]
    correlation_id: Optional[uuid.UUID]
    data_provenance: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncBatchRequest(BaseModel):
    """Batch sync request — enqueue multiple operations at once."""
    operations: List[OfflineOperationEnqueue] = Field(
        min_length=1,
        max_length=100,
        description="List of operations to enqueue. 1–100 items.",
    )


class SyncBatchResult(BaseModel):
    """Result of a batch enqueue — per-operation outcomes."""
    enqueued: int = Field(description="Number of new operations successfully enqueued.")
    skipped_duplicate: int = Field(description="Number of operations skipped (already present idempotent key).")
    failed: int = Field(description="Number of operations that could not be stored.")
    results: List[Dict[str, Any]] = Field(
        description="Per-operation result: operation_id, outcome (ENQUEUED|DUPLICATE|ERROR), and optional message."
    )


class OperationApplyRequest(BaseModel):
    """Request to mark a PENDING operation as APPLIED or FAILED."""
    status: str = Field(description="Target status: APPLIED or FAILED or REJECTED.")
    failure_reason: Optional[str] = Field(
        default=None,
        description="Human-readable failure reason. Required when status is FAILED or REJECTED.",
    )

    @model_validator(mode="after")
    def _validate_failure_reason(self) -> "OperationApplyRequest":
        if self.status in ("FAILED", "REJECTED") and not self.failure_reason:
            raise ValueError("failure_reason is required when status is FAILED or REJECTED.")
        return self


class SyncQueueSummary(BaseModel):
    """High-level summary of the offline sync queue state."""
    pending: int
    applied: int
    failed: int
    rejected: int
    total: int
    data_provenance: str = "SYNTHETIC_DEMO"
