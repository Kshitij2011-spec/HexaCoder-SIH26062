"""SQLAlchemy Data Access Repository for Transport Legs and Cargo Assignments."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.app.domains.transport.models import TransportLegModel, TransportCargoAssignmentModel
from backend.app.domains.cargo.models import CargoConsignmentModel


class TransportRepository:
    """Encapsulates database operations for Transport legs and physical cargo manifests."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, leg_id: uuid.UUID) -> Optional[TransportLegModel]:
        stmt = select(TransportLegModel).where(TransportLegModel.id == leg_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[TransportLegModel]:
        stmt = select(TransportLegModel).where(TransportLegModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_legs(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        origin_location_id: Optional[uuid.UUID] = None,
        destination_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TransportLegModel], int]:
        query = select(TransportLegModel)
        count_query = select(func.count(TransportLegModel.id))

        if expedition_id is not None:
            query = query.where(TransportLegModel.expedition_id == expedition_id)
            count_query = count_query.where(TransportLegModel.expedition_id == expedition_id)
        if mode:
            query = query.where(TransportLegModel.mode == mode)
            count_query = count_query.where(TransportLegModel.mode == mode)
        if status:
            query = query.where(TransportLegModel.status == status)
            count_query = count_query.where(TransportLegModel.status == status)
        if origin_location_id is not None:
            query = query.where(TransportLegModel.origin_location_id == origin_location_id)
            count_query = count_query.where(TransportLegModel.origin_location_id == origin_location_id)
        if destination_location_id is not None:
            query = query.where(TransportLegModel.destination_location_id == destination_location_id)
            count_query = count_query.where(TransportLegModel.destination_location_id == destination_location_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(TransportLegModel.code.asc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create(self, model: TransportLegModel) -> TransportLegModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update(self, model: TransportLegModel) -> TransportLegModel:
        self.session.flush()
        return model

    # ------------------------------------------------------------
    # Cargo Assignment Operations
    # ------------------------------------------------------------

    def create_cargo_assignment(self, model: TransportCargoAssignmentModel) -> TransportCargoAssignmentModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_assignment(self, transport_leg_id: uuid.UUID, cargo_consignment_id: uuid.UUID) -> Optional[TransportCargoAssignmentModel]:
        stmt = select(TransportCargoAssignmentModel).where(
            TransportCargoAssignmentModel.transport_leg_id == transport_leg_id,
            TransportCargoAssignmentModel.cargo_consignment_id == cargo_consignment_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_assignments_for_leg(self, transport_leg_id: uuid.UUID) -> List[TransportCargoAssignmentModel]:
        stmt = select(TransportCargoAssignmentModel).where(
            TransportCargoAssignmentModel.transport_leg_id == transport_leg_id
        ).order_by(TransportCargoAssignmentModel.assigned_at.asc())
        return list(self.session.execute(stmt).scalars().all())

    def list_active_cargo_consignments_for_leg(self, transport_leg_id: uuid.UUID) -> List[CargoConsignmentModel]:
        stmt = (
            select(CargoConsignmentModel)
            .join(
                TransportCargoAssignmentModel,
                TransportCargoAssignmentModel.cargo_consignment_id == CargoConsignmentModel.id
            )
            .where(
                TransportCargoAssignmentModel.transport_leg_id == transport_leg_id,
                TransportCargoAssignmentModel.released_at.is_(None)
            )
            .order_by(CargoConsignmentModel.code.asc())
        )
        return list(self.session.execute(stmt).scalars().all())
