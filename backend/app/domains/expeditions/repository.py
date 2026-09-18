"""Expedition Persistence Repository."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.app.domains.expeditions.models import ExpeditionModel


class ExpeditionRepository:
    """Repository handling SQL persistence for expeditions."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, model: ExpeditionModel) -> ExpeditionModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, expedition_id: uuid.UUID) -> Optional[ExpeditionModel]:
        stmt = select(ExpeditionModel).where(ExpeditionModel.id == expedition_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[ExpeditionModel]:
        stmt = select(ExpeditionModel).where(ExpeditionModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_expeditions(
        self,
        status: Optional[str] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ExpeditionModel], int]:
        conditions = []
        if status:
            conditions.append(ExpeditionModel.status == status.upper())
        if season:
            conditions.append(ExpeditionModel.season == season)

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(ExpeditionModel.id)).where(where_clause)
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(ExpeditionModel)
            .where(where_clause)
            .order_by(ExpeditionModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total

    def update(self, model: ExpeditionModel) -> ExpeditionModel:
        self.session.flush()
        return model
