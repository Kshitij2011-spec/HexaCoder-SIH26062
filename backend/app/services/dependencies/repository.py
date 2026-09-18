"""Repository for Semantic Dependencies."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_
from backend.app.services.dependencies.models import DependencyModel


class DependencyRepository:
    """Data access repository for dependencies table."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, dep_id: uuid.UUID) -> Optional[DependencyModel]:
        return self.session.execute(
            select(DependencyModel).where(DependencyModel.id == dep_id)
        ).scalar_one_or_none()

    def get_outgoing(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        relationship_type: Optional[str] = None
    ) -> List[DependencyModel]:
        """Finds all dependencies where entity is the source (entity -> target)."""
        query = select(DependencyModel).where(
            DependencyModel.source_entity_type == entity_type.upper(),
            DependencyModel.source_entity_id == entity_id
        )
        if relationship_type:
            query = query.where(DependencyModel.relationship_type == relationship_type.upper())
        query = query.order_by(DependencyModel.created_at.asc())
        return list(self.session.execute(query).scalars().all())

    def get_incoming(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        relationship_type: Optional[str] = None
    ) -> List[DependencyModel]:
        """Finds all dependencies where entity is the target (source -> entity)."""
        query = select(DependencyModel).where(
            DependencyModel.target_entity_type == entity_type.upper(),
            DependencyModel.target_entity_id == entity_id
        )
        if relationship_type:
            query = query.where(DependencyModel.relationship_type == relationship_type.upper())
        query = query.order_by(DependencyModel.created_at.asc())
        return list(self.session.execute(query).scalars().all())

    def get_connected(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        relationship_type: Optional[str] = None
    ) -> List[DependencyModel]:
        """Finds all dependencies where entity is either source or target."""
        e_type = entity_type.upper()
        query = select(DependencyModel).where(
            or_(
                and_(
                    DependencyModel.source_entity_type == e_type,
                    DependencyModel.source_entity_id == entity_id
                ),
                and_(
                    DependencyModel.target_entity_type == e_type,
                    DependencyModel.target_entity_id == entity_id
                )
            )
        )
        if relationship_type:
            query = query.where(DependencyModel.relationship_type == relationship_type.upper())
        query = query.order_by(DependencyModel.created_at.asc())
        return list(self.session.execute(query).scalars().all())

    def create(self, model: DependencyModel) -> DependencyModel:
        self.session.add(model)
        self.session.flush()
        return model
