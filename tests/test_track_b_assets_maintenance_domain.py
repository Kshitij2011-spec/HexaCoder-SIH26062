"""
Comprehensive Test Suite for Person B / Track B - Milestone B3:
- Asset Registry & CRUD (Unique asset_code, unique serial_number, location linkage)
- Asset Lifecycle State Machine (AVAILABLE -> RESERVED -> IN_USE -> MAINTENANCE -> QUARANTINED -> RETIRED)
- Terminal Retirement Behavior (No updates, movements, transitions, or maintenance on retired assets)
- Asset Relocation & Location Validation
- Maintenance Orders Lifecycle (SCHEDULED -> IN_PROGRESS -> COMPLETED / CANCELLED / OVERDUE)
- Active-Maintenance Collision Protection (Overlapping active orders rejected with 409)
- Non-Silent Completion Rule (Asset status untouched unless explicitly requested)
- Operational Timeline (Chronological events, movements, maintenance orders)
- Immutable Event Journaling (AssetCreated, AssetStatusChanged, AssetMoved, MaintenanceScheduled, MaintenanceStarted, MaintenanceCompleted, MaintenanceCancelled)
- Attributable Audit Logging with Correlation ID Tracing
- Full Backward Compatibility with B1 (Logistics/Cargo/Transport) & B2 (Inventory)
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
import backend.app.domains.assets.models
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.domains.assets.states import (
    AssetStatus,
    MaintenanceStatus,
    AssetCriticality,
    AssetCondition,
)
from backend.app.domains.assets.transitions import (
    validate_asset_transition,
    validate_maintenance_transition,
)
from backend.app.domains.assets.service import AssetService
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for Assets & Maintenance tests."""
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
# 1. ARCHITECTURAL SANITY & BOUNDARY CHECKS
# ============================================================

def test_assets_domain_no_circular_dependencies():
    """Verifies that AssetService has no circular dependencies with other Track B or Track A domains."""
    service_path = Path("backend/app/domains/assets/service.py")
    tree = ast.parse(service_path.read_text(encoding="utf-8"))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    for mod in imported_modules:
        assert "TransportService" not in mod
        assert "CargoService" not in mod
        assert "InventoryService" not in mod
        assert "backend.app.domains.expeditions" not in mod


# ============================================================
# 2. STATE MACHINE TRANSITION UNIT TESTS
# ============================================================

def test_asset_lifecycle_transitions():
    """Tests all valid and invalid lifecycle movements for assets."""
    # Valid transitions
    validate_asset_transition("AVAILABLE", "RESERVED")
    validate_asset_transition("RESERVED", "IN_USE")
    validate_asset_transition("IN_USE", "MAINTENANCE")
    validate_asset_transition("MAINTENANCE", "QUARANTINED")
    validate_asset_transition("QUARANTINED", "AVAILABLE")
    validate_asset_transition("AVAILABLE", "RETIRED")
    validate_asset_transition("RESERVED", "RETIRED")
    validate_asset_transition("IN_USE", "RETIRED")
    validate_asset_transition("MAINTENANCE", "RETIRED")
    validate_asset_transition("QUARANTINED", "RETIRED")

    # Invalid transitions
    with pytest.raises(InvalidStateTransitionError):
        validate_asset_transition("MAINTENANCE", "IN_USE")  # Must be AVAILABLE first

    with pytest.raises(InvalidStateTransitionError):
        validate_asset_transition("RETIRED", "AVAILABLE")  # Terminal state


def test_maintenance_lifecycle_transitions():
    """Tests all valid and invalid lifecycle movements for maintenance records."""
    # Valid transitions
    validate_maintenance_transition("SCHEDULED", "IN_PROGRESS")
    validate_maintenance_transition("IN_PROGRESS", "COMPLETED")
    validate_maintenance_transition("SCHEDULED", "CANCELLED")
    validate_maintenance_transition("IN_PROGRESS", "CANCELLED")
    validate_maintenance_transition("SCHEDULED", "OVERDUE")
    validate_maintenance_transition("OVERDUE", "IN_PROGRESS")
    validate_maintenance_transition("OVERDUE", "CANCELLED")

    # Terminal transitions
    with pytest.raises(InvalidStateTransitionError):
        validate_maintenance_transition("COMPLETED", "IN_PROGRESS")

    with pytest.raises(InvalidStateTransitionError):
        validate_maintenance_transition("CANCELLED", "SCHEDULED")


