"""Personnel Persistence Repository."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.app.domains.people.models import PersonModel


class PersonRepository:
    """Repository handling SQL persistence for expedition personnel."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, model: PersonModel) -> PersonModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, person_id: uuid.UUID) -> Optional[PersonModel]:
        stmt = select(PersonModel).where(PersonModel.id == person_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, person_code: str) -> Optional[PersonModel]:
        stmt = select(PersonModel).where(PersonModel.person_code == person_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_people(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        readiness_state: Optional[str] = None,
        movement_state: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[PersonModel], int]:
        conditions = []
        if expedition_id:
            conditions.append(PersonModel.expedition_id == expedition_id)
        if team_id:
            conditions.append(PersonModel.team_id == team_id)
        if readiness_state:
            conditions.append(PersonModel.readiness_state == readiness_state.upper())
        if movement_state:
            conditions.append(PersonModel.movement_state == movement_state.upper())

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(PersonModel.id)).where(where_clause)
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(PersonModel)
            .where(where_clause)
            .order_by(PersonModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total

    def update(self, model: PersonModel) -> PersonModel:
        self.session.flush()
        return model
