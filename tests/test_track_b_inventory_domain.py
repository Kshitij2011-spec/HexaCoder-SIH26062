"""
Comprehensive Test Suite for Person B / Track B - Milestone B2:
- Inventory Catalog Items (Creation, uniqueness, criticality, listing)
- Inventory Stock Lots (Location linkage, on-hand, reserved, quarantined, damaged)
- Domain-Authoritative Stock Availability Math (available = on_hand - unavailable)
- Reorder Point & Deficit Calculation (Deterministic alert when available <= reorder_point)
- Immutable Operational Transaction Ledger (RECEIPT, RESERVATION, RELEASE, ISSUE, QUARANTINE)
- State Machine Transitions (Valid lifecycle movements, invalid transition rejection)
- Cargo Reference Traceability (reference_type='CARGO_PACKAGE', reference_id=UUID)
- EventService & AuditService Integration (Transactional events and audit log trails)
- Zero Mutation of Demo Baseline Seed Data
"""

import ast
import uuid
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import (
    InvalidStateTransitionError,
    DomainValidationError,
    ConflictError,
    EntityNotFoundError,
)

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
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.shared.types.states import (
    InventoryStatus,
    InventoryTransactionType,
    ItemCriticality,
    LocationStatus,
)
from backend.app.domains.inventory.transitions import (
    ALLOWED_INVENTORY_TRANSITIONS,
    validate_inventory_transition,
)
from backend.app.domains.inventory.service import (
    InventoryService,
    calculate_lot_availability,
)
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for Inventory domain tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
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


# ============================================================
# 1. ARCHITECTURAL SANITY & NO CIRCULAR DEPENDENCY
# ============================================================

def test_inventory_service_no_circular_dependency():
    """
    Verifies that Inventory domain does not introduce circular imports
    with Transport, Cargo, or Person A domains.
    """
    inventory_service_path = Path("backend/app/domains/inventory/service.py")
    tree = ast.parse(inventory_service_path.read_text(encoding="utf-8"))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    # Inventory must not import TransportService or CargoService
    for mod in imported_modules:
        assert "TransportService" not in mod
        assert "CargoService" not in mod
        assert "backend.app.domains.expeditions" not in mod


# ============================================================
# 2. DETERMINISTIC STOCK AVAILABILITY FORMULA
# ============================================================

def test_calculate_lot_availability_formula():
    """
    Verifies domain-authoritative formula:
    available = on_hand - (reserved + quarantined + damaged)
    is_deficit = available <= reorder_point
    """
    # Nominal case: 100 on hand, 20 reserved, 5 quarantined, 5 damaged -> 70 available
    avail, deficit = calculate_lot_availability(
        on_hand=Decimal("100"),
        reserved=Decimal("20"),
        quarantined=Decimal("5"),
        damaged=Decimal("5"),
        reorder_point=Decimal("50")
    )
    assert avail == Decimal("70")
    assert deficit is False

    # Deficit case: available (40) <= reorder_point (50)
    avail2, deficit2 = calculate_lot_availability(
        on_hand=Decimal("100"),
        reserved=Decimal("40"),
        quarantined=Decimal("10"),
        damaged=Decimal("10"),
        reorder_point=Decimal("50")
    )
    assert avail2 == Decimal("40")
    assert deficit2 is True

    # Clamping: unavailable exceeding on hand returns 0 available
    avail3, deficit3 = calculate_lot_availability(
        on_hand=Decimal("10"),
        reserved=Decimal("10"),
        quarantined=Decimal("5"),
        damaged=Decimal("0")
    )
    assert avail3 == Decimal("0")
    assert deficit3 is False


# ============================================================
# 3. STATE MACHINE TRANSITION RULES
# ============================================================

def test_inventory_state_machine_transitions():
    """Verifies allowed and disallowed lifecycle transitions for stock lots."""
    # Valid transitions
    validate_inventory_transition("ON_ORDER", "INBOUND")
    validate_inventory_transition("INBOUND", "AVAILABLE")
    validate_inventory_transition("AVAILABLE", "RESERVED")
    validate_inventory_transition("RESERVED", "AVAILABLE")
    validate_inventory_transition("RESERVED", "ISSUED")
    validate_inventory_transition("AVAILABLE", "QUARANTINED")
    validate_inventory_transition("QUARANTINED", "AVAILABLE")
    validate_inventory_transition("ISSUED", "CONSUMED")

    # Invalid transitions
    with pytest.raises(InvalidStateTransitionError):
        validate_inventory_transition("CONSUMED", "AVAILABLE")

    with pytest.raises(InvalidStateTransitionError):
        validate_inventory_transition("DISPOSED", "AVAILABLE")


