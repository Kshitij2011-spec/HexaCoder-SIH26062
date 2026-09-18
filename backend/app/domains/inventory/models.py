"""SQLAlchemy ORM Models for Inventory Catalog, Stock Lots, and Ledger Transactions."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base, PG_UUID, PG_JSON


class InventoryItemModel(Base):
    """
    Inventory Item Entity mapping to public.inventory_items.
    Standardized catalog item for equipment, rations, fuel, scientific supplies, and spares.
    """
    __tablename__ = "inventory_items"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    item_code = Column(String(50), unique=True, nullable=False)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=False)
    criticality = Column(String(50), nullable=False, default="STANDARD")
    description = Column(Text, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    stock_lots = relationship("InventoryStockLotModel", back_populates="item", cascade="all, delete-orphan")


class InventoryStockLotModel(Base):
    """
    Inventory Stock Lot Entity mapping to public.inventory_stock_lots.
    Physical lot/batch of inventory stored at a specific polar or hub location.
    """
    __tablename__ = "inventory_stock_lots"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    inventory_item_id = Column(PG_UUID, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False)
    lot_code = Column(String(50), nullable=True)
    location_id = Column(PG_UUID, nullable=False)
    on_hand_quantity = Column(Numeric(12, 2), nullable=False, default=0)
    reserved_quantity = Column(Numeric(12, 2), nullable=False, default=0)
    quarantined_quantity = Column(Numeric(12, 2), nullable=False, default=0)
    damaged_quantity = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="AVAILABLE")
    condition = Column(String(100), nullable=False, default="GOOD")
    reorder_point = Column(Numeric(12, 2), nullable=True)
    replenishment_lead_days = Column(Integer, nullable=True)
    next_inbound_at = Column(DateTime(timezone=True), nullable=True)
    dependent_asset_id = Column(PG_UUID, nullable=True)
    dependent_mission_id = Column(PG_UUID, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    item = relationship("InventoryItemModel", back_populates="stock_lots")
    transactions = relationship(
        "InventoryTransactionModel",
        back_populates="stock_lot",
        cascade="all, delete-orphan",
        order_by="desc(InventoryTransactionModel.occurred_at)"
    )


class InventoryTransactionModel(Base):
    """
    Inventory Transaction Entity mapping to public.inventory_transactions.
    Immutable operational ledger entry recording stock movements and adjustments.
    """
    __tablename__ = "inventory_transactions"

    id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
    stock_lot_id = Column(PG_UUID, ForeignKey("inventory_stock_lots.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(PG_UUID, nullable=True)
    performed_by_person_id = Column(PG_UUID, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    operational_metadata = Column(PG_JSON, nullable=False, default=dict)
    data_provenance = Column(String(50), nullable=False, default="SYNTHETIC_DEMO")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    stock_lot = relationship("InventoryStockLotModel", back_populates="transactions")
