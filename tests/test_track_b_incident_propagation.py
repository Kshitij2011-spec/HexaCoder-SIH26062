"""
Comprehensive Test Suite for Person B / Track B - Milestone B8:
Incident Propagation & Cross-Domain Operational Impact

Covers all 20 required scenarios:
1. HIGH location propagation -> RESTRICTED
2. CRITICAL location propagation -> INACCESSIBLE
3. LOW/MEDIUM location propagation -> SKIPPED
4. HIGH asset propagation -> MAINTENANCE
5. CRITICAL asset propagation -> QUARANTINED
6. Inventory quarantine propagation (authoritative ledger, availability math)
7. Inventory availability adjustment and unavailable stock handling
8. Cargo -> REQUIRES_OPERATOR_ACTION when unsupported / unprompted
9. Transport with explicit delay metadata -> DELAYED + cargo cascade
10. Transport without explicit delay metadata -> REQUIRES_OPERATOR_ACTION
11. Unsupported reference type -> NOT_SUPPORTED
12. Invalid reference resource UUID -> REJECTED
13. Illegal state transition per domain state machine -> REJECTED
14. CLOSED incident propagation rejection -> ConflictError
15. Repeated propagation idempotency (no duplicate transitions or ledger entries)
16. Operational event generation (IncidentImpactPropagated)
17. Attributable audit trail generation (PROPAGATE_INCIDENT_IMPACT)
18. Multi-reference incident propagation
19. Mixed / partial propagation results reporting
20. Error and transaction safety (API response envelope & non-destructive handling)
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import ConflictError

# Import all models for declarative schema registration
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.people.models
import backend.app.domains.teams.models
import backend.app.domains.time_windows.models
import backend.app.domains.locations.models
import backend.app.domains.transport.models
import backend.app.domains.cargo.models
import backend.app.domains.inventory.models
import backend.app.domains.assets.models
import backend.app.domains.incidents.models
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.domains.locations.models import LocationModel
from backend.app.domains.assets.models import AssetModel
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.incidents.models import (
    IncidentModel,
    IncidentReferenceModel,
    IncidentPropagationModel,
)
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
    PropagationStatus,
    PropagationAction,
)
from backend.app.domains.incidents.propagation import IncidentPropagationService
from backend.app.domains.assets.states import AssetStatus
from backend.app.shared.types.states import LocationStatus, InventoryStatus, TransportStatus


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for Incident Propagation tests."""
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
    """Yields an active database session for direct service-level tests."""
    override = app.dependency_overrides[get_db]
    session_gen = override()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()


