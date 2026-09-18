"""SQLAlchemy Data Access Repository for Inventory Items, Stock Lots, and Transactions."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)


class InventoryRepository:
    """Encapsulates transactional database access operations for Inventory entities."""

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # 1. CATALOG ITEMS
    # ============================================================

    def get_item_by_id(self, item_id: uuid.UUID) -> Optional[InventoryItemModel]:
        stmt = select(InventoryItemModel).where(InventoryItemModel.id == item_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_item_by_code(self, item_code: str) -> Optional[InventoryItemModel]:
        stmt = select(InventoryItemModel).where(InventoryItemModel.item_code == item_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_items(
        self,
        category: Optional[str] = None,
        criticality: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryItemModel], int]:
        query = select(InventoryItemModel)
        count_query = select(func.count(InventoryItemModel.id))

        if category:
            query = query.where(InventoryItemModel.category == category)
            count_query = count_query.where(InventoryItemModel.category == category)
        if criticality:
            query = query.where(InventoryItemModel.criticality == criticality)
            count_query = count_query.where(InventoryItemModel.criticality == criticality)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(InventoryItemModel.item_code.asc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create_item(self, model: InventoryItemModel) -> InventoryItemModel:
        self.session.add(model)
        self.session.flush()
        return model

    # ============================================================
    # 2. STOCK LOTS
    # ============================================================

    def get_stock_lot_by_id(self, lot_id: uuid.UUID) -> Optional[InventoryStockLotModel]:
        stmt = select(InventoryStockLotModel).where(InventoryStockLotModel.id == lot_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_stock_lots(
        self,
        inventory_item_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryStockLotModel], int]:
        query = select(InventoryStockLotModel)
        count_query = select(func.count(InventoryStockLotModel.id))

        if inventory_item_id:
            query = query.where(InventoryStockLotModel.inventory_item_id == inventory_item_id)
            count_query = count_query.where(InventoryStockLotModel.inventory_item_id == inventory_item_id)
        if location_id:
            query = query.where(InventoryStockLotModel.location_id == location_id)
            count_query = count_query.where(InventoryStockLotModel.location_id == location_id)
        if status:
            query = query.where(InventoryStockLotModel.status == status)
            count_query = count_query.where(InventoryStockLotModel.status == status)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(InventoryStockLotModel.created_at.desc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create_stock_lot(self, model: InventoryStockLotModel) -> InventoryStockLotModel:
        self.session.add(model)
        self.session.flush()
        return model

    def update_stock_lot(self, model: InventoryStockLotModel) -> InventoryStockLotModel:
        self.session.flush()
        return model

    # ============================================================
    # 3. IMMUTABLE TRANSACTION LEDGER
    # ============================================================

    def append_transaction(self, model: InventoryTransactionModel) -> InventoryTransactionModel:
        self.session.add(model)
        self.session.flush()
        return model

    def list_transactions_by_lot(
        self,
        stock_lot_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[InventoryTransactionModel], int]:
        query = select(InventoryTransactionModel).where(InventoryTransactionModel.stock_lot_id == stock_lot_id)
        count_query = select(func.count(InventoryTransactionModel.id)).where(InventoryTransactionModel.stock_lot_id == stock_lot_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(desc(InventoryTransactionModel.occurred_at)).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total
