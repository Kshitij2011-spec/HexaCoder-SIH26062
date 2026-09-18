"""Data access repository for offline_operations queue."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.domains.sync.models import OfflineOperationModel


class SyncRepository:
    """Thin data-access layer for offline_operations. No business logic here."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, record_id: uuid.UUID) -> Optional[OfflineOperationModel]:
        stmt = select(OfflineOperationModel).where(OfflineOperationModel.id == record_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_operation_id(self, operation_id: uuid.UUID) -> Optional[OfflineOperationModel]:
        """Idempotency lookup — returns existing record if operation_id already present."""
        stmt = select(OfflineOperationModel).where(
            OfflineOperationModel.operation_id == operation_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, op: OfflineOperationModel) -> OfflineOperationModel:
        self.session.add(op)
        self.session.flush()
        return op

    def list_pending(
        self,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OfflineOperationModel], int]:
        """Lists PENDING operations, optionally filtered by entity_type."""
        base = select(OfflineOperationModel).where(
            OfflineOperationModel.status == "PENDING"
        )
        if entity_type:
            base = base.where(OfflineOperationModel.entity_type == entity_type.upper())
        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = self.session.execute(count_stmt).scalar_one()
        items = (
            self.session.execute(
                base.order_by(OfflineOperationModel.queued_at.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(items), total

    def list_all(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OfflineOperationModel], int]:
        """Lists operations with optional filters."""
        base = select(OfflineOperationModel)
        if status:
            base = base.where(OfflineOperationModel.status == status.upper())
        if entity_type:
            base = base.where(OfflineOperationModel.entity_type == entity_type.upper())
        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = self.session.execute(count_stmt).scalar_one()
        items = (
            self.session.execute(
                base.order_by(OfflineOperationModel.queued_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(items), total

    def count_by_status(self) -> dict:
        """Returns counts grouped by status for the queue summary."""
        rows = self.session.execute(
            select(
                OfflineOperationModel.status,
                func.count().label("cnt"),
            ).group_by(OfflineOperationModel.status)
        ).all()
        counts = {r.status: r.cnt for r in rows}
        return counts

    def save(self, op: OfflineOperationModel) -> OfflineOperationModel:
        self.session.flush()
        return op
