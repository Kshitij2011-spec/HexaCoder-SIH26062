"""Audit Service for Recording Application State Changes."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.platform.audit.models import AuditLogModel
from backend.app.platform.audit.repository import AuditRepository


class AuditService:
    """Service handling audit recording transactionally with domain operations."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = AuditRepository(session)

    def record_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        actor_person_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[datetime] = None
    ) -> AuditLogModel:
        """
        Records an audit log entry in the current transaction.
        Distinguishes application action provenance from domain operational events.
        """
        entry = AuditLogModel(
            action=action,
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            correlation_id=correlation_id,
            actor_user_id=actor_user_id,
            actor_person_id=actor_person_id,
            metadata_=metadata or {},
            occurred_at=occurred_at or datetime.now(timezone.utc)
        )
        return self.repository.record(entry)

    def get_entity_audit_trail(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[AuditLogModel], int]:
        """Retrieves audit entries for an entity."""
        return self.repository.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size
        )
