"""Polar Utility & Consumables Runway Engine Domain Service.

Provides deterministic consumption burn-rate calculation, runway exhaustion horizons,
and resupply gap analysis for critical polar resources without simulating SCADA or telemetry.
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, desc

from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.inventory.service import calculate_lot_availability
from backend.app.domains.inventory.runway_schemas import (
    ResourceRunwayItem,
    ResourceRunwaySummary,
)
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.missions.models import MissionModel
from backend.app.services.constraints.models import ConstraintModel
from backend.app.shared.types.states import InventoryTransactionType
from backend.app.core.errors import EntityNotFoundError


def ensure_utc(dt: Optional[datetime]) -> datetime:
    """Ensures datetime object is timezone-aware and normalized to UTC."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


CONSUMABLE_CATEGORIES = {
    "FUEL",
    "FOOD",
    "RATIONS",
    "WATER",
    "MEDICAL",
    "CONSUMABLES",
    "GASES",
    "SURVIVAL",
    "SPARES",
}

CRITICAL_TIERS = {
    "CRITICAL",
    "HIGH",
    "LIFE_SUPPORT",
    "MISSION_CRITICAL",
    "SAFETY",
}


class ResourceRunwayService:
    """
    Deterministic domain service for polar utility and consumables runway modeling.
    Derives burn rates from immutable transaction ledger records, computes projected
    exhaustion dates, and detects resupply deficit gaps before replenishment arrivals.
    """

    def __init__(self, session: Session):
        self.session = session

    def evaluate_lot_runway(
        self,
        lot_id: uuid.UUID,
        lookback_days: int = 14,
        now_dt: Optional[datetime] = None,
    ) -> Optional[ResourceRunwayItem]:
        """Calculates deterministic runway metrics for a single stock lot."""
        lot = self.session.get(InventoryStockLotModel, lot_id)
        if not lot:
            return None

        item = self.session.get(InventoryItemModel, lot.inventory_item_id)
        if not item:
            return None

        now_utc = ensure_utc(now_dt)
        location = self.session.get(LocationModel, lot.location_id)
        location_name = location.name if location else None

        # 1. Authoritative available balance
        on_hand = Decimal(str(lot.on_hand_quantity or "0"))
        reserved = Decimal(str(lot.reserved_quantity or "0"))
        quarantined = Decimal(str(lot.quarantined_quantity or "0"))
        damaged = Decimal(str(lot.damaged_quantity or "0"))
        reorder_point = Decimal(str(lot.reorder_point)) if lot.reorder_point is not None else None

        available, _ = calculate_lot_availability(
            on_hand=on_hand,
            reserved=reserved,
            quarantined=quarantined,
            damaged=damaged,
            reorder_point=reorder_point,
        )

        # 2. Derive daily burn rate from verified physical ISSUE transactions
        cutoff_date = now_utc - timedelta(days=lookback_days)
        tx_stmt = (
            select(InventoryTransactionModel)
            .where(
                InventoryTransactionModel.stock_lot_id == lot.id,
                InventoryTransactionModel.transaction_type == InventoryTransactionType.ISSUE.value,
                InventoryTransactionModel.occurred_at >= cutoff_date,
                InventoryTransactionModel.quantity > 0,
            )
            .order_by(InventoryTransactionModel.occurred_at.asc())
        )
        qualifying_txs = list(self.session.execute(tx_stmt).scalars().all())

        daily_burn_rate = Decimal("0.00")
        burn_rate_source = "NO_CONSUMPTION_OBSERVED"
        burn_rate_evidence: Dict[str, Any] = {}

        if qualifying_txs:
            total_consumed = sum(Decimal(str(tx.quantity)) for tx in qualifying_txs)
            earliest_dt = ensure_utc(qualifying_txs[0].occurred_at)
            elapsed_seconds = max(1.0, (now_utc - earliest_dt).total_seconds())
            elapsed_days = max(1.0, elapsed_seconds / 86400.0)

            daily_burn_rate = (total_consumed / Decimal(str(elapsed_days))).quantize(Decimal("0.01"))
            burn_rate_source = f"OBSERVED_TRANSACTIONS_{lookback_days}D"
            burn_rate_evidence = {
                "observations": len(qualifying_txs),
                "consumed_quantity": float(total_consumed),
                "elapsed_days": round(elapsed_days, 2),
                "window_days": lookback_days,
            }
        else:
            # Fallback to catalog or stock lot declared baseline if present
            lot_meta = lot.operational_metadata or {}
            item_meta = item.operational_metadata or {}
            baseline = lot_meta.get("baseline_daily_burn_rate") or item_meta.get("baseline_daily_burn_rate")

            if baseline is not None:
                try:
                    b_dec = Decimal(str(baseline))
                    if b_dec > 0:
                        daily_burn_rate = b_dec.quantize(Decimal("0.01"))
                        burn_rate_source = "CATALOG_BASELINE"
                        burn_rate_evidence = {"baseline_daily_burn_rate": float(b_dec)}
                except Exception:
                    pass

        # 3. Deterministic buffer horizon (reorder_point / daily_burn_rate)
        reorder_buffer_days: Optional[float] = None
        if daily_burn_rate > Decimal("0") and reorder_point is not None:
            reorder_buffer_days = round(float(reorder_point / daily_burn_rate), 1)

        # 4. Runway Days & Projected Exhaustion Horizon
        runway_days: Optional[float] = None
        exhaustion_at: Optional[datetime] = None

        if daily_burn_rate > Decimal("0"):
            runway_days = round(float(available / daily_burn_rate), 1)
            exhaustion_at = now_utc + timedelta(days=runway_days)

        # 5. Resupply Gap Analysis
        resupply_gap_days = 0.0
        inbound_at_utc: Optional[datetime] = None
        if lot.next_inbound_at is not None:
            inbound_at_utc = ensure_utc(lot.next_inbound_at)
            if exhaustion_at is not None and exhaustion_at < inbound_at_utc:
                gap_seconds = (inbound_at_utc - exhaustion_at).total_seconds()
                resupply_gap_days = round(max(0.0, gap_seconds / 86400.0), 1)

        # 6. Deterministic Runway Operational State Ordering
        # Order: NO_CONSUMPTION_OBSERVED -> RESUPPLY_GAP -> NO_INBOUND_SCHEDULED -> AT_RISK -> COVERED
        lead_days = lot.replenishment_lead_days

        if daily_burn_rate <= Decimal("0"):
            runway_state = "NO_CONSUMPTION_OBSERVED"
        elif inbound_at_utc is not None and resupply_gap_days > 0.0:
            runway_state = "RESUPPLY_GAP"
        elif inbound_at_utc is None and (
            (reorder_point is not None and available <= reorder_point)
            or (reorder_buffer_days is not None and runway_days is not None and runway_days <= reorder_buffer_days)
            or (lead_days is not None and runway_days is not None and runway_days <= float(lead_days))
        ):
            runway_state = "NO_INBOUND_SCHEDULED"
        elif inbound_at_utc is not None and (
            (lead_days is not None and runway_days is not None and runway_days <= float(lead_days))
            or (reorder_point is not None and available <= reorder_point)
            or (reorder_buffer_days is not None and runway_days is not None and runway_days <= reorder_buffer_days)
        ):
            runway_state = "AT_RISK"
        else:
            runway_state = "COVERED"

        # 7. Check if active constraint exists for this stock lot
        active_constraint_id = None
        c_stmt = select(ConstraintModel.id).where(
            ConstraintModel.active.is_(True),
            ConstraintModel.subject_id == lot.id,
            ConstraintModel.rule_code.in_(["RESOURCE_RUNWAY_HORIZON", "INVENTORY_AVAILABILITY"]),
        )
        active_constraint_id = self.session.execute(c_stmt).scalars().first()

        return ResourceRunwayItem(
            stock_lot_id=lot.id,
            inventory_item_id=item.id,
            lot_code=lot.lot_code,
            item_code=item.item_code,
            item_name=item.item_name,
            category=item.category,
            criticality=str(item.criticality),
            unit=item.unit,
            location_id=lot.location_id,
            location_name=location_name,
            on_hand_quantity=on_hand,
            reserved_quantity=reserved,
            quarantined_quantity=quarantined,
            damaged_quantity=damaged,
            available_quantity=available,
            reorder_point=reorder_point,
            replenishment_lead_days=lead_days,
            reorder_buffer_days=reorder_buffer_days,
            daily_burn_rate=daily_burn_rate,
            burn_rate_source=burn_rate_source,
            burn_rate_evidence=burn_rate_evidence,
            runway_days=runway_days,
            exhaustion_at=exhaustion_at,
            next_inbound_at=inbound_at_utc,
            resupply_gap_days=resupply_gap_days,
            runway_state=runway_state,
            dependent_mission_id=lot.dependent_mission_id,
            dependent_asset_id=lot.dependent_asset_id,
            active_constraint_id=active_constraint_id,
            data_provenance="FORECAST",
        )

    def get_expedition_runways(
        self,
        expedition_id: uuid.UUID,
        location_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        criticality: Optional[str] = None,
        lookback_days: int = 14,
    ) -> ResourceRunwaySummary:
        """
        Gathers and evaluates all candidate consumable inventory lots for an expedition campaign.
        Filters strictly by candidate selection criteria (consumable categories, critical tiers,
        or mission/asset bindings).
        """
        now_utc = datetime.now(timezone.utc)

        # 1. Discover operational locations and missions for the expedition
        missions = list(
            self.session.execute(
                select(MissionModel).where(MissionModel.expedition_id == expedition_id)
            ).scalars().all()
        )
        mission_ids = {m.id for m in missions}
        expedition_location_ids = {m.location_id for m in missions if m.location_id}

        # 2. Query active stock lots
        lot_stmt = (
            select(InventoryStockLotModel, InventoryItemModel)
            .join(InventoryItemModel, InventoryStockLotModel.inventory_item_id == InventoryItemModel.id)
            .where(
                InventoryStockLotModel.status.in_(["AVAILABLE", "RESERVED"])
            )
        )

        if location_id:
            lot_stmt = lot_stmt.where(InventoryStockLotModel.location_id == location_id)
        elif expedition_location_ids or mission_ids:
            # Match lots either assigned to the expedition's locations or explicitly linked to its missions
            lot_conditions = []
            if expedition_location_ids:
                lot_conditions.append(InventoryStockLotModel.location_id.in_(expedition_location_ids))
            if mission_ids:
                lot_conditions.append(InventoryStockLotModel.dependent_mission_id.in_(mission_ids))
            lot_stmt = lot_stmt.where(or_(*lot_conditions))

        if category:
            lot_stmt = lot_stmt.where(InventoryItemModel.category == category)
        if criticality:
            lot_stmt = lot_stmt.where(InventoryItemModel.criticality == criticality)

        rows = list(self.session.execute(lot_stmt).all())

        runway_items: List[ResourceRunwayItem] = []
        for lot, item in rows:
            # Deterministic Resource Selection Filter
            item_cat = (item.category or "").upper()
            item_crit = (str(item.criticality) or "").upper()
            is_consumable = (
                item_cat in CONSUMABLE_CATEGORIES
                or item_crit in CRITICAL_TIERS
                or lot.dependent_mission_id is not None
                or lot.dependent_asset_id is not None
            )
            if not is_consumable:
                continue

            evaluated = self.evaluate_lot_runway(lot.id, lookback_days=lookback_days, now_dt=now_utc)
            if evaluated:
                runway_items.append(evaluated)

        # Sort: RESUPPLY_GAP first, then AT_RISK, then NO_INBOUND_SCHEDULED, then COVERED, then NO_CONSUMPTION_OBSERVED
        state_priority = {
            "RESUPPLY_GAP": 0,
            "AT_RISK": 1,
            "NO_INBOUND_SCHEDULED": 2,
            "COVERED": 3,
            "NO_CONSUMPTION_OBSERVED": 4,
        }
        runway_items.sort(
            key=lambda x: (
                state_priority.get(x.runway_state, 99),
                x.runway_days if x.runway_days is not None else 999999.0,
            )
        )

        gap_count = sum(1 for r in runway_items if r.runway_state == "RESUPPLY_GAP")
        at_risk_count = sum(1 for r in runway_items if r.runway_state == "AT_RISK")
        active_runways = [r.runway_days for r in runway_items if r.runway_days is not None]
        min_runway = min(active_runways) if active_runways else None

        return ResourceRunwaySummary(
            expedition_id=expedition_id,
            evaluated_at=now_utc,
            total_candidates=len(runway_items),
            items_with_resupply_gap=gap_count,
            items_at_risk=at_risk_count,
            minimum_runway_days=min_runway,
            runways=runway_items,
            data_provenance="DERIVED",
        )