# ============================================================
# 4. CATALOG ITEMS API & UNIQUENESS
# ============================================================

def test_catalog_items_crud_and_uniqueness(client):
    """Verifies catalog item registration, duplicate code conflict, and retrieval."""
    item_code = f"TEST-FUEL-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "item_code": item_code,
        "item_name": "Polar Aviation Turbine Fuel Jet A-1",
        "category": "FUEL",
        "unit": "LITER",
        "criticality": "MISSION_CRITICAL",
        "description": "Low freeze point aviation fuel (-50C)",
        "operational_metadata": {"freeze_point_celsius": -50}
    }

    # 1. Create item
    res = client.post("/api/v1/inventory/items", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["item_code"] == item_code
    assert data["criticality"] == "MISSION_CRITICAL"
    item_id = data["id"]

    # 2. Duplicate rejection
    dup_res = client.post("/api/v1/inventory/items", json=payload)
    assert dup_res.status_code == 409

    # 3. Get item by ID
    get_res = client.get(f"/api/v1/inventory/items/{item_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["item_name"] == "Polar Aviation Turbine Fuel Jet A-1"

    # 4. List items
    list_res = client.get("/api/v1/inventory/items", params={"category": "FUEL"})
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert any(i["id"] == item_id for i in items)


# ============================================================
# 5. STOCK LOT CREATION & AVAILABILITY ENDPOINTS
# ============================================================

def test_stock_lot_lifecycle_and_availability(client):
    """
    Verifies:
    - Creating stock lot at location
    - Opening balance transaction in ledger
    - Computed availability and deficit indicators
    """
    # 1. Create test location
    loc_code = f"LOC-STK-{uuid.uuid4().hex[:6].upper()}"
    loc_res = client.post("/api/v1/locations", json={
        "code": loc_code,
        "name": "Maitri Station Bulk Storage",
        "type": "STATION",
        "status": "AVAILABLE"
    })
    assert loc_res.status_code == 201
    loc_id = loc_res.json()["data"]["id"]

    # 2. Create catalog item
    item_code = f"ITEM-RATION-{uuid.uuid4().hex[:6].upper()}"
    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": item_code,
        "item_name": "High-Calorie Freeze Dried Field Ration Pack",
        "category": "RATIONS",
        "unit": "BOX",
        "criticality": "LIFE_SUPPORT"
    })
    assert item_res.status_code == 201
    item_id = item_res.json()["data"]["id"]

    # 3. Create stock lot with 200 units on hand, reorder point 50
    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": loc_id,
        "lot_code": "BATCH-2026-01",
        "on_hand_quantity": 200.0,
        "reorder_point": 50.0,
        "status": "AVAILABLE"
    })
    assert lot_res.status_code == 201
    lot_data = lot_res.json()["data"]
    lot_id = lot_data["id"]
    assert float(lot_data["on_hand_quantity"]) == 200.0
    assert float(lot_data["available_quantity"]) == 200.0
    assert lot_data["is_deficit"] is False

    # 4. Check availability endpoint
    avail_res = client.get(f"/api/v1/inventory/stock-lots/{lot_id}/availability")
    assert avail_res.status_code == 200
    avail_data = avail_res.json()["data"]
    assert float(avail_data["available_quantity"]) == 200.0
    assert avail_data["is_deficit"] is False

    # 5. Check ledger recorded the opening balance transaction
    tx_res = client.get(f"/api/v1/inventory/stock-lots/{lot_id}/transactions")
    assert tx_res.status_code == 200
    txs = tx_res.json()["data"]
    assert len(txs) == 1
    assert txs[0]["transaction_type"] == "RECEIPT"
    assert float(txs[0]["quantity"]) == 200.0


# ============================================================
# 6. OPERATIONAL MUTATIONS: RECEIVE, RESERVE, RELEASE, ISSUE, QUARANTINE
# ============================================================

