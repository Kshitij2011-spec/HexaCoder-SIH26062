"""
Comprehensive Test Suite for Person B / Track B:
- Locations Domain (Hierarchy, operational state transitions, cycle rejection)
- Transport Domain (Legs, mode, temporal windows, manifest assignments)
- Cargo Domain (Consignments, physical packages, timeline endpoint)
- Domain-Authoritative Deterministic Risk Calculation (Threshold rules, timezone awareness)
- Realistic Transport State Machine (Direct transitions to DELAYED, terminal rejections)
- Clean One-Directional Transport -> Cargo Flow (No circular dependencies)
- Unified Causal Audit & Multi-Event Emission
- Fully Isolated Hero Integration Test (Zero mutation/dependence on demo seed baseline)
"""

import sys
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
from backend.app.core.errors import (
    InvalidStateTransitionError,
    DomainValidationError,
    ConflictError,
    EntityNotFoundError,
)

# Import all domain models for test harness metadata
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.people.models
import backend.app.domains.teams.models
import backend.app.domains.time_windows.models
import backend.app.domains.locations.models
import backend.app.domains.transport.models
import backend.app.domains.cargo.models
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.shared.types.states import (
    LocationStatus,
    TransportStatus,
    CargoStatus,
    CargoPackageStatus,
    CargoRiskLevel,
    AssignmentStatus,
)
from backend.app.domains.locations.transitions import validate_location_transition
from backend.app.domains.transport.transitions import validate_transport_transition
from backend.app.domains.cargo.transitions import (
    validate_cargo_consignment_transition,
    validate_cargo_package_transition,
)
from backend.app.domains.cargo.service import calculate_cargo_risk, CargoService
from backend.app.domains.transport.service import TransportService
from backend.app.domains.locations.service import LocationService
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory database fixture for Track B test suite."""
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
    """Yields an active database session for direct service testing."""
    override = app.dependency_overrides[get_db]
    session_gen = override()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()


# ============================================================
# 1. ARCHITECTURAL SANITY & CIRCULAR DEPENDENCY CHECK
# ============================================================

def test_no_circular_dependency_between_transport_and_cargo():
    """
    CORRECTION 1: Verify strict one-directional dependency.
    TransportService -> CargoService.
    CargoService MUST NOT import TransportService or transport module.
    """
    import ast
    from pathlib import Path
    cargo_service_path = Path("backend/app/domains/cargo/service.py")
    tree = ast.parse(cargo_service_path.read_text(encoding="utf-8"))

    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)
            for alias in node.names:
                imported_names.append(alias.name)

    for name in imported_names:
        assert "transport" not in name.lower(), f"CargoService imports forbidden transport symbol/module: {name}"
        assert "TransportService" not in name, f"CargoService imports forbidden TransportService: {name}"



# ============================================================
# 2. DOMAIN-AUTHORITATIVE RISK CALCULATION UNIT TESTS
# ============================================================

def test_risk_calculation_exception_states():
    """CORRECTION 2: DAMAGED, LOST, REJECTED must result in CRITICAL risk regardless of ETA."""
    req = datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc)
    eta = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)  # Well ahead of deadline

    assert calculate_cargo_risk("DAMAGED", eta, req) == "CRITICAL"
    assert calculate_cargo_risk("LOST", eta, req) == "CRITICAL"
    assert calculate_cargo_risk("REJECTED", eta, req) == "CRITICAL"


def test_risk_calculation_none_eta():
    """CORRECTION 2: Unconfirmed ETA must yield MODERATE risk."""
    req = datetime(2026, 12, 31, 12, 0, tzinfo=timezone.utc)
    assert calculate_cargo_risk("IN_TRANSIT", None, req) == "MODERATE"


def test_risk_calculation_deadline_breached():
    """CORRECTION 2: ETA > required_by must yield CRITICAL risk."""
    req = datetime(2026, 12, 24, 0, 0, tzinfo=timezone.utc)
    eta_late = datetime(2026, 12, 24, 0, 1, tzinfo=timezone.utc)  # 1 minute late
    assert calculate_cargo_risk("IN_TRANSIT", eta_late, req) == "CRITICAL"

    eta_way_late = datetime(2026, 12, 26, 0, 0, tzinfo=timezone.utc)
    assert calculate_cargo_risk("IN_TRANSIT", eta_way_late, req) == "CRITICAL"


def test_risk_calculation_buffer_thresholds():
    """CORRECTION 2: buffer < 48h -> ELEVATED, buffer < 120h -> MODERATE, otherwise -> NOMINAL."""
    req = datetime(2026, 12, 24, 0, 0, tzinfo=timezone.utc)

    # Buffer = 24 hours (< 48h) -> ELEVATED
    eta_tight = req - timedelta(hours=24)
    assert calculate_cargo_risk("IN_TRANSIT", eta_tight, req) == "ELEVATED"

    # Buffer = 47.9 hours (< 48h) -> ELEVATED
    eta_almost_48 = req - timedelta(hours=47, minutes=55)
    assert calculate_cargo_risk("IN_TRANSIT", eta_almost_48, req) == "ELEVATED"

    # Buffer = 72 hours (>= 48h and < 120h) -> MODERATE
    eta_mod = req - timedelta(hours=72)
    assert calculate_cargo_risk("IN_TRANSIT", eta_mod, req) == "MODERATE"

    # Buffer = 144 hours (6 days, >= 120h) -> NOMINAL
    eta_safe = req - timedelta(hours=144)
    assert calculate_cargo_risk("IN_TRANSIT", eta_safe, req) == "NOMINAL"


def test_risk_calculation_timezone_normalization():
    """CORRECTION 2: Timezones are normalized to UTC safely without arithmetic offsets mismatch."""
    req_utc = datetime(2026, 12, 24, 0, 0, tzinfo=timezone.utc)
    # 5.5 hours ahead (+05:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    eta_ist = datetime(2026, 12, 24, 10, 0, tzinfo=ist)  # 04:30 UTC -> 4.5 hours after required deadline
    assert calculate_cargo_risk("IN_TRANSIT", eta_ist, req_utc) == "CRITICAL"


# ============================================================
# 3. REALISTIC TRANSPORT TRANSITIONS
# ============================================================

def test_transport_transitions_to_delayed():
    """CORRECTION 3: Direct transitions READY -> DELAYED, DEPARTED -> DELAYED, IN_TRANSIT -> DELAYED are valid."""
    validate_transport_transition("READY", "DELAYED")
    validate_transport_transition("DEPARTED", "DELAYED")
    validate_transport_transition("IN_TRANSIT", "DELAYED")
    validate_transport_transition("BOOKED", "DELAYED")


def test_transport_terminal_state_rejection():
    """CORRECTION 3: Terminal states (CLOSED, CANCELLED) cannot transition to DELAYED or IN_TRANSIT."""
    with pytest.raises(InvalidStateTransitionError):
        validate_transport_transition("CLOSED", "DELAYED")

    with pytest.raises(InvalidStateTransitionError):
        validate_transport_transition("CLOSED", "IN_TRANSIT")

    with pytest.raises(InvalidStateTransitionError):
        validate_transport_transition("CANCELLED", "IN_TRANSIT")


# ============================================================
# 4. LOCATION DOMAIN TESTS
# ============================================================

def test_create_and_get_location(client):
    """Verifies location creation, storage, and retrieval."""
    loc_code = f"TEST-LOC-{uuid.uuid4().hex[:6]}"
    payload = {
        "code": loc_code,
        "name": "Maitri Science Waypoint Beta",
        "type": "WAYPOINT",
        "latitude": "-70.7650",
        "longitude": "11.7340",
        "description": "Geological field waypoint",
        "status": "AVAILABLE"
    }
    create_res = client.post("/api/v1/locations", json=payload)
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["errors"] is None
    loc_id = body["data"]["id"]

    get_res = client.get(f"/api/v1/locations/{loc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["code"] == loc_code
    assert get_res.json()["data"]["status"] == "AVAILABLE"


def test_location_state_transition(client):
    """Verifies operational state machine execution on locations."""
    loc_code = f"TEST-LOC-{uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/v1/locations", json={
        "code": loc_code,
        "name": "Troll Runway",
        "type": "AIRFIELD",
        "status": "AVAILABLE"
    })
    loc_id = create_res.json()["data"]["id"]

    # AVAILABLE -> RESTRICTED (e.g. blizzards)
    patch_res = client.patch(f"/api/v1/locations/{loc_id}/state", json={
        "status": "RESTRICTED",
        "reason": "Severe katabatic windstorm in effect"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "RESTRICTED"

    # RESTRICTED -> INACCESSIBLE
    patch_res2 = client.patch(f"/api/v1/locations/{loc_id}/state", json={
        "status": "INACCESSIBLE",
        "reason": "Crevasse field shift"
    })
    assert patch_res2.status_code == 200
    assert patch_res2.json()["data"]["status"] == "INACCESSIBLE"


def test_location_hierarchy_and_cycle_detection(client, db_session):
    """
    Verifies multi-tier location hierarchy (India -> Cape Town -> Vessel -> Station -> Field Camp)
    and prevents self-parenting and circular hierarchy.
    """
    service = LocationService(db_session)

    # 1. India
    ind = service.create_location(data=backend.app.domains.locations.schemas.LocationCreate(
        code=f"IND-{uuid.uuid4().hex[:4]}", name="Goa HQ", type="PORT"
    ))
    # 2. Cape Town
    cpt = service.create_location(data=backend.app.domains.locations.schemas.LocationCreate(
        code=f"CPT-{uuid.uuid4().hex[:4]}", name="Cape Town Staging", type="PORT", parent_location_id=ind.id
    ))
    # 3. Vessel
    vsl = service.create_location(data=backend.app.domains.locations.schemas.LocationCreate(
        code=f"VSL-{uuid.uuid4().hex[:4]}", name="Polar Vessel", type="ANCHORAGE", parent_location_id=cpt.id
    ))
    # 4. Station
    stn = service.create_location(data=backend.app.domains.locations.schemas.LocationCreate(
        code=f"STN-{uuid.uuid4().hex[:4]}", name="Maitri Station", type="STATION", parent_location_id=vsl.id
    ))
    # 5. Field Camp
    fld = service.create_location(data=backend.app.domains.locations.schemas.LocationCreate(
        code=f"FLD-{uuid.uuid4().hex[:4]}", name="Field Camp Alpha", type="FIELD_CAMP", parent_location_id=stn.id
    ))

    # Query hierarchy via API
    res = client.get(f"/api/v1/locations/{fld.id}/hierarchy")
    assert res.status_code == 200
    h_data = res.json()["data"]
    assert h_data["location"]["code"] == fld.code
    assert len(h_data["ancestors"]) == 4
    ancestor_codes = [a["code"] for a in h_data["ancestors"]]
    assert ancestor_codes == [ind.code, cpt.code, vsl.code, stn.code]

    # Cycle detection: attempt to set field camp as parent of its ancestor (India)
    with pytest.raises(DomainValidationError):
        service.update_location(
            location_id=ind.id,
            data=backend.app.domains.locations.schemas.LocationUpdate(parent_location_id=fld.id)
        )

    # Self-parenting rejection
    with pytest.raises(DomainValidationError):
        service.update_location(
            location_id=ind.id,
            data=backend.app.domains.locations.schemas.LocationUpdate(parent_location_id=ind.id)
        )


# ============================================================
# 5. TRANSPORT DOMAIN TESTS
# ============================================================

def test_transport_leg_validation_and_creation(client):
    """Verifies transport leg creation and endpoint validation."""
    exp_id = str(uuid.uuid4())
    loc1_id = str(uuid.uuid4())
    loc2_id = str(uuid.uuid4())

    # Origin == destination must fail validation
    invalid_payload = {
        "code": f"T-ERR-{uuid.uuid4().hex[:4]}",
        "expedition_id": exp_id,
        "mode": "VESSEL",
        "origin_location_id": loc1_id,
        "destination_location_id": loc1_id,
        "status": "PLANNED"
    }
    fail_res = client.post("/api/v1/transport/legs", json=invalid_payload)
    assert fail_res.status_code == 422

    # Valid leg
    valid_payload = {
        "code": f"T-LEG-{uuid.uuid4().hex[:6]}",
        "expedition_id": exp_id,
        "mode": "VESSEL",
        "origin_location_id": loc1_id,
        "destination_location_id": loc2_id,
        "planned_departure_at": "2026-11-20T08:00:00Z",
        "planned_arrival_at": "2026-12-15T12:00:00Z",
        "capacity": 500.0,
        "capacity_unit": "METRIC_TONS",
        "status": "PLANNED"
    }
    ok_res = client.post("/api/v1/transport/legs", json=valid_payload)
    assert ok_res.status_code == 201
    assert ok_res.json()["data"]["status"] == "PLANNED"


# ============================================================
# 6. CARGO DOMAIN TESTS
# ============================================================

def test_cargo_consignment_and_package_lifecycle(client):
    """Verifies consignment creation, package bundling, and timeline retrieval."""
    exp_id = str(uuid.uuid4())
    loc1_id = str(uuid.uuid4())
    loc2_id = str(uuid.uuid4())

    # Create consignment
    c_code = f"C-TEST-{uuid.uuid4().hex[:4]}"
    consignment_payload = {
        "code": c_code,
        "expedition_id": exp_id,
        "origin_location_id": loc1_id,
        "destination_location_id": loc2_id,
        "priority": 1,
        "required_by_at": "2026-12-25T00:00:00Z",
        "planned_arrival_at": "2026-12-18T12:00:00Z",
        "status": "REQUESTED"
    }
    c_res = client.post("/api/v1/cargo/consignments", json=consignment_payload)
    assert c_res.status_code == 201
    c_data = c_res.json()["data"]
    consignment_id = c_data["id"]
    assert c_data["risk_level"] == "NOMINAL"

    # Add package 1
    pkg1_res = client.post(f"/api/v1/cargo/consignments/{consignment_id}/packages", json={
        "code": f"PKG-1-{uuid.uuid4().hex[:4]}",
        "contents_summary": "Seismometer Spare Parts",
        "quantity": 1,
        "weight_kg": 25.5,
        "condition": "EXCELLENT",
        "status": "PACKED"
    })
    assert pkg1_res.status_code == 201

    # Add package 2
    pkg2_res = client.post(f"/api/v1/cargo/consignments/{consignment_id}/packages", json={
        "code": f"PKG-2-{uuid.uuid4().hex[:4]}",
        "contents_summary": "Cryo Cables Pallet",
        "quantity": 10,
        "weight_kg": 150.0,
        "condition": "GOOD",
        "status": "PACKED"
    })
    assert pkg2_res.status_code == 201

    # List packages
    pkgs_res = client.get(f"/api/v1/cargo/consignments/{consignment_id}/packages")
    assert pkgs_res.status_code == 200
    assert len(pkgs_res.json()["data"]) == 2

    # Get consignment detail
    detail_res = client.get(f"/api/v1/cargo/consignments/{consignment_id}")
    assert detail_res.status_code == 200
    assert len(detail_res.json()["data"]["packages"]) == 2

    # Query timeline endpoint
    timeline_res = client.get(f"/api/v1/cargo/consignments/{consignment_id}/timeline")
    assert timeline_res.status_code == 200
    t_data = timeline_res.json()["data"]
    assert t_data["is_delayed"] is False
    assert t_data["buffer_hours"] > 100.0  # Dec 18 to Dec 25 is 156 hours


# ============================================================
# 7. FULL HERO SCENARIO INTEGRATION TEST (COMPLETELY ISOLATED)
# ============================================================

def test_isolated_hero_scenario_transport_delay_propagates_to_cargo(client, db_session):
    """
    CORRECTIONS 4 & 5: Fully isolated Hero Logistics Integration Test.

    Workflow:
    - Uses distinct, isolated test UUIDs and codes (does NOT touch EXP-26-A, T-08, C-117, etc.)
    - Manifests Consignment (T-08 equivalent moving C-117 equivalent)
    - Initial state: ON TIME, ETA Dec 18, Required Dec 24, Risk: NOMINAL
    - Action: POST /api/v1/transport/legs/{id}/delay moving ETA to Dec 25 (breaching deadline)
    - Verifies:
        1. Single initiating audit entry DELAY_TRANSPORT_LEG with correlation_id
        2. TransportLegDelayed event emitted
        3. Consignment ETA updated to Dec 25
        4. Consignment risk updated to CRITICAL
        5. Consignment status updated to DELAYED
        6. CargoConsignmentETAUpdated and CargoConsignmentDelayed events emitted
    """
    event_service = EventService(db_session)
    audit_service = AuditService(db_session)

    test_cid = uuid.uuid4()
    expedition_id = uuid.uuid4()
    origin_loc_id = uuid.uuid4()
    dest_loc_id = uuid.uuid4()

    # 1. Create Transport Leg (T-08 equivalent)
    leg_code = f"HERO-T-{uuid.uuid4().hex[:6]}"
    leg_create = client.post("/api/v1/transport/legs", json={
        "code": leg_code,
        "expedition_id": str(expedition_id),
        "mode": "VESSEL",
        "origin_location_id": str(origin_loc_id),
        "destination_location_id": str(dest_loc_id),
        "planned_departure_at": "2026-11-22T08:00:00Z",
        "planned_arrival_at": "2026-12-18T12:00:00Z",
        "estimated_arrival_at": "2026-12-18T12:00:00Z",
        "status": "IN_TRANSIT"
    }, headers={"X-Request-ID": str(test_cid)})
    assert leg_create.status_code == 201
    leg_id = leg_create.json()["data"]["id"]

    # 2. Create Cargo Consignment (C-117 equivalent)
    cargo_code = f"HERO-C-{uuid.uuid4().hex[:6]}"
    cargo_create = client.post("/api/v1/cargo/consignments", json={
        "code": cargo_code,
        "expedition_id": str(expedition_id),
        "origin_location_id": str(origin_loc_id),
        "destination_location_id": str(dest_loc_id),
        "priority": 1,
        "required_by_at": "2026-12-24T00:00:00Z",  # Hard mission deadline
        "planned_arrival_at": "2026-12-18T12:00:00Z",
        "estimated_arrival_at": "2026-12-18T12:00:00Z",
        "status": "IN_TRANSIT"
    }, headers={"X-Request-ID": str(test_cid)})
    assert cargo_create.status_code == 201
    cargo_id = cargo_create.json()["data"]["id"]
    assert cargo_create.json()["data"]["risk_level"] == "NOMINAL"

    # 3. Create Package (PKG-117-01 equivalent)
    pkg_create = client.post(f"/api/v1/cargo/consignments/{cargo_id}/packages", json={
        "code": f"HERO-PKG-{uuid.uuid4().hex[:6]}",
        "contents_summary": "Broadband Seismometer Sensor Unit I-42",
        "quantity": 1,
        "status": "IN_TRANSIT"
    }, headers={"X-Request-ID": str(test_cid)})
    assert pkg_create.status_code == 201

    # 4. Manifest Consignment on Transport Leg (Cargo MOVES_VIA Transport)
    assign_res = client.post(f"/api/v1/transport/legs/{leg_id}/assign-cargo", json={
        "cargo_consignment_id": cargo_id
    }, headers={"X-Request-ID": str(test_cid)})
    assert assign_res.status_code == 201

    # Verify query for cargo on this leg
    cargo_list_res = client.get(f"/api/v1/transport/legs/{leg_id}/cargo")
    assert cargo_list_res.status_code == 200
    assert len(cargo_list_res.json()["data"]) == 1
    assert cargo_list_res.json()["data"][0]["id"] == cargo_id

    # 5. TRIGGER HERO OPERATIONAL DISRUPTION: TRANSPORT DELAY (Sea-ice pack delays leg to Dec 25)
    delay_cid = uuid.uuid4()
    delay_res = client.post(f"/api/v1/transport/legs/{leg_id}/delay", json={
        "new_estimated_arrival_at": "2026-12-25T18:00:00Z",
        "delay_reason": "Heavy polar sea-ice ridge preventing anchorage approach",
        "operational_metadata": {"sea_ice_thickness_meters": 2.8}
    }, headers={"X-Request-ID": str(delay_cid)})

    assert delay_res.status_code == 200
    impact_data = delay_res.json()["data"]
    assert impact_data["transport_leg"]["status"] == "DELAYED"
    assert len(impact_data["affected_cargo_consignments"]) == 1

    # Verify propagated cargo state
    affected_cargo = impact_data["affected_cargo_consignments"][0]
    assert affected_cargo["id"] == cargo_id
    assert affected_cargo["status"] == "DELAYED"
    assert affected_cargo["risk_level"] == "CRITICAL"  # Breached Dec 24 deadline!

    # 6. Verify Persistent Cargo State via GET /timeline
    timeline_res = client.get(f"/api/v1/cargo/consignments/{cargo_id}/timeline")
    assert timeline_res.status_code == 200
    t_info = timeline_res.json()["data"]
    assert t_info["status"] == "DELAYED"
    assert t_info["risk_level"] == "CRITICAL"
    assert t_info["is_delayed"] is True
    assert t_info["buffer_hours"] < 0  # Negative buffer: deadline breached

    # 7. Verify Operational Events in Event Journal
    events, count = event_service.list_events()
    event_types = [e.event_type for e in events]
    assert "TransportLegDelayed" in event_types
    assert "CargoConsignmentETAUpdated" in event_types
    assert "CargoConsignmentDelayed" in event_types

    # Find the TransportLegDelayed event and verify correlation ID
    t_delay_event = next(e for e in events if e.event_type == "TransportLegDelayed" and str(e.entity_id) == leg_id)
    assert t_delay_event.correlation_id == delay_cid

    # Find CargoConsignmentDelayed event and verify it shares the same correlation ID
    c_delay_event = next(e for e in events if e.event_type == "CargoConsignmentDelayed" and str(e.entity_id) == cargo_id)
    assert c_delay_event.correlation_id == delay_cid

    # 8. Verify Audit Log Trail
    audit_entries, a_count = audit_service.get_entity_audit_trail("TRANSPORT_LEG", uuid.UUID(leg_id))
    actions = [a.action for a in audit_entries]
    assert "DELAY_TRANSPORT_LEG" in actions
    delay_audit = next(a for a in audit_entries if a.action == "DELAY_TRANSPORT_LEG")
    assert delay_audit.correlation_id == delay_cid
    assert delay_audit.after_snapshot["status"] == "DELAYED"
    assert delay_audit.after_snapshot["affected_consignments_count"] == 1
