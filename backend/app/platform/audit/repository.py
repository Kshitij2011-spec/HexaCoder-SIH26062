"""Audit Log Repository."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.app.platform.audit.models import AuditLogModel


class AuditRepository:
    """Repository handling persistence and retrieval of audit log entries."""
    def __init__(self, session: Session):
        self.session = session

    def record(self, audit_entry: AuditLogModel) -> AuditLogModel:
        """Persists an audit log record within the current session."""
        self.session.add(audit_entry)
        self.session.flush()
        return audit_entry

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[AuditLogModel], int]:
        """Lists audit entries for an entity."""
        stmt = (
            select(AuditLogModel)
            .where(
                AuditLogModel.entity_type == entity_type.upper(),
                AuditLogModel.entity_id == entity_id
            )
            .order_by(AuditLogModel.occurred_at.desc())
        )
        count_stmt = select(func.count(AuditLogModel.id)).where(
            AuditLogModel.entity_type == entity_type.upper(),
            AuditLogModel.entity_id == entity_id
        )
        total = self.session.execute(count_stmt).scalar() or 0
        offset = (page - 1) * page_size
        results = self.session.execute(stmt.offset(offset).limit(page_size)).scalars().all()
        return list(results), total