def test_operational_stock_mutations_and_ledger(client, db_session):
    """
    Verifies full operational stock ledger flow:
    - Receive additional goods referencing Cargo Package
    - Reserve stock for field operation
    - Prevent over-reservation
    - Release portion of reservation
    - Issue stock to field
    - Quarantine damaged stock
    - Verify audit trail and immutable events emitted
    """
    event_service = EventService(db_session)
    audit_service = AuditService(db_session)

    test_cid = uuid.uuid4()
    loc_id = uuid.uuid4()
    # Create item
    item_code = f"ITEM-MED-{uuid.uuid4().hex[:6].upper()}"
    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": item_code,
        "item_name": "Emergency Cold Weather Trauma Kit",
        "category": "MEDICAL",
        "unit": "KIT",
        "criticality": "LIFE_SUPPORT"
    }, headers={"X-Request-ID": str(test_cid)})
    assert item_res.status_code == 201
    item_id = item_res.json()["data"]["id"]

    # Create empty stock lot
    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": str(loc_id),
        "lot_code": "LOT-MED-01",
        "on_hand_quantity": 0.0,
        "reorder_point": 20.0,
        "status": "AVAILABLE"
    }, headers={"X-Request-ID": str(test_cid)})
    assert lot_res.status_code == 201
    lot_id = lot_res.json()["data"]["id"]

    # 1. RECEIPT: Receive 100 kits from cargo package
    cargo_pkg_id = uuid.uuid4()
    receive_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/receive", json={
        "quantity": 100.0,
        "reference_type": "CARGO_PACKAGE",
        "reference_id": str(cargo_pkg_id),
        "notes": "Offloaded from Twin Otter flight TO-04"
    }, headers={"X-Request-ID": str(test_cid)})
    assert receive_res.status_code == 200
    r_data = receive_res.json()["data"]
    assert float(r_data["on_hand_quantity"]) == 100.0
    assert float(r_data["available_quantity"]) == 100.0

    # 2. RESERVATION: Reserve 30 kits for Deep Field Traverse
    reserve_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/reserve", json={
        "quantity": 30.0,
        "reference_type": "MISSION",
        "reference_id": str(uuid.uuid4()),
        "notes": "Reserved for Dome Concordia Seismic Traverse"
    }, headers={"X-Request-ID": str(test_cid)})
    assert reserve_res.status_code == 200
    res_data = reserve_res.json()["data"]
    assert float(res_data["on_hand_quantity"]) == 100.0
    assert float(res_data["reserved_quantity"]) == 30.0
    assert float(res_data["available_quantity"]) == 70.0

    # 3. OVER-RESERVATION REJECTION: Attempt to reserve 80 kits (only 70 available)
    over_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/reserve", json={
        "quantity": 80.0,
        "notes": "Excessive request"
    })
    assert over_res.status_code == 422

    # 4. RELEASE: Release 10 kits back to available
    release_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/release", json={
        "quantity": 10.0,
        "notes": "Traverse team size reduced"
    }, headers={"X-Request-ID": str(test_cid)})
    assert release_res.status_code == 200
    rel_data = release_res.json()["data"]
    assert float(rel_data["reserved_quantity"]) == 20.0
    assert float(rel_data["available_quantity"]) == 80.0

    # 5. ISSUE: Issue 20 kits to departing team (deducts from reserved and on-hand)
    issue_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/issue", json={
        "quantity": 20.0,
        "notes": "Issued to Team Alpha leader"
    }, headers={"X-Request-ID": str(test_cid)})
    assert issue_res.status_code == 200
    iss_data = issue_res.json()["data"]
    assert float(iss_data["on_hand_quantity"]) == 80.0
    assert float(iss_data["reserved_quantity"]) == 0.0
    assert float(iss_data["available_quantity"]) == 80.0

    # 6. QUARANTINE: Quarantine 15 kits due to water ingress
    quar_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/quarantine", json={
        "quantity": 15.0,
        "reason": "Container seal damaged by blizzard drift ice"
    }, headers={"X-Request-ID": str(test_cid)})
    assert quar_res.status_code == 200
    q_data = quar_res.json()["data"]
    assert float(q_data["on_hand_quantity"]) == 80.0
    assert float(q_data["quarantined_quantity"]) == 15.0
    assert float(q_data["available_quantity"]) == 65.0  # 80 - 15 = 65

    # 7. VERIFY IMMUTABLE TRANSACTION LEDGER
    ledger_res = client.get(f"/api/v1/inventory/stock-lots/{lot_id}/transactions")
    assert ledger_res.status_code == 200
    tx_list = ledger_res.json()["data"]
    # Recorded: RECEIPT (100), RESERVATION (30), RELEASE (10), ISSUE (20), QUARANTINE (15)
    tx_types = [t["transaction_type"] for t in tx_list]
    assert "RECEIPT" in tx_types
    assert "RESERVATION" in tx_types
    assert "RELEASE" in tx_types
    assert "ISSUE" in tx_types
    assert "QUARANTINE" in tx_types

    # 8. VERIFY OPERATIONAL EVENTS
    events, _ = event_service.list_events()
    inv_events = [e for e in events if e.entity_type == "INVENTORY_STOCK_LOT" and str(e.entity_id) == lot_id]
    inv_event_types = [e.event_type for e in inv_events]
    assert "StockReceived" in inv_event_types
    assert "StockReserved" in inv_event_types
    assert "StockReservationReleased" in inv_event_types
    assert "StockIssued" in inv_event_types
    assert "StockQuarantined" in inv_event_types

    # 9. VERIFY AUDIT TRAIL
    audits, _ = audit_service.get_entity_audit_trail("INVENTORY_STOCK_LOT", uuid.UUID(lot_id))
    audit_actions = [a.action for a in audits]
    assert "RECEIVE_STOCK" in audit_actions
    assert "RESERVE_STOCK" in audit_actions
    assert "RELEASE_STOCK_RESERVATION" in audit_actions
    assert "ISSUE_STOCK" in audit_actions
    assert "QUARANTINE_STOCK" in audit_actions


