"""Pydantic v2 Schemas for Polar Utility & Consumables Runway Engine Read Models."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class BurnRateEvidence(BaseModel):
    """Detailed evidence supporting the calculated daily burn rate."""
    observations: int = Field(default=0, description="Count of physical consumption transactions observed")
    consumed_quantity: float = Field(default=0.0, description="Total units consumed in observation window")
    elapsed_days: float = Field(default=0.0, description="Elapsed days across observed transactions")
    window_days: int = Field(default=14, description="Lookback window duration in days")
    baseline_daily_burn_rate: Optional[float] = Field(default=None, description="Catalog fallback rate if used")


class ResourceRunwayItem(BaseModel):
    """Deterministic operational runway metrics for a single consumable inventory stock lot."""
    model_config = ConfigDict(from_attributes=True)

    stock_lot_id: uuid.UUID
    inventory_item_id: uuid.UUID
    lot_code: Optional[str] = None
    item_code: str
    item_name: str
    category: str
    criticality: str
    unit: str
    location_id: uuid.UUID
    location_name: Optional[str] = None

    # Authoritative balances
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    quarantined_quantity: Decimal
    damaged_quantity: Decimal
    available_quantity: Decimal

    # Existing repository thresholds
    reorder_point: Optional[Decimal] = None
    replenishment_lead_days: Optional[int] = None
    reorder_buffer_days: Optional[float] = Field(
        default=None,
        description="Deterministic buffer: reorder_point / daily_burn_rate (when burn rate > 0)"
    )

    # Burn rate & evidence
    daily_burn_rate: Decimal = Field(description="Units consumed per 24 hours")
    burn_rate_source: str = Field(description="OBSERVED_TRANSACTIONS_14D | CATALOG_BASELINE | NO_CONSUMPTION_OBSERVED")
    burn_rate_evidence: Dict[str, Any] = Field(default_factory=dict)

    # Forecast projections
    runway_days: Optional[float] = Field(default=None, description="Days of supply remaining before stockout (None if zero burn)")
    exhaustion_at: Optional[datetime] = Field(default=None, description="Projected calendar timestamp of stock depletion (FORECAST)")
    next_inbound_at: Optional[datetime] = Field(default=None, description="Scheduled replenishment arrival timestamp (MEASURED/FORECAST)")
    resupply_gap_days: float = Field(default=0.0, description="Days of deficit between exhaustion and resupply arrival")

    # Deterministic runway state
    # Ordering: NO_CONSUMPTION_OBSERVED -> RESUPPLY_GAP -> NO_INBOUND_SCHEDULED -> AT_RISK -> COVERED
    runway_state: str = Field(
        description="RESUPPLY_GAP | AT_RISK | COVERED | NO_INBOUND_SCHEDULED | NO_CONSUMPTION_OBSERVED"
    )

    # Contextual linkages
    dependent_mission_id: Optional[uuid.UUID] = None
    dependent_asset_id: Optional[uuid.UUID] = None
    active_constraint_id: Optional[uuid.UUID] = None

    # Provenance
    data_provenance: str = Field(default="FORECAST", description="Provenance of the runway projection")


class ResourceRunwaySummary(BaseModel):
    """Campaign-level summary of consumable resource continuity and resupply gap posture."""
    model_config = ConfigDict(from_attributes=True)

    expedition_id: uuid.UUID
    evaluated_at: datetime
    total_candidates: int = Field(default=0, description="Total consumable stock lots evaluated")
    items_with_resupply_gap: int = Field(default=0, description="Count of lots with exhaustion preceding inbound arrival")
    items_at_risk: int = Field(default=0, description="Count of lots breaching lead-time or reorder buffer")
    minimum_runway_days: Optional[float] = Field(default=None, description="Shortest consumable runway horizon in campaign")
    runways: List[ResourceRunwayItem] = Field(default_factory=list)
    data_provenance: str = Field(default="DERIVED", description="Provenance of aggregate runway rollup")
