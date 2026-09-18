"""SQLAlchemy Data Access Repository for Cargo Consignments and Packages."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel


class CargoRepository:
    """Encapsulates database operations for Cargo consignments and packages."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------
    # Consignment Operations
    # ------------------------------------------------------------

    def get_by_id(self, consignment_id: uuid.UUID) -> Optional[CargoConsignmentModel]:
        stmt = select(CargoConsignmentModel).options(
            selectinload(CargoConsignmentModel.packages)
        ).where(CargoConsignmentModel.id == consignment_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[CargoConsignmentModel]:
        stmt = select(CargoConsignmentModel).options(
            selectinload(CargoConsignmentModel.packages)
        ).where(CargoConsignmentModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_consignments(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        origin_location_id: Optional[uuid.UUID] = None,
        destination_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CargoConsignmentModel], int]:
        query = select(CargoConsignmentModel).options(
            selectinload(CargoConsignmentModel.packages)
        )
        count_query = select(func.count(CargoConsignmentModel.id))

        if expedition_id is not None:
            query = query.where(CargoConsignmentModel.expedition_id == expedition_id)
            count_query = count_query.where(CargoConsignmentModel.expedition_id == expedition_id)
        if status:
            query = query.where(CargoConsignmentModel.status == status)
            count_query = count_query.where(CargoConsignmentModel.status == status)
        if risk_level:
            query = query.where(CargoConsignmentModel.risk_level == risk_level)
            count_query = count_query.where(CargoConsignmentModel.risk_level == risk_level)
        if origin_location_id is not None:
            query = query.where(CargoConsignmentModel.origin_location_id == origin_location_id)
            count_query = count_query.where(CargoConsignmentModel.origin_location_id == origin_location_id)
        if destination_location_id is not None:
            query = query.where(CargoConsignmentModel.destination_location_id == destination_location_id)
            count_query = count_query.where(CargoConsignmentModel.destination_location_id == destination_location_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(CargoConsignmentModel.code.asc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create(self, model: CargoConsignmentModel) -> CargoConsignmentModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update(self, model: CargoConsignmentModel) -> CargoConsignmentModel:
        self.session.flush()
        return model

    # ------------------------------------------------------------
    # Package Operations
    # ------------------------------------------------------------

    def get_package_by_id(self, package_id: uuid.UUID) -> Optional[CargoPackageModel]:
        stmt = select(CargoPackageModel).where(CargoPackageModel.id == package_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_package_by_code(self, code: str) -> Optional[CargoPackageModel]:
        stmt = select(CargoPackageModel).where(CargoPackageModel.code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_packages_by_consignment(self, consignment_id: uuid.UUID) -> List[CargoPackageModel]:
        stmt = select(CargoPackageModel).where(
            CargoPackageModel.consignment_id == consignment_id
        ).order_by(CargoPackageModel.code.asc())
        return list(self.session.execute(stmt).scalars().all())

    def create_package(self, model: CargoPackageModel) -> CargoPackageModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update_package(self, model: CargoPackageModel) -> CargoPackageModel:
        self.session.flush()
        return model