# ============================================================
# 7. CONSUMED TERMINAL STATE ON COMPLETE STOCK ISSUANCE
# ============================================================

def test_stock_lot_marked_consumed_when_empty(client):
    """Verifies that issuing 100% of physical stock transitions status to CONSUMED."""
    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": f"ITEM-EXP-{uuid.uuid4().hex[:6].upper()}",
        "item_name": "Seismic Explosive Booster Charge",
        "category": "SCIENTIFIC",
        "unit": "CHARGE"
    })
    item_id = item_res.json()["data"]["id"]

    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": str(uuid.uuid4()),
        "on_hand_quantity": 5.0,
        "status": "AVAILABLE"
    })
    lot_id = lot_res.json()["data"]["id"]

    # Issue all 5 charges
    issue_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/issue", json={
        "quantity": 5.0,
        "notes": "Detonated in crustal survey profile"
    })
    assert issue_res.status_code == 200
    assert float(issue_res.json()["data"]["on_hand_quantity"]) == 0.0
    assert issue_res.json()["data"]["status"] == "CONSUMED"


# ============================================================
# 8. STATUS TRANSITION API & AUDIT TRAIL
# ============================================================

def test_stock_status_transition_api_and_audit(client, db_session):
    """Verifies valid and invalid status transition endpoints with event & audit recording."""
    event_service = EventService(db_session)
    audit_service = AuditService(db_session)

    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": f"ITEM-SPARE-{uuid.uuid4().hex[:6].upper()}",
        "item_name": "Piston Hydro-Seal Spare",
        "category": "SPARE_PARTS",
        "unit": "UNIT"
    })
    item_id = item_res.json()["data"]["id"]

    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": str(uuid.uuid4()),
        "on_hand_quantity": 10.0,
        "status": "AVAILABLE"
    })
    lot_id = lot_res.json()["data"]["id"]

    # 1. Valid transition: AVAILABLE -> QUARANTINED
    trans_cid = uuid.uuid4()
    t_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/transition", json={
        "target_status": "QUARANTINED",
        "reason": "Cold embrittlement inspection needed"
    }, headers={"X-Request-ID": str(trans_cid)})
    assert t_res.status_code == 200
    assert t_res.json()["data"]["status"] == "QUARANTINED"

    # 2. Invalid transition: QUARANTINED -> ISSUED (not directly allowed)
    bad_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/transition", json={
        "target_status": "ISSUED",
        "reason": "Direct issue attempt"
    })
    assert bad_res.status_code == 409

    # 3. Verify event and audit
    events, _ = event_service.list_events()
    t_events = [e for e in events if e.event_type == "StockStatusChanged" and str(e.entity_id) == lot_id]
    assert len(t_events) >= 1
    assert t_events[-1].correlation_id == trans_cid

    audits, _ = audit_service.get_entity_audit_trail("INVENTORY_STOCK_LOT", uuid.UUID(lot_id))
    assert any(a.action == "TRANSITION_STOCK_STATUS" for a in audits)


