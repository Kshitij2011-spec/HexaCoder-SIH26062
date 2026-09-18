"""Repository for Operational Constraints."""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.services.constraints.models import ConstraintModel


class ConstraintRepository:
    """Data access repository for constraints table."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, constraint_id: uuid.UUID) -> Optional[ConstraintModel]:
        return self.session.execute(
            select(ConstraintModel).where(ConstraintModel.id == constraint_id)
        ).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[ConstraintModel]:
        return self.session.execute(
            select(ConstraintModel).where(ConstraintModel.code == code)
        ).scalar_one_or_none()

    def list_all(self, active_only: bool = True) -> List[ConstraintModel]:
        query = select(ConstraintModel)
        if active_only:
            query = query.where(ConstraintModel.active.is_(True))
        query = query.order_by(ConstraintModel.created_at.asc())
        return list(self.session.execute(query).scalars().all())

    def get_for_subject(
        self,
        subject_type: str,
        subject_id: uuid.UUID,
        active_only: bool = True
    ) -> List[ConstraintModel]:
        query = select(ConstraintModel).where(
            ConstraintModel.subject_type == subject_type.upper(),
            ConstraintModel.subject_id == subject_id
        )
        if active_only:
            query = query.where(ConstraintModel.active.is_(True))
        query = query.order_by(ConstraintModel.created_at.asc())
        return list(self.session.execute(query).scalars().all())

    def get_for_rule(self, rule_code: str, active_only: bool = True) -> List[ConstraintModel]:
        query = select(ConstraintModel).where(ConstraintModel.rule_code == rule_code)
        if active_only:
            query = query.where(ConstraintModel.active.is_(True))
        return list(self.session.execute(query).scalars().all())

    def create(self, model: ConstraintModel) -> ConstraintModel:
        self.session.add(model)
        self.session.flush()
        return model