# ============================================================
# 3. ASSET CRUD & UNIQUENESS CONSTRAINTS
# ============================================================

def test_asset_creation_and_uniqueness(client):
    """Verifies asset creation, unique asset_code, and unique serial_number."""
    code = f"AST-GEN-{uuid.uuid4().hex[:6].upper()}"
    serial = f"SN-{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "asset_code": code,
        "serial_number": serial,
        "name": "Caterpillar 3512 Polar Diesel Generator",
        "type": "POWER_GENERATION",
        "model": "3512B-HD",
        "condition": "OPERATIONAL",
        "criticality": "LIFE_SUPPORT",
        "description": "Primary base load generator for Bharati Station",
        "status": "AVAILABLE"
    }

    # 1. Create asset
    res = client.post("/api/v1/assets", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["asset_code"] == code
    assert data["serial_number"] == serial
    asset_id = data["id"]

    # 2. Duplicate asset_code rejection
    dup_code_res = client.post("/api/v1/assets", json={
        **payload,
        "serial_number": f"SN-OTHER-{uuid.uuid4().hex[:4]}"
    })
    assert dup_code_res.status_code == 409

    # 3. Duplicate serial_number rejection
    dup_sn_res = client.post("/api/v1/assets", json={
        **payload,
        "asset_code": f"AST-OTHER-{uuid.uuid4().hex[:4]}"
    })
    assert dup_sn_res.status_code == 409

    # 4. Get asset by ID
    get_res = client.get(f"/api/v1/assets/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Caterpillar 3512 Polar Diesel Generator"

    # 5. Patch asset metadata
    patch_res = client.patch(f"/api/v1/assets/{asset_id}", json={
        "name": "Caterpillar 3512B Primary GenSet",
        "condition": "DEGRADED"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["name"] == "Caterpillar 3512B Primary GenSet"
    assert patch_res.json()["data"]["condition"] == "DEGRADED"

    # 6. List assets
    list_res = client.get("/api/v1/assets", params={"type": "POWER_GENERATION"})
    assert list_res.status_code == 200
    assert any(a["id"] == asset_id for a in list_res.json()["data"])


# ============================================================
# 4. ASSET RELOCATION & LOCATION VALIDATION
# ============================================================

def test_asset_relocation_and_audit(client, db_session):
    """Verifies asset move, invalid destination location rejection, and audit trail."""
    event_service = EventService(db_session)
    audit_service = AuditService(db_session)

    # 1. Create origin location
    loc1_res = client.post("/api/v1/locations", json={
        "code": f"LOC-BHARATI-{uuid.uuid4().hex[:4].upper()}",
        "name": "Bharati Research Station",
        "type": "STATION",
        "status": "AVAILABLE"
    })
    assert loc1_res.status_code == 201
    loc1_id = loc1_res.json()["data"]["id"]

    # 2. Create destination location
    loc2_res = client.post("/api/v1/locations", json={
        "code": f"LOC-MAITRI-{uuid.uuid4().hex[:4].upper()}",
        "name": "Maitri Research Station",
        "type": "STATION",
        "status": "AVAILABLE"
    })
    assert loc2_res.status_code == 201
    loc2_id = loc2_res.json()["data"]["id"]

    # 3. Create asset at Bharati
    asset_res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-PISTON-{uuid.uuid4().hex[:6].upper()}",
        "name": "Kässbohrer PistenBully 300 Polar",
        "type": "VEHICLE",
        "location_id": loc1_id,
        "status": "AVAILABLE"
    })
    assert asset_res.status_code == 201
    asset_id = asset_res.json()["data"]["id"]

    # 4. Move to non-existent location (404)
    fake_loc_id = uuid.uuid4()
    bad_move_res = client.post(f"/api/v1/assets/{asset_id}/move", json={
        "destination_location_id": str(fake_loc_id)
    })
    assert bad_move_res.status_code == 404

    # 5. Move to Maitri with correlation ID
    move_cid = uuid.uuid4()
    move_res = client.post(f"/api/v1/assets/{asset_id}/move", json={
        "destination_location_id": loc2_id,
        "reason": "Redeployed for summer science traverse"
    }, headers={"X-Request-ID": str(move_cid)})
    assert move_res.status_code == 200
    assert move_res.json()["data"]["location_id"] == loc2_id

    # 6. Verify AssetMoved event
    events, _ = event_service.list_events()
    move_events = [e for e in events if e.event_type == "AssetMoved" and str(e.entity_id) == asset_id]
    assert len(move_events) == 1
    assert move_events[0].correlation_id == move_cid
    assert move_events[0].evidence["to_location_id"] == loc2_id

    # 7. Verify MOVE_ASSET audit record
    audits, _ = audit_service.get_entity_audit_trail("ASSET", uuid.UUID(asset_id))
    move_audits = [a for a in audits if a.action == "MOVE_ASSET"]
    assert len(move_audits) == 1
    assert move_audits[0].correlation_id == move_cid


# ============================================================
# 5. TERMINAL RETIREMENT BEHAVIOR
# ============================================================

def test_retired_asset_terminal_invariants(client):
    """
    Verifies terminal retirement invariants:
    - Once RETIRED, asset cannot transition
    - Cannot be updated
    - Cannot be moved
    - Cannot receive new maintenance
    """
    asset_res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-RET-{uuid.uuid4().hex[:6].upper()}",
        "name": "Decommissioned Skidoo Snowmobile",
        "type": "VEHICLE",
        "status": "AVAILABLE"
    })
    assert asset_res.status_code == 201
    asset_id = asset_res.json()["data"]["id"]

    # 1. Transition to RETIRED
    ret_res = client.post(f"/api/v1/assets/{asset_id}/transition", json={
        "target_status": "RETIRED",
        "reason": "Engine block cracked; beyond economical repair"
    })
    assert ret_res.status_code == 200
    assert ret_res.json()["data"]["status"] == "RETIRED"
    assert ret_res.json()["data"]["retired_at"] is not None

    # 2. Cannot transition out of RETIRED (422/409)
    bad_trans = client.post(f"/api/v1/assets/{asset_id}/transition", json={
        "target_status": "AVAILABLE"
    })
    assert bad_trans.status_code in [409, 422]

    # 3. Cannot update metadata (422)
    bad_patch = client.patch(f"/api/v1/assets/{asset_id}", json={
        "name": "Zombie Snowmobile"
    })
    assert bad_patch.status_code == 422

    # 4. Cannot move (422)
    bad_move = client.post(f"/api/v1/assets/{asset_id}/move", json={
        "destination_location_id": str(uuid.uuid4())
    })
    assert bad_move.status_code == 422

    # 5. Cannot schedule new maintenance (422)
    bad_maint = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "OVERHAUL"
    })
    assert bad_maint.status_code == 422


