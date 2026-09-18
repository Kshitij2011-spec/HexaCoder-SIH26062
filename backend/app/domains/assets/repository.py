"""SQLAlchemy Data Access Repository for Assets and Maintenance Records."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from backend.app.domains.assets.models import AssetModel, MaintenanceRecordModel
from backend.app.domains.assets.states import MaintenanceStatus


class AssetRepository:
    """Encapsulates transactional database access operations for Asset and Maintenance entities."""

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # 1. ASSET CRUD
    # ============================================================

    def get_by_id(self, asset_id: uuid.UUID) -> Optional[AssetModel]:
        stmt = select(AssetModel).where(AssetModel.id == asset_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, asset_code: str) -> Optional[AssetModel]:
        stmt = select(AssetModel).where(AssetModel.asset_code == asset_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_serial(self, serial_number: str) -> Optional[AssetModel]:
        if not serial_number:
            return None
        stmt = select(AssetModel).where(AssetModel.serial_number == serial_number)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_assets(
        self,
        type_: Optional[str] = None,
        status: Optional[str] = None,
        location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[AssetModel], int]:
        query = select(AssetModel)
        count_query = select(func.count(AssetModel.id))

        if type_:
            query = query.where(AssetModel.type == type_)
            count_query = count_query.where(AssetModel.type == type_)
        if status:
            query = query.where(AssetModel.status == status)
            count_query = count_query.where(AssetModel.status == status)
        if location_id is not None:
            query = query.where(AssetModel.location_id == location_id)
            count_query = count_query.where(AssetModel.location_id == location_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(AssetModel.asset_code.asc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create(self, model: AssetModel) -> AssetModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update(self, model: AssetModel) -> AssetModel:
        self.session.flush()
        return model

    # ============================================================
    # 2. MAINTENANCE RECORDS
    # ============================================================

    def get_maintenance_by_id(self, record_id: uuid.UUID) -> Optional[MaintenanceRecordModel]:
        stmt = select(MaintenanceRecordModel).where(MaintenanceRecordModel.id == record_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_maintenance_by_asset(
        self,
        asset_id: uuid.UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[MaintenanceRecordModel], int]:
        query = select(MaintenanceRecordModel).where(MaintenanceRecordModel.asset_id == asset_id)
        count_query = select(func.count(MaintenanceRecordModel.id)).where(MaintenanceRecordModel.asset_id == asset_id)

        if status:
            query = query.where(MaintenanceRecordModel.status == status)
            count_query = count_query.where(MaintenanceRecordModel.status == status)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(desc(MaintenanceRecordModel.created_at)).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def get_active_maintenance_for_asset(
        self,
        asset_id: uuid.UUID,
        for_update: bool = False
    ) -> Optional[MaintenanceRecordModel]:
        """
        Retrieves active maintenance (SCHEDULED or IN_PROGRESS) for an asset.
        Supports row-level lock if requested and backend supports it.
        """
        active_statuses = [MaintenanceStatus.SCHEDULED.value, MaintenanceStatus.IN_PROGRESS.value]
        stmt = select(MaintenanceRecordModel).where(
            MaintenanceRecordModel.asset_id == asset_id,
            MaintenanceRecordModel.status.in_(active_statuses)
        )
        if for_update and self.session.bind and self.session.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalars().first()

    def create_maintenance(self, model: MaintenanceRecordModel) -> MaintenanceRecordModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update_maintenance(self, model: MaintenanceRecordModel) -> MaintenanceRecordModel:
        self.session.flush()
        return model