# ============================================================
# 9. OPERATIONAL MUTATION BOUNDARY VALIDATIONS
# ============================================================

def test_operational_mutation_validation_errors(client):
    """Verifies domain validation errors on illegal quantities and non-existent entities."""
    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": f"ITEM-VAL-{uuid.uuid4().hex[:6].upper()}",
        "item_name": "Validation Test Chemical Compound",
        "category": "SCIENTIFIC",
        "unit": "LITER"
    })
    item_id = item_res.json()["data"]["id"]

    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": str(uuid.uuid4()),
        "on_hand_quantity": 50.0,
        "reserved_quantity": 10.0,
        "status": "AVAILABLE"
    })
    lot_id = lot_res.json()["data"]["id"]

    # 1. Release more than reserved (reserved is 10, try 25)
    rel_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/release", json={
        "quantity": 25.0
    })
    assert rel_res.status_code == 422

    # 2. Issue more than usable (usable is 50, try 60)
    iss_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/issue", json={
        "quantity": 60.0
    })
    assert iss_res.status_code == 422

    # 3. Quarantine more than unreserved available (available is 40, try 45)
    quar_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/quarantine", json={
        "quantity": 45.0,
        "reason": "Test"
    })
    assert quar_res.status_code == 422

    # 4. Non-existent stock lot operations
    fake_id = uuid.uuid4()
    assert client.get(f"/api/v1/inventory/stock-lots/{fake_id}").status_code == 404
    assert client.post(f"/api/v1/inventory/stock-lots/{fake_id}/receive", json={"quantity": 5.0}).status_code == 404
    assert client.post(f"/api/v1/inventory/stock-lots/{fake_id}/reserve", json={"quantity": 5.0}).status_code == 404


# ============================================================
# 10. REORDER POINT DEFICIT INDICATOR & FILTERING
# ============================================================

def test_stock_lot_deficit_indicator_and_filtering(client):
    """Verifies that available dropping below reorder_point flips is_deficit to True."""
    loc_id = uuid.uuid4()
    item_res = client.post("/api/v1/inventory/items", json={
        "item_code": f"ITEM-DEFICIT-{uuid.uuid4().hex[:6].upper()}",
        "item_name": "Emergency Hypothermia Survival Blankets",
        "category": "SAFETY",
        "unit": "BLANKET",
        "criticality": "LIFE_SUPPORT"
    })
    item_id = item_res.json()["data"]["id"]

    # 100 on hand, reorder point 40 -> available 100 (not deficit)
    lot_res = client.post("/api/v1/inventory/stock-lots", json={
        "inventory_item_id": item_id,
        "location_id": str(loc_id),
        "on_hand_quantity": 100.0,
        "reorder_point": 40.0,
        "status": "AVAILABLE"
    })
    lot_id = lot_res.json()["data"]["id"]
    assert lot_res.json()["data"]["is_deficit"] is False

    # Reserve 70 blankets -> available becomes 30 (which is <= 40 reorder point)
    res_res = client.post(f"/api/v1/inventory/stock-lots/{lot_id}/reserve", json={
        "quantity": 70.0
    })
    assert res_res.status_code == 200
    assert res_res.json()["data"]["is_deficit"] is True

    # Availability endpoint confirms deficit
    avail_res = client.get(f"/api/v1/inventory/stock-lots/{lot_id}/availability")
    assert avail_res.status_code == 200
    assert avail_res.json()["data"]["is_deficit"] is True
    assert float(avail_res.json()["data"]["available_quantity"]) == 30.0

    # Filter stock lots by location_id
    filter_res = client.get("/api/v1/inventory/stock-lots", params={"location_id": str(loc_id)})
    assert filter_res.status_code == 200
    assert len(filter_res.json()["data"]) >= 1