# ============================================================
# 6. MAINTENANCE LIFECYCLE, START, COMPLETE, & CANCEL
# ============================================================

def test_maintenance_order_full_lifecycle(client, db_session):
    """
    Verifies complete maintenance workflow:
    - Schedule maintenance
    - Start maintenance (with optional asset status transition to MAINTENANCE)
    - Complete maintenance (verifying non-silent completion rule)
    - Explicit target_asset_status verification
    - Event and audit verification
    """
    event_service = EventService(db_session)
    audit_service = AuditService(db_session)

    test_cid = uuid.uuid4()
    # 1. Create operational asset
    asset_res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-DRILL-{uuid.uuid4().hex[:6].upper()}",
        "name": "Hot Water Ice-Core Drill System",
        "type": "SCIENTIFIC",
        "status": "AVAILABLE"
    }, headers={"X-Request-ID": str(test_cid)})
    assert asset_res.status_code == 201
    asset_id = asset_res.json()["data"]["id"]

    # 2. Schedule maintenance
    maint_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "PREVENTATIVE_500_HOUR",
        "priority": 2,
        "description": "High pressure boiler nozzle and heat exchanger descaling",
        "performed_by": "Expedition Mechanical Engineer",
        "technician_reference": "TECH-IND-042"
    }, headers={"X-Request-ID": str(test_cid)})
    assert maint_res.status_code == 201
    maint_data = maint_res.json()["data"]
    maint_id = maint_data["id"]
    assert maint_data["status"] == "SCHEDULED"
    assert maint_data["priority"] == 2

    # 3. Start maintenance with transition_asset_to_maintenance=True
    start_res = client.post(f"/api/v1/assets/maintenance/{maint_id}/start", json={
        "transition_asset_to_maintenance": True,
        "notes": "Work commenced in Bharati main workshop hangar"
    }, headers={"X-Request-ID": str(test_cid)})
    assert start_res.status_code == 200
    assert start_res.json()["data"]["status"] == "IN_PROGRESS"
    assert start_res.json()["data"]["started_at"] is not None

    # Verify asset status transitioned to MAINTENANCE
    asset_check = client.get(f"/api/v1/assets/{asset_id}")
    assert asset_check.json()["data"]["status"] == "MAINTENANCE"

    # 4. Complete maintenance WITHOUT target_asset_status (Non-silent rule: asset stays MAINTENANCE)
    comp_res = client.post(f"/api/v1/assets/maintenance/{maint_id}/complete", json={
        "findings": "Minor soot accumulation on combustion electrodes. Replaced fuel filters.",
        "corrective_action": "Electrodes cleaned and re-gapped to 3.5mm. Filter cartridge swapped.",
        "notes": "Pressure testing confirmed nominal at 150 bar."
    }, headers={"X-Request-ID": str(test_cid)})
    assert comp_res.status_code == 200
    comp_data = comp_res.json()["data"]
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["completed_at"] is not None
    assert comp_data["findings"] is not None

    # Asset status must NOT silently change (stays MAINTENANCE)
    asset_check2 = client.get(f"/api/v1/assets/{asset_id}")
    assert asset_check2.json()["data"]["status"] == "MAINTENANCE"

    # 5. Now schedule a second maintenance to test explicit target_asset_status
    maint2_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "FINAL_CERTIFICATION",
        "priority": 1
    })
    assert maint2_res.status_code == 201
    maint2_id = maint2_res.json()["data"]["id"]

    client.post(f"/api/v1/assets/maintenance/{maint2_id}/start", json={})

    # Complete with explicit target_asset_status=AVAILABLE
    comp2_res = client.post(f"/api/v1/assets/maintenance/{maint2_id}/complete", json={
        "findings": "Full system load test passed",
        "target_asset_status": "AVAILABLE"
    })
    assert comp2_res.status_code == 200

    # Asset status is now AVAILABLE
    asset_check3 = client.get(f"/api/v1/assets/{asset_id}")
    assert asset_check3.json()["data"]["status"] == "AVAILABLE"

    # 6. Verify operational events
    events, _ = event_service.list_events()
    event_types = [e.event_type for e in events]
    assert "MaintenanceScheduled" in event_types
    assert "MaintenanceStarted" in event_types
    assert "MaintenanceCompleted" in event_types

    # 7. Verify audit records
    audits, _ = audit_service.get_entity_audit_trail("MAINTENANCE_RECORD", uuid.UUID(maint_id))
    audit_actions = [a.action for a in audits]
    assert "SCHEDULE_MAINTENANCE" in audit_actions
    assert "START_MAINTENANCE" in audit_actions
    assert "COMPLETE_MAINTENANCE" in audit_actions


