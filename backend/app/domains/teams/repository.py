"""Teams Persistence Repository."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.people.models import PersonModel


class TeamRepository:
    """Repository handling SQL persistence and queries for expedition teams."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, model: TeamModel) -> TeamModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, team_id: uuid.UUID) -> Optional[TeamModel]:
        stmt = select(TeamModel).where(TeamModel.id == team_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[TeamModel]:
        stmt = select(TeamModel).where(TeamModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_teams(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TeamModel], int]:
        conditions = []
        if expedition_id:
            conditions.append(TeamModel.expedition_id == expedition_id)
        if status:
            conditions.append(TeamModel.status == status.upper())

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(TeamModel.id)).where(where_clause)
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(TeamModel)
            .where(where_clause)
            .order_by(TeamModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total

    def update(self, model: TeamModel) -> TeamModel:
        self.session.flush()
        return model

    def get_members(self, team_id: uuid.UUID) -> List[PersonModel]:
        """Returns all personnel assigned to this team via people.team_id."""
        stmt = select(PersonModel).where(PersonModel.team_id == team_id).order_by(PersonModel.full_name)
        return list(self.session.execute(stmt).scalars().all())
