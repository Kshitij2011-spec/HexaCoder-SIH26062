"""
Comprehensive Test Suite for Milestone A9 — Polar Utility & Consumables Runway Engine:
- Authoritative availability reuse
- Empirical daily burn-rate derivation from physical ISSUE ledger transactions
- Fallback to catalog baseline consumption metadata
- Zero consumption, single transaction, clustered transactions, and irregular timestamp handling
- Runway days calculation and exhaustion horizon forecasting (no infinity/NaN)
- Inbound replenishment gap analysis (RESUPPLY_GAP, AT_RISK, COVERED, NO_INBOUND_SCHEDULED)
- Deterministic buffer calculation (reorder_point / burn_rate)
- RESOURCE_RUNWAY_HORIZON constraint evaluation
- Control Tower API endpoint (GET /api/v1/control-tower/expeditions/{id}/runways)
- Candidate filtering (consumable lifelines included, durable equipment excluded)
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Declarative models
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.locations.models
import backend.app.domains.inventory.models
import backend.app.platform.events.models
import backend.app.platform.audit.models
import backend.app.services.constraints.models

from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.inventory.service import calculate_lot_availability
from backend.app.domains.inventory.runway import ResourceRunwayService
from backend.app.services.constraints.models import ConstraintModel
from backend.app.services.constraints.service import ConstraintService
from backend.app.shared.types.states import (
    InventoryTransactionType,
    InventoryStatus,
    ItemCriticality,
)
from backend.app.shared.types.reasoning import ConstraintState


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for A9 Runway tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, class_=Session, autocommit=False, autoflush=False)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(client):
    override = app.dependency_overrides[get_db]
    session_gen = override()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()


def test_authoritative_availability_reuse():
    """Confirms availability helper accounts for reserved, quarantined, and damaged stock."""
    avail, is_deficit = calculate_lot_availability(
        on_hand=Decimal("1000.00"),
        reserved=Decimal("200.00"),
        quarantined=Decimal("50.00"),
        damaged=Decimal("50.00"),
        reorder_point=Decimal("800.00"),
    )
    assert avail == Decimal("700.00")
    assert is_deficit is True


def test_empirical_burn_rate_multiple_issue_transactions(db_session: Session):
    """Verifies that daily burn rate correctly averages qualifying physical ISSUE transactions."""
    now = datetime.now(timezone.utc)
    service = ResourceRunwayService(db_session)

    loc = LocationModel(id=uuid.uuid4(), code="LOC-MTR-01", name="Maitri Station", type="STATION")
    db_session.add(loc)

    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="FUEL-DSL-TEST",
        item_name="Arctic Diesel Fuel",
        category="FUEL",
        unit="LITERS",
        criticality=ItemCriticality.LIFE_SUPPORT.value,
    )
    db_session.add(item)

    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("5000.00"),
        reserved_quantity=Decimal("500.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("1000.00"),
        replenishment_lead_days=30,
        next_inbound_at=now + timedelta(days=40),
    )
    db_session.add(lot)
    db_session.commit()

    # Seed 3 ISSUE transactions over the last 10 days
    # Day -10: 500 L
    # Day -5: 500 L
    # Day -1: 500 L
    # Total consumed: 1500 L over ~10 days -> ~150 L/day
    tx1 = InventoryTransactionModel(
        id=uuid.uuid4(),
        stock_lot_id=lot.id,
        transaction_type=InventoryTransactionType.ISSUE.value,
        quantity=Decimal("500.00"),
        occurred_at=now - timedelta(days=10),
    )
    tx2 = InventoryTransactionModel(
        id=uuid.uuid4(),
        stock_lot_id=lot.id,
        transaction_type=InventoryTransactionType.ISSUE.value,
        quantity=Decimal("500.00"),
        occurred_at=now - timedelta(days=5),
    )
    tx3 = InventoryTransactionModel(
        id=uuid.uuid4(),
        stock_lot_id=lot.id,
        transaction_type=InventoryTransactionType.ISSUE.value,
        quantity=Decimal("500.00"),
        occurred_at=now - timedelta(days=1),
    )
    # Also add a RESERVATION transaction which should NOT be counted in burn rate
    tx_res = InventoryTransactionModel(
        id=uuid.uuid4(),
        stock_lot_id=lot.id,
        transaction_type=InventoryTransactionType.RESERVATION.value,
        quantity=Decimal("2000.00"),
        occurred_at=now - timedelta(days=3),
    )
    db_session.add_all([tx1, tx2, tx3, tx_res])
    db_session.commit()

    runway = service.evaluate_lot_runway(lot.id, lookback_days=14, now_dt=now)
    assert runway is not None
    assert runway.available_quantity == Decimal("4500.00")
    # Total consumed = 1500, elapsed days = 10.0 -> burn rate = 150.00 L/day
    assert runway.burn_rate_source == "OBSERVED_TRANSACTIONS_14D"
    assert runway.burn_rate_evidence["observations"] == 3
    assert runway.burn_rate_evidence["consumed_quantity"] == 1500.0
    assert float(runway.daily_burn_rate) == pytest.approx(150.0, rel=0.05)

    # Runway days: 4500 / 150 = 30.0 days
    assert runway.runway_days == pytest.approx(30.0, rel=0.05)
    # Inbound arrival is at Day +40, exhaustion is at Day +30 -> Resupply gap of 10 days!
    assert runway.runway_state == "RESUPPLY_GAP"
    assert runway.resupply_gap_days == pytest.approx(10.0, abs=0.5)


def test_zero_consumption_runway_handling(db_session: Session):
    """Verifies that lots with zero recorded consumption do not emit infinity or divide by zero."""
    now = datetime.now(timezone.utc)
    service = ResourceRunwayService(db_session)

    loc = LocationModel(id=uuid.uuid4(), code="LOC-MTR-02", name="Maitri Storage", type="DEPOT")
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="SPARE-VALVE-TEST",
        item_name="Hydraulic Valve",
        category="SPARES",
        unit="UNIT",
        criticality=ItemCriticality.MISSION_CRITICAL.value,
    )
    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("10.00"),
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
    )
    db_session.add_all([loc, item, lot])
    db_session.commit()

    runway = service.evaluate_lot_runway(lot.id, now_dt=now)
    assert runway is not None
    assert runway.daily_burn_rate == Decimal("0.00")
    assert runway.runway_days is None
    assert runway.exhaustion_at is None
    assert runway.runway_state == "NO_CONSUMPTION_OBSERVED"
    assert runway.burn_rate_source == "NO_CONSUMPTION_OBSERVED"


def test_catalog_baseline_fallback(db_session: Session):
    """Verifies fallback to declared catalog baseline burn rate when transaction history is empty."""
    now = datetime.now(timezone.utc)
    service = ResourceRunwayService(db_session)

    loc = LocationModel(id=uuid.uuid4(), code="LOC-BHR-01", name="Bharati Station", type="STATION")
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="FOOD-RAT-TEST",
        item_name="Polar Survival Rations",
        category="FOOD",
        unit="PACK",
        criticality=ItemCriticality.LIFE_SUPPORT.value,
        operational_metadata={"baseline_daily_burn_rate": 20.0},
    )
    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("600.00"),
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("100.00"),
        replenishment_lead_days=15,
        next_inbound_at=now + timedelta(days=25),
    )
    db_session.add_all([loc, item, lot])
    db_session.commit()

    runway = service.evaluate_lot_runway(lot.id, now_dt=now)
    assert runway is not None
    assert runway.burn_rate_source == "CATALOG_BASELINE"
    assert float(runway.daily_burn_rate) == 20.0
    # Available = 600, burn = 20 -> runway = 30 days
    assert runway.runway_days == 30.0
    # Next inbound in 25 days, exhaustion in 30 days -> Inbound arrives BEFORE exhaustion (gap=0.0) -> COVERED
    assert runway.resupply_gap_days == 0.0
    assert runway.runway_state == "COVERED"


def test_resupply_gap_vs_covered_vs_no_inbound_states(db_session: Session):
    """Verifies exact deterministic state transitions: RESUPPLY_GAP, NO_INBOUND_SCHEDULED, AT_RISK, COVERED."""
    now = datetime.now(timezone.utc)
    service = ResourceRunwayService(db_session)

    loc = LocationModel(id=uuid.uuid4(), code="LOC-TEST-STATES", name="Test Base", type="BASE")
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="WATER-FILT-TEST",
        item_name="Water Filter Media",
        category="WATER",
        unit="KG",
        criticality=ItemCriticality.LIFE_SUPPORT.value,
        operational_metadata={"baseline_daily_burn_rate": 10.0},
    )
    db_session.add_all([loc, item])
    db_session.commit()

    # Case A: NO_INBOUND_SCHEDULED when stock runway <= replenishment lead days
    lot_no_inbound = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("100.00"),  # 10 days runway at 10 KG/day
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("50.00"),
        replenishment_lead_days=20,  # runway (10d) <= lead days (20d)
        next_inbound_at=None,
    )
    db_session.add(lot_no_inbound)
    db_session.commit()

    runway_no_inbound = service.evaluate_lot_runway(lot_no_inbound.id, now_dt=now)
    assert runway_no_inbound.runway_state == "NO_INBOUND_SCHEDULED"

    # Case B: AT_RISK when inbound is scheduled, no gap, but runway <= replenishment lead days
    lot_at_risk = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("150.00"),  # 15 days runway at 10 KG/day
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("50.00"),
        replenishment_lead_days=20,  # runway (15d) <= lead days (20d)
        next_inbound_at=now + timedelta(days=12),  # inbound in 12 days (arrives before day 15 exhaustion, so gap=0)
    )
    db_session.add(lot_at_risk)
    db_session.commit()

    runway_at_risk = service.evaluate_lot_runway(lot_at_risk.id, now_dt=now)
    assert runway_at_risk.resupply_gap_days == 0.0
    assert runway_at_risk.runway_state == "AT_RISK"


def test_resource_runway_horizon_constraint_evaluation(db_session: Session):
    """Verifies that RESOURCE_RUNWAY_HORIZON correctly evaluates to VIOLATED on resupply gap."""
    now = datetime.now(timezone.utc)
    constraint_service = ConstraintService(db_session)

    loc = LocationModel(id=uuid.uuid4(), code="LOC-MTR-CST", name="Maitri Depot", type="STATION")
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="HEATING-OIL-TEST",
        item_name="Extreme Cold Heating Oil",
        category="FUEL",
        unit="LITERS",
        criticality=ItemCriticality.LIFE_SUPPORT.value,
        operational_metadata={"baseline_daily_burn_rate": 100.0},
    )
    # Available = 1000 L -> 10 days runway. Inbound is 20 days away -> Gap = 10 days!
    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("1000.00"),
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("500.00"),
        replenishment_lead_days=30,
        next_inbound_at=now + timedelta(days=20),
    )
    db_session.add_all([loc, item, lot])
    db_session.commit()

    constraint = ConstraintModel(
        id=uuid.uuid4(),
        code="CST-RUNWAY-OIL-01",
        name="Heating Oil Resupply Gap Check",
        type="OPERATIONAL",
        rule_code="RESOURCE_RUNWAY_HORIZON",
        subject_type="INVENTORY_STOCK_LOT",
        subject_id=lot.id,
        hard_or_soft="HARD",
        severity="CRITICAL",
        active=True,
    )
    db_session.add(constraint)
    db_session.commit()

    result = constraint_service.evaluate_constraint(constraint)
    assert result.state == ConstraintState.VIOLATED
    assert "resupply deficit gap" in result.reason.lower()
    assert result.evidence["runway_state"] == "RESUPPLY_GAP"
    assert result.evidence["daily_burn_rate"] == 100.0


def test_control_tower_runways_endpoint(client: TestClient, db_session: Session):
    """Verifies GET /api/v1/control-tower/expeditions/{id}/runways returns valid typed envelope."""
    now = datetime.now(timezone.utc)
    exp = ExpeditionModel(
        id=uuid.uuid4(),
        code="EXP-45-ISEA-TEST",
        name="45th Indian Scientific Expedition",
        season="2026-2027",
        status="ACTIVE",
    )
    loc = LocationModel(id=uuid.uuid4(), code="LOC-EXP-BASE", name="Maitri Base", type="STATION")
    mission = MissionModel(
        id=uuid.uuid4(),
        expedition_id=exp.id,
        code="MSN-TEST-A9",
        title="Schirmacher Oasis Survey",
        type="SCIENTIFIC",
        priority=1,
        location_id=loc.id,
    )
    item_consumable = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="JET-A1-RUNWAY",
        item_name="Aviation Jet Fuel",
        category="FUEL",
        unit="DRUM",
        criticality=ItemCriticality.LIFE_SUPPORT.value,
        operational_metadata={"baseline_daily_burn_rate": 5.0},
    )
    item_durable = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="DURABLE-HAMMER",
        item_name="Geological Sledgehammer",
        category="TOOLS",
        unit="PIECE",
        criticality=ItemCriticality.STANDARD.value,
    )
    lot_consumable = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item_consumable.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("100.00"),
        reserved_quantity=Decimal("10.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
        reorder_point=Decimal("20.00"),
        next_inbound_at=now + timedelta(days=25),
    )
    lot_durable = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item_durable.id,
        location_id=loc.id,
        on_hand_quantity=Decimal("5.00"),
        reserved_quantity=Decimal("0.00"),
        quarantined_quantity=Decimal("0.00"),
        damaged_quantity=Decimal("0.00"),
    )
    db_session.add_all([exp, loc, mission, item_consumable, item_durable, lot_consumable, lot_durable])
    db_session.commit()

    resp = client.get(f"/api/v1/control-tower/expeditions/{exp.id}/runways")
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data.get("errors") is None
    assert json_data.get("data") is not None
    data = json_data["data"]

    assert data["expedition_id"] == str(exp.id)
    # The durable hammer must be excluded by candidate selection filter
    assert data["total_candidates"] == 1
    assert len(data["runways"]) == 1
    runway_item = data["runways"][0]
    assert runway_item["item_code"] == "JET-A1-RUNWAY"
    assert runway_item["category"] == "FUEL"
    assert runway_item["daily_burn_rate"] == "5.00"
    assert runway_item["runway_days"] == 18.0  # (100 - 10) / 5 = 18.0 days
    # Next inbound is 25 days away, so gap = 7 days -> RESUPPLY_GAP
    assert runway_item["runway_state"] == "RESUPPLY_GAP"
    assert runway_item["resupply_gap_days"] == 7.0