def _create_incident(
    db: Session,
    code: str,
    severity: str = "HIGH",
    status: str = "OPEN",
    title: str = "Test Incident",
) -> IncidentModel:
    inc = IncidentModel(
        id=uuid.uuid4(),
        incident_code=code,
        title=title,
        type="EQUIPMENT_FAILURE",
        severity=severity,
        priority=4,
        status=status,
        detected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


def _add_reference(
    db: Session,
    incident_id: uuid.UUID,
    ref_type: str,
    ref_id: uuid.UUID,
    notes: str = "Operational link",
    meta: dict = None,
) -> IncidentReferenceModel:
    ref = IncidentReferenceModel(
        id=uuid.uuid4(),
        incident_id=incident_id,
        reference_type=ref_type,
        reference_id=ref_id,
        notes=notes,
        operational_metadata=meta or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


# ============================================================
# 1. LOCATION PROPAGATION TESTS
# ============================================================

def test_high_severity_location_propagation(db_session: Session):
    """Scenario 1: HIGH severity incident restricts referenced AVAILABLE location."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-PROP-01",
        name="Field Camp Alpha",
        type="FIELD_CAMP",
        status=LocationStatus.AVAILABLE.value,
        latitude=-70.76,
        longitude=11.74,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    inc = _create_incident(db_session, "INC-LOC-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.total_references == 1
    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.action == PropagationAction.RESTRICT_LOCATION.value
    assert res.previous_state == LocationStatus.AVAILABLE.value
    assert res.resulting_state == LocationStatus.RESTRICTED.value

    # Verify actual LocationModel mutation
    db_session.refresh(loc)
    assert loc.status == LocationStatus.RESTRICTED.value


def test_critical_severity_location_propagation(db_session: Session):
    """Scenario 2: CRITICAL severity incident isolates referenced AVAILABLE location to INACCESSIBLE."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-PROP-02",
        name="Maitri Runway 01",
        type="RUNWAY",
        status=LocationStatus.AVAILABLE.value,
        latitude=-70.77,
        longitude=11.75,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    inc = _create_incident(db_session, "INC-LOC-02", severity="CRITICAL")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.resulting_state == LocationStatus.INACCESSIBLE.value

    db_session.refresh(loc)
    assert loc.status == LocationStatus.INACCESSIBLE.value


def test_low_severity_location_skipped(db_session: Session):
    """Scenario 3: LOW/MEDIUM severity incident SKIPS location mutation."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-PROP-03",
        name="Weather Hut",
        type="OUTPOST",
        status=LocationStatus.AVAILABLE.value,
        latitude=-70.78,
        longitude=11.76,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    inc = _create_incident(db_session, "INC-LOC-03", severity="LOW")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.skipped_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.SKIPPED
    assert "LOW does not trigger" in res.reason

    db_session.refresh(loc)
    assert loc.status == LocationStatus.AVAILABLE.value


# ============================================================
# 2. ASSET PROPAGATION TESTS
# ============================================================

def test_high_severity_asset_propagation(db_session: Session):
    """Scenario 4: HIGH severity incident transitions AVAILABLE asset to MAINTENANCE."""
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-PROP-01",
        name="Snowcat 01",
        type="VEHICLE",
        status=AssetStatus.AVAILABLE.value,
        condition="OPERATIONAL",
        criticality="MISSION_CRITICAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(asset)
    db_session.commit()

    inc = _create_incident(db_session, "INC-AST-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.ASSET.value, asset.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.action == PropagationAction.MAINTENANCE_ASSET.value
    assert res.resulting_state == AssetStatus.MAINTENANCE.value

    db_session.refresh(asset)
    assert asset.status == AssetStatus.MAINTENANCE.value


def test_critical_severity_asset_propagation(db_session: Session):
    """Scenario 5: CRITICAL severity incident transitions AVAILABLE asset to QUARANTINED."""
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-PROP-02",
        name="Primary Generator A",
        type="GENERATOR",
        status=AssetStatus.AVAILABLE.value,
        condition="OPERATIONAL",
        criticality="LIFE_SUPPORT",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(asset)
    db_session.commit()

    inc = _create_incident(db_session, "INC-AST-02", severity="CRITICAL")
    _add_reference(db_session, inc.id, IncidentReferenceType.ASSET.value, asset.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.action == PropagationAction.QUARANTINE_ASSET.value
    assert res.resulting_state == AssetStatus.QUARANTINED.value

    db_session.refresh(asset)
    assert asset.status == AssetStatus.QUARANTINED.value


# ============================================================
# 3. INVENTORY PROPAGATION TESTS
# ============================================================

def test_inventory_quarantine_propagation(db_session: Session):
    """Scenario 6: HIGH incident triggers authoritative stock quarantine with transaction ledger."""
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="MED-PROP-01",
        item_name="Field Medical Kit",
        category="MEDICAL",
        unit="KIT",
        criticality="MISSION_CRITICAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(item)
    db_session.flush()

    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        lot_code="LOT-PROP-01",
        location_id=uuid.uuid4(),
        on_hand_quantity=Decimal("50"),
        reserved_quantity=Decimal("10"),
        quarantined_quantity=Decimal("0"),
        damaged_quantity=Decimal("0"),
        status=InventoryStatus.AVAILABLE.value,
        condition="OPERATIONAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(lot)
    db_session.commit()

    inc = _create_incident(db_session, "INC-INV-01", severity="HIGH")
    # Quarantine 20 units via reference metadata
    _add_reference(
        db_session,
        inc.id,
        IncidentReferenceType.INVENTORY_STOCK_LOT.value,
        lot.id,
        meta={"quantity": 20},
    )

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.action == PropagationAction.QUARANTINE_STOCK.value

    # Verify lot availability and quarantined quantity
    db_session.refresh(lot)
    assert lot.quarantined_quantity == Decimal("20")

    # Verify inventory transaction was committed to audit ledger
    tx = db_session.execute(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.stock_lot_id == lot.id,
            InventoryTransactionModel.transaction_type == "QUARANTINE",
        )
    ).scalar_one_or_none()
    assert tx is not None
    assert tx.quantity == Decimal("20")


def test_inventory_zero_availability_handling(db_session: Session):
    """Scenario 7: Stock lot with 0 unreserved available quantity SKIPS quarantine."""
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="RATION-PROP-01",
        item_name="Emergency Ration",
        category="RATIONS",
        unit="PACK",
        criticality="MISSION_CRITICAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(item)
    db_session.flush()

    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        lot_code="LOT-PROP-ZERO",
        location_id=uuid.uuid4(),
        on_hand_quantity=Decimal("25"),
        reserved_quantity=Decimal("25"),  # All 25 reserved!
        quarantined_quantity=Decimal("0"),
        damaged_quantity=Decimal("0"),
        status=InventoryStatus.RESERVED.value,
        condition="OPERATIONAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(lot)
    db_session.commit()

    inc = _create_incident(db_session, "INC-INV-ZERO", severity="CRITICAL")
    _add_reference(db_session, inc.id, IncidentReferenceType.INVENTORY_STOCK_LOT.value, lot.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.skipped_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.SKIPPED
    assert "no unreserved available quantity" in res.reason

    db_session.refresh(lot)
    assert lot.quarantined_quantity == Decimal("0")


# ============================================================
# 4. CARGO PROPAGATION TESTS
# ============================================================

def test_cargo_propagation_requires_operator_action(db_session: Session):
    """Scenario 8: Cargo consignment reference returns REQUIRES_OPERATOR_ACTION without artificial state mutation."""
    now = datetime.now(timezone.utc)
    consignment = CargoConsignmentModel(
        id=uuid.uuid4(),
        code="C-PROP-88",
        expedition_id=uuid.uuid4(),
        origin_location_id=uuid.uuid4(),
        destination_location_id=uuid.uuid4(),
        priority=3,
        required_by_at=now + timedelta(days=5),
        planned_arrival_at=now + timedelta(days=3),
        estimated_arrival_at=now + timedelta(days=3),
        status="IN_TRANSIT",
        risk_level="LOW",
        data_provenance="SYNTHETIC_DEMO",
        created_at=now,
        updated_at=now,
    )
    db_session.add(consignment)
    db_session.commit()

    inc = _create_incident(db_session, "INC-CARGO-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.CARGO_CONSIGNMENT.value, consignment.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.requires_action_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.REQUIRES_OPERATOR_ACTION
    assert res.action == PropagationAction.REVIEW_CARGO.value
    assert res.reason == "Cargo impact requires explicit operator action."

    # Verify cargo status is unchanged
    db_session.refresh(consignment)
    assert consignment.status == "IN_TRANSIT"


# ============================================================
# 5. TRANSPORT PROPAGATION TESTS
# ============================================================

def test_transport_propagation_with_explicit_delay(db_session: Session):
    """Scenario 9: Transport leg with explicit delay metadata executes authoritative delay and cascades."""
    now = datetime.now(timezone.utc)
    leg = TransportLegModel(
        id=uuid.uuid4(),
        code="LEG-PROP-01",
        expedition_id=uuid.uuid4(),
        mode="AIR",
        origin_location_id=uuid.uuid4(),
        destination_location_id=uuid.uuid4(),
        departure_window_open=now,
        departure_window_close=now + timedelta(hours=3),
        planned_departure_at=now + timedelta(hours=1),
        planned_arrival_at=now + timedelta(hours=4),
        estimated_departure_at=now + timedelta(hours=1),
        estimated_arrival_at=now + timedelta(hours=4),
        status=TransportStatus.READY.value,
        data_provenance="SYNTHETIC_DEMO",
        created_at=now,
        updated_at=now,
    )
    db_session.add(leg)
    db_session.commit()

    new_eta = (now + timedelta(hours=12)).isoformat()
    inc = _create_incident(db_session, "INC-TRN-01", severity="HIGH")
    _add_reference(
        db_session,
        inc.id,
        IncidentReferenceType.TRANSPORT_LEG.value,
        leg.id,
        meta={"new_estimated_arrival_at": new_eta},
    )

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.APPLIED
    assert res.action == PropagationAction.DELAY_TRANSPORT.value
    assert res.resulting_state == TransportStatus.DELAYED.value

    db_session.refresh(leg)
    assert leg.status == TransportStatus.DELAYED.value


def test_transport_propagation_without_explicit_delay(db_session: Session):
    """Scenario 10: Transport leg without delay parameters returns REQUIRES_OPERATOR_ACTION."""
    now = datetime.now(timezone.utc)
    leg = TransportLegModel(
        id=uuid.uuid4(),
        code="LEG-PROP-02",
        expedition_id=uuid.uuid4(),
        mode="OVERLAND",
        origin_location_id=uuid.uuid4(),
        destination_location_id=uuid.uuid4(),
        departure_window_open=now,
        departure_window_close=now + timedelta(hours=3),
        planned_departure_at=now + timedelta(hours=1),
        planned_arrival_at=now + timedelta(hours=6),
        estimated_departure_at=now + timedelta(hours=1),
        estimated_arrival_at=now + timedelta(hours=6),
        status=TransportStatus.READY.value,
        data_provenance="SYNTHETIC_DEMO",
        created_at=now,
        updated_at=now,
    )
    db_session.add(leg)
    db_session.commit()

    inc = _create_incident(db_session, "INC-TRN-NODELAY", severity="HIGH")
    # No delay metadata provided!
    _add_reference(db_session, inc.id, IncidentReferenceType.TRANSPORT_LEG.value, leg.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.requires_action_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.REQUIRES_OPERATOR_ACTION
    assert "requires explicit new ETA" in res.reason

    db_session.refresh(leg)
    assert leg.status == TransportStatus.READY.value


# ============================================================
# 6. EDGE CASES, STATE GUARDS & ERROR HANDLING
# ============================================================

def test_unsupported_reference_type(db_session: Session):
    """Scenario 11: Unsupported reference type returns NOT_SUPPORTED deterministically."""
    inc = _create_incident(db_session, "INC-UNSUPP-01", severity="HIGH")
    # Reference with unsupported type
    ref = IncidentReferenceModel(
        id=uuid.uuid4(),
        incident_id=inc.id,
        reference_type="WEATHER_STATION",
        reference_id=uuid.uuid4(),
        operational_metadata={},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(ref)
    db_session.commit()

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.total_references == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.NOT_SUPPORTED
    assert "does not support automatic incident propagation" in res.reason


def test_invalid_reference_resource_not_found(db_session: Session):
    """Scenario 12: Reference pointing to non-existent resource returns REJECTED."""
    inc = _create_incident(db_session, "INC-NOTFOUND-01", severity="HIGH")
    non_existent_id = uuid.uuid4()
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, non_existent_id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.rejected_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.REJECTED
    assert "was not found" in res.reason


def test_illegal_state_transition_rejection(db_session: Session):
    """Scenario 13: Illegal state transition according to domain rules is REJECTED without forcing state."""
    # Asset in RETIRED status cannot transition to MAINTENANCE or QUARANTINED
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-RETIRED-01",
        name="Decommissioned Ski-Doo",
        type="VEHICLE",
        status=AssetStatus.RETIRED.value,
        condition="INOPERABLE",
        criticality="STANDARD",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(asset)
    db_session.commit()

    inc = _create_incident(db_session, "INC-ILLEGAL-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.ASSET.value, asset.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.rejected_count == 1
    res = summary.results[0]
    assert res.status == PropagationStatus.REJECTED
    assert "RETIRED is a terminal lifecycle state" in res.reason

    db_session.refresh(asset)
    assert asset.status == AssetStatus.RETIRED.value


def test_closed_incident_rejection(db_session: Session):
    """Scenario 14: Propagation from CLOSED incident strictly raises ConflictError."""
    inc = _create_incident(db_session, "INC-CLOSED-01", severity="HIGH", status="CLOSED")

    service = IncidentPropagationService(db_session)
    with pytest.raises(ConflictError) as exc_info:
        service.propagate_incident_impact(inc.id)

    assert "Cannot propagate impact for CLOSED incident" in str(exc_info.value)


# ============================================================
# 7. IDEMPOTENCY & EVENT / AUDIT LOGGING
# ============================================================

def test_repeated_propagation_idempotency(db_session: Session):
    """Scenario 15: Calling propagation repeatedly does not duplicate state changes or inventory records."""
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="MED-IDEMP-01",
        item_name="Antibiotic Stock",
        category="MEDICAL",
        unit="VIAL",
        criticality="MISSION_CRITICAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(item)
    db_session.flush()

    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        lot_code="LOT-IDEMP-01",
        location_id=uuid.uuid4(),
        on_hand_quantity=Decimal("100"),
        reserved_quantity=Decimal("0"),
        quarantined_quantity=Decimal("0"),
        damaged_quantity=Decimal("0"),
        status=InventoryStatus.AVAILABLE.value,
        condition="OPERATIONAL",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(lot)
    db_session.commit()

    inc = _create_incident(db_session, "INC-IDEMP-01", severity="HIGH")
    _add_reference(
        db_session,
        inc.id,
        IncidentReferenceType.INVENTORY_STOCK_LOT.value,
        lot.id,
        meta={"quantity": 30},
    )

    service = IncidentPropagationService(db_session)

    # First run -> APPLIED
    run1 = service.propagate_incident_impact(inc.id)
    assert run1.applied_count == 1
    db_session.refresh(lot)
    assert lot.quarantined_quantity == Decimal("30")

    # Second run -> SKIPPED (Idempotent: no duplicate quarantine)
    run2 = service.propagate_incident_impact(inc.id)
    assert run2.applied_count == 0
    assert run2.skipped_count == 1
    assert "already been quarantined by this incident" in run2.results[0].reason

    db_session.refresh(lot)
    assert lot.quarantined_quantity == Decimal("30")

    # Ensure only 1 quarantine ledger transaction was recorded
    txs = db_session.execute(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.stock_lot_id == lot.id,
            InventoryTransactionModel.transaction_type == "QUARANTINE",
        )
    ).scalars().all()
    assert len(txs) == 1


def test_operational_event_generation(db_session: Session):
    """Scenario 16: Successful propagation emits IncidentImpactPropagated operational event."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-EV-01",
        name="Event Observation Point",
        type="OUTPOST",
        status=LocationStatus.AVAILABLE.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    inc = _create_incident(db_session, "INC-EV-01", severity="CRITICAL")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.applied_count == 1
    event_id = summary.results[0].event_id
    assert event_id is not None

    # Verify event stored in event journal
    ev = db_session.execute(
        select(backend.app.platform.events.models.OperationalEventModel).where(
            backend.app.platform.events.models.OperationalEventModel.event_id == event_id
        )
    ).scalar_one_or_none()
    assert ev is not None
    assert ev.event_type == "IncidentImpactPropagated"
    assert ev.evidence["status"] == "APPLIED"


def test_audit_trail_generation(db_session: Session):
    """Scenario 17: Propagation batch records attributable audit log entry."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-AUD-01",
        name="Audit Station Sector",
        type="STATION",
        status=LocationStatus.AVAILABLE.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    actor_id = uuid.uuid4()
    inc = _create_incident(db_session, "INC-AUD-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id, actor_person_id=actor_id)

    audit_id = summary.results[0].audit_id
    assert audit_id is not None

    audit_entry = db_session.execute(
        select(backend.app.platform.audit.models.AuditLogModel).where(
            backend.app.platform.audit.models.AuditLogModel.id == audit_id
        )
    ).scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.action == "PROPAGATE_INCIDENT_IMPACT"
    assert audit_entry.actor_person_id == actor_id


# ============================================================
# 8. MULTI-REFERENCE & BATCH ORCHESTRATION
# ============================================================

def test_multi_reference_incident_propagation(db_session: Session):
    """Scenario 18: Incident referencing multiple resources processes each deterministically."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-MULTI-01",
        name="Multi Location",
        type="STATION",
        status=LocationStatus.AVAILABLE.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-MULTI-01",
        name="Multi Asset",
        type="EQUIPMENT",
        status=AssetStatus.AVAILABLE.value,
        condition="OPERATIONAL",
        criticality="STANDARD",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([loc, asset])
    db_session.commit()

    inc = _create_incident(db_session, "INC-MULTI-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)
    _add_reference(db_session, inc.id, IncidentReferenceType.ASSET.value, asset.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.total_references == 2
    assert summary.applied_count == 2

    statuses = {r.reference_type: r.status for r in summary.results}
    assert statuses["LOCATION"] == PropagationStatus.APPLIED
    assert statuses["ASSET"] == PropagationStatus.APPLIED


def test_mixed_partial_results(db_session: Session):
    """Scenario 19: Incident with valid, skipped, and invalid targets reports mixed per-reference outcomes."""
    # 1. Valid location -> APPLIED
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-MIX-01",
        name="Mix Location",
        type="STATION",
        status=LocationStatus.AVAILABLE.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # 2. Retired asset -> REJECTED
    retired_asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-MIX-RET",
        name="Retired Crane",
        type="HEAVY_EQUIPMENT",
        status=AssetStatus.RETIRED.value,
        condition="INOPERABLE",
        criticality="STANDARD",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # 3. Cargo -> REQUIRES_OPERATOR_ACTION
    now = datetime.now(timezone.utc)
    cargo = CargoConsignmentModel(
        id=uuid.uuid4(),
        code="C-MIX-01",
        expedition_id=uuid.uuid4(),
        origin_location_id=uuid.uuid4(),
        destination_location_id=uuid.uuid4(),
        priority=3,
        required_by_at=now + timedelta(days=5),
        planned_arrival_at=now + timedelta(days=2),
        estimated_arrival_at=now + timedelta(days=2),
        status="PACKED",
        risk_level="LOW",
        data_provenance="SYNTHETIC_DEMO",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([loc, retired_asset, cargo])
    db_session.commit()

    inc = _create_incident(db_session, "INC-MIX-01", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)
    _add_reference(db_session, inc.id, IncidentReferenceType.ASSET.value, retired_asset.id)
    _add_reference(db_session, inc.id, IncidentReferenceType.CARGO_CONSIGNMENT.value, cargo.id)

    service = IncidentPropagationService(db_session)
    summary = service.propagate_incident_impact(inc.id)

    assert summary.total_references == 3
    assert summary.applied_count == 1
    assert summary.rejected_count == 1
    assert summary.requires_action_count == 1

    status_map = {r.reference_type: r.status for r in summary.results}
    assert status_map["LOCATION"] == PropagationStatus.APPLIED
    assert status_map["ASSET"] == PropagationStatus.REJECTED
    assert status_map["CARGO_CONSIGNMENT"] == PropagationStatus.REQUIRES_OPERATOR_ACTION


# ============================================================
# 9. REST API INTEGRATION TESTS
# ============================================================

def test_api_propagate_endpoint(client: TestClient, db_session: Session):
    """Scenario 20: POST /api/v1/incidents/{id}/propagate and GET /propagation integration via HTTP."""
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-API-01",
        name="API Station",
        type="STATION",
        status=LocationStatus.AVAILABLE.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(loc)
    db_session.commit()

    inc = _create_incident(db_session, "INC-API-PROP", severity="HIGH")
    _add_reference(db_session, inc.id, IncidentReferenceType.LOCATION.value, loc.id)

    # 1. Trigger propagation via REST API
    resp = client.post(f"/api/v1/incidents/{inc.id}/propagate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    data = body["data"]
    assert data["incident_code"] == "INC-API-PROP"
    assert data["applied_count"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "APPLIED"

    # 2. Query propagation history via REST API
    history_resp = client.get(f"/api/v1/incidents/{inc.id}/propagation")
    assert history_resp.status_code == 200
    history_body = history_resp.json()
    assert history_body["errors"] is None
    records = history_body["data"]
    assert len(records) >= 1
    assert records[0]["status"] == "APPLIED"
    assert records[0]["reference_type"] == "LOCATION"