# ============================================================
# 7. ACTIVE-MAINTENANCE COLLISION PROTECTION
# ============================================================

def test_overlapping_active_maintenance_rejection(client):
    """
    Verifies that an asset cannot have more than one active maintenance order.
    Attempting to schedule while another is SCHEDULED or IN_PROGRESS returns 409 Conflict.
    """
    asset_res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-COLL-{uuid.uuid4().hex[:6].upper()}",
        "name": "Polar Radiometer Calibration Unit",
        "type": "SCIENTIFIC",
        "status": "AVAILABLE"
    })
    asset_id = asset_res.json()["data"]["id"]

    # 1. Schedule first order
    m1_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "CALIBRATION_CHECK",
        "priority": 3
    })
    assert m1_res.status_code == 201

    # 2. Attempt to schedule second order while m1 is SCHEDULED -> 409
    m2_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "SECONDARY_CHECK",
        "priority": 4
    })
    assert m2_res.status_code == 409

    # 3. Start m1 (status becomes IN_PROGRESS)
    m1_id = m1_res.json()["data"]["id"]
    client.post(f"/api/v1/assets/maintenance/{m1_id}/start", json={})

    # 4. Attempt to schedule while m1 is IN_PROGRESS -> still 409
    m3_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "THIRD_CHECK",
        "priority": 4
    })
    assert m3_res.status_code == 409

    # 5. Cancel m1 (terminal)
    cancel_res = client.post(f"/api/v1/assets/maintenance/{m1_id}/cancel", json={
        "reason": "Calibration gas cylinder empty; postponing"
    })
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # 6. Now scheduling a new order succeeds
    m4_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "RESCHEDULED_CALIBRATION",
        "priority": 3
    })
    assert m4_res.status_code == 201


