"""Mission Persistence Repository."""

import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, text
from backend.app.domains.missions.models import MissionModel


class MissionRepository:
    """Repository handling SQL persistence for missions and their relationship graphs."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, model: MissionModel) -> MissionModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, mission_id: uuid.UUID) -> Optional[MissionModel]:
        stmt = select(MissionModel).where(MissionModel.id == mission_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, expedition_id: uuid.UUID, code: str) -> Optional[MissionModel]:
        stmt = select(MissionModel).where(
            MissionModel.expedition_id == expedition_id,
            MissionModel.code == code
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_missions(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[MissionModel], int]:
        conditions = []
        if expedition_id:
            conditions.append(MissionModel.expedition_id == expedition_id)
        if status:
            conditions.append(MissionModel.status == status.upper())
        if priority is not None:
            conditions.append(MissionModel.priority == priority)

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(MissionModel.id)).where(where_clause)
        total = self.session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(MissionModel)
            .where(where_clause)
            .order_by(MissionModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        results = self.session.execute(query).scalars().all()
        return list(results), total

    def update(self, model: MissionModel) -> MissionModel:
        self.session.flush()
        return model

    def get_relationships(self, mission_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves semantic dependency relationships involving this mission."""
        sql = text("""
            SELECT id, relationship_type, source_entity_type, source_entity_id,
                   target_entity_type, target_entity_id, criticality, metadata, data_provenance
            FROM dependencies
            WHERE (source_entity_type = 'MISSION' AND source_entity_id = :mid)
               OR (target_entity_type = 'MISSION' AND target_entity_id = :mid)
            ORDER BY created_at ASC;
        """)
        rows = self.session.execute(sql, {"mid": str(mission_id)}).mappings().all()
        return [dict(row) for row in rows]

    def get_time_windows(self, mission_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves time windows associated with this mission."""
        sql = text("""
            SELECT id, type, open_at, close_at, hard_or_soft, subject_type, subject_id, status, description, data_provenance
            FROM time_windows
            WHERE subject_type = 'MISSION' AND subject_id = :mid
            ORDER BY open_at ASC;
        """)
        rows = self.session.execute(sql, {"mid": str(mission_id)}).mappings().all()
        return [dict(row) for row in rows]
