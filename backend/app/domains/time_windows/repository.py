"""Time Windows Persistence Repository."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.app.domains.time_windows.models import TimeWindowModel


class TimeWindowRepository:
    """Repository handling SQL persistence for temporal constraint windows."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, model: TimeWindowModel) -> TimeWindowModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, window_id: uuid.UUID) -> Optional[TimeWindowModel]:
        stmt = select(TimeWindowModel).where(TimeWindowModel.id == window_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_windows(
        self,
        subject_type: Optional[str] = None,
        subject_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TimeWindowModel], int]:
        conditions = []
        if subject_type:
            conditions.append(TimeWindowModel.subject_type == subject_type.upper())
        if subject_id:
            conditions.append(TimeWindowModel.subject_id == subject_id)
        if status:
            conditions.append(TimeWindowModel.status == status.upper())

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(TimeWindowModel.id)).where(where_clause)
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(TimeWindowModel)
            .where(where_clause)
            .order_by(TimeWindowModel.open_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total

    def update(self, model: TimeWindowModel) -> TimeWindowModel:
        self.session.flush()
        return model
