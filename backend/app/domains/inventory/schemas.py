"""Pydantic Schemas for Inventory Catalog, Stock Lots, and Ledger."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.shared.types.states import InventoryStatus, InventoryTransactionType, ItemCriticality
from backend.app.shared.types.provenance import DataProvenance
from backend.app.core.errors import DomainValidationError


# ============================================================
# 1. CATALOG ITEMS SCHEMAS
# ============================================================

class InventoryItemBase(BaseModel):
    item_name: str = Field(min_length=2, max_length=255, description="Item name / label")
    category: str = Field(min_length=2, max_length=100, description="Logistics category e.g. RATIONS, FUEL, SPARE_PARTS, MEDICAL")
    unit: str = Field(min_length=1, max_length=50, description="Unit of measure e.g. KG, LITER, UNIT, BOX")
    criticality: ItemCriticality = Field(default=ItemCriticality.STANDARD, description="Expedition criticality tier")
    description: Optional[str] = Field(default=None, description="Detailed item specification")
    operational_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom specifications or attributes")
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)


class InventoryItemCreate(InventoryItemBase):
    item_code: str = Field(min_length=2, max_length=50, description="Unique catalog code e.g. ITEM-FUEL-JET1")


class InventoryItemRead(InventoryItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_code: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# 2. STOCK LOTS SCHEMAS
# ============================================================

class InventoryStockLotBase(BaseModel):
    lot_code: Optional[str] = Field(default=None, max_length=50, description="Batch/Lot identifier")
    location_id: uuid.UUID = Field(description="Location where stock is stored")
    on_hand_quantity: Decimal = Field(default=Decimal("0"), ge=0, description="Total physical on-hand quantity")
    reserved_quantity: Decimal = Field(default=Decimal("0"), ge=0, description="Quantity committed to missions/cargo")
    quarantined_quantity: Decimal = Field(default=Decimal("0"), ge=0, description="Quantity withheld for inspection/hazard")
    damaged_quantity: Decimal = Field(default=Decimal("0"), ge=0, description="Quantity damaged/unusable")
    status: InventoryStatus = Field(default=InventoryStatus.AVAILABLE)
    condition: str = Field(default="GOOD", max_length=100)
    reorder_point: Optional[Decimal] = Field(default=None, ge=0, description="Safety stock threshold for reorder")
    replenishment_lead_days: Optional[int] = Field(default=None, ge=0)
    next_inbound_at: Optional[datetime] = None
    dependent_asset_id: Optional[uuid.UUID] = None
    dependent_mission_id: Optional[uuid.UUID] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)
    data_provenance: DataProvenance = Field(default=DataProvenance.SYNTHETIC_DEMO)

    @field_validator("reserved_quantity")
    @classmethod
    def validate_reserved(cls, v: Decimal, info) -> Decimal:
        on_hand = info.data.get("on_hand_quantity", Decimal("0"))
        if v > on_hand:
            raise DomainValidationError("Reserved quantity cannot exceed on-hand quantity", field="reserved_quantity")
        return v


class InventoryStockLotCreate(InventoryStockLotBase):
    inventory_item_id: uuid.UUID = Field(description="Catalog item reference")


class InventoryStockLotRead(InventoryStockLotBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_item_id: uuid.UUID
    available_quantity: Decimal = Field(default=Decimal("0"), description="Available unreserved, unquarantined stock")
    is_deficit: bool = Field(default=False, description="True if available quantity <= reorder point")
    created_at: datetime
    updated_at: datetime


class StockAvailabilityRead(BaseModel):
    stock_lot_id: uuid.UUID
    inventory_item_id: uuid.UUID
    location_id: uuid.UUID
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    quarantined_quantity: Decimal
    damaged_quantity: Decimal
    available_quantity: Decimal
    reorder_point: Optional[Decimal]
    is_deficit: bool
    status: InventoryStatus


# ============================================================
# 3. TRANSACTION LEDGER SCHEMAS
# ============================================================

class InventoryTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_lot_id: uuid.UUID
    transaction_type: InventoryTransactionType
    quantity: Decimal
    reference_type: Optional[str]
    reference_id: Optional[uuid.UUID]
    performed_by_person_id: Optional[uuid.UUID]
    occurred_at: datetime
    notes: Optional[str]
    operational_metadata: Dict[str, Any]
    data_provenance: DataProvenance
    created_at: datetime


# ============================================================
# 4. OPERATIONAL MUTATION REQUEST SCHEMAS
# ============================================================

class StockReceiptRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Quantity to receive into stock")
    reference_type: Optional[str] = Field(default=None, description="Source reference e.g. CARGO_PACKAGE, CONSIGNMENT")
    reference_id: Optional[uuid.UUID] = Field(default=None, description="UUID of source cargo/package/shipment")
    performed_by_person_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, description="Receipt notes or inspection summary")
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class StockReservationRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Quantity to reserve from available stock")
    reference_type: Optional[str] = Field(default=None, description="Target reference e.g. MISSION, CARGO_PACKAGE")
    reference_id: Optional[uuid.UUID] = Field(default=None, description="UUID of target consumer/assignment")
    performed_by_person_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class StockReleaseRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Quantity of reservation to release back to available")
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    performed_by_person_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class StockIssueRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Quantity to issue out from reserved or on-hand stock")
    reference_type: Optional[str] = Field(default=None, description="Issuance reference e.g. MISSION, PERSON")
    reference_id: Optional[uuid.UUID] = None
    performed_by_person_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class StockQuarantineRequest(BaseModel):
    quantity: Decimal = Field(gt=0, description="Quantity to quarantine from available stock")
    reason: str = Field(min_length=3, description="Justification for quarantine e.g. cold-chain breach, damage")
    performed_by_person_id: Optional[uuid.UUID] = None
    operational_metadata: Dict[str, Any] = Field(default_factory=dict)


class StockStatusTransitionRequest(BaseModel):
    target_status: InventoryStatus
    reason: Optional[str] = None
    performed_by_person_id: Optional[uuid.UUID] = None
