"""Pydantic Schemas for Application Audit Logs."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    """Audit log entry representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_person_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    correlation_id: Optional[uuid.UUID] = None
    occurred_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