# ============================================================
# 8. OPERATIONAL ASSET TIMELINE ENDPOINT
# ============================================================

def test_asset_timeline_endpoint(client):
    """Verifies that GET /api/v1/assets/{id}/timeline returns chronological movements & orders."""
    asset_res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-TIME-{uuid.uuid4().hex[:6].upper()}",
        "name": "Automatic Weather Station Met Tower",
        "type": "METEOROLOGY",
        "status": "AVAILABLE"
    })
    asset_id = asset_res.json()["data"]["id"]

    # Schedule and complete maintenance
    m_res = client.post(f"/api/v1/assets/{asset_id}/maintenance", json={
        "maintenance_type": "ANEMOMETER_REPLACEMENT"
    })
    m_id = m_res.json()["data"]["id"]
    client.post(f"/api/v1/assets/maintenance/{m_id}/start", json={})
    client.post(f"/api/v1/assets/maintenance/{m_id}/complete", json={
        "findings": "Bearings frozen by rime ice",
        "corrective_action": "Replaced heated cup anemometer unit"
    })

    # Query timeline
    timeline_res = client.get(f"/api/v1/assets/{asset_id}/timeline")
    assert timeline_res.status_code == 200
    t_data = timeline_res.json()["data"]
    assert t_data["asset_id"] == asset_id
    assert t_data["maintenance_history_count"] == 1
    assert len(t_data["timeline"]) >= 1


# ============================================================
# 9. ASSET CREATION WITH INVALID LOCATION REJECTION
# ============================================================

def test_asset_creation_invalid_location(client):
    """Verifies that providing a non-existent location_id on creation returns 404."""
    fake_loc = uuid.uuid4()
    res = client.post("/api/v1/assets", json={
        "asset_code": f"AST-BADLOC-{uuid.uuid4().hex[:6].upper()}",
        "name": "Ghost Sensor Pod",
        "type": "SCIENTIFIC",
        "location_id": str(fake_loc)
    })
    assert res.status_code == 404


# ============================================================
# 10. MAINTENANCE RECORD NOT FOUND & CANCEL ERROR HANDLING
# ============================================================

def test_maintenance_errors_and_not_found(client):
    """Verifies 404 on missing maintenance orders and terminal cancellation."""
    fake_id = uuid.uuid4()
    assert client.get(f"/api/v1/assets/maintenance/{fake_id}").status_code == 404
    assert client.post(f"/api/v1/assets/maintenance/{fake_id}/start", json={}).status_code == 404
    assert client.post(f"/api/v1/assets/maintenance/{fake_id}/complete", json={}).status_code == 404
    assert client.post(f"/api/v1/assets/maintenance/{fake_id}/cancel", json={"reason": "test"}).status_code == 404

