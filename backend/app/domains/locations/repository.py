"""SQLAlchemy Data Access Repository for Locations."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.app.domains.locations.models import LocationModel


class LocationRepository:
    """Encapsulates database access operations for Location entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, location_id: uuid.UUID) -> Optional[LocationModel]:
        stmt = select(LocationModel).where(LocationModel.id == location_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[LocationModel]:
        stmt = select(LocationModel).where(LocationModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_locations(
        self,
        type_: Optional[str] = None,
        status: Optional[str] = None,
        parent_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LocationModel], int]:
        query = select(LocationModel)
        count_query = select(func.count(LocationModel.id))

        if type_:
            query = query.where(LocationModel.type == type_)
            count_query = count_query.where(LocationModel.type == type_)
        if status:
            query = query.where(LocationModel.status == status)
            count_query = count_query.where(LocationModel.status == status)
        if parent_location_id is not None:
            query = query.where(LocationModel.parent_location_id == parent_location_id)
            count_query = count_query.where(LocationModel.parent_location_id == parent_location_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(LocationModel.code.asc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def get_children(self, parent_location_id: uuid.UUID) -> List[LocationModel]:
        stmt = select(LocationModel).where(LocationModel.parent_location_id == parent_location_id).order_by(LocationModel.code.asc())
        return list(self.session.execute(stmt).scalars().all())

    def create(self, model: LocationModel) -> LocationModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update(self, model: LocationModel) -> LocationModel:
        self.session.flush()
        return model
