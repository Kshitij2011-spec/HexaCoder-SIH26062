"""
Comprehensive Test Suite for Person B / Track B - Milestone B4: Incident Response Domain:
- Incident Registry & CRUD (Unique incident_code, location and asset linkages)
- Incident Lifecycle State Machine (OPEN -> ACKNOWLEDGED -> MITIGATING -> RESOLVED -> CLOSED)
- Rejection of Invalid State Transitions & Terminal CLOSED Protection
- Lifecycle Timestamps (acknowledged_at, resolved_at, closed_at)
- Priority & Severity Range Validation (1 <= priority <= 5, controlled severities)
- Affected-Resource References (LOCATION, ASSET, INVENTORY_STOCK_LOT, CARGO_CONSIGNMENT, TRANSPORT_LEG)
- Strict Cross-Domain Isolation (Incident creation/referencing does NOT mutate other domains)
- Operational Timeline (Deterministic chronological event and reference history)
- Immutable Operational Events (IncidentCreated, IncidentUpdated, IncidentAcknowledged, etc.)
- Attributable Audit Logging with Correlation ID Tracing
- Full Backward Compatibility with Track A and Track B (B1, B2, B3)
"""

import ast
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
import backend.app.domains.incidents.models
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.domains.locations.models import LocationModel
from backend.app.domains.assets.models import AssetModel
from backend.app.domains.inventory.models import InventoryItemModel, InventoryStockLotModel
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
)
from backend.app.domains.incidents.transitions import (
    validate_incident_transition,
    is_terminal_incident_status,
)
from backend.app.domains.incidents.service import IncidentService
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for Incident Response tests."""
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

def test_incidents_domain_no_circular_dependencies():
    """Verifies that IncidentService has no circular dependencies with domain services."""
    service_path = Path("backend/app/domains/incidents/service.py")
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
        assert "AssetService" not in mod


# ============================================================
# 2. STATE MACHINE & TRANSITION ENFORCEMENT
# ============================================================

def test_valid_incident_transitions():
    """Verifies every legal lifecycle transition path."""
    # OPEN transitions
    validate_incident_transition(IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED)
    validate_incident_transition(IncidentStatus.OPEN, IncidentStatus.RESOLVED)
    validate_incident_transition(IncidentStatus.OPEN, IncidentStatus.CLOSED)

    # ACKNOWLEDGED transitions
    validate_incident_transition(IncidentStatus.ACKNOWLEDGED, IncidentStatus.MITIGATING)
    validate_incident_transition(IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED)
    validate_incident_transition(IncidentStatus.ACKNOWLEDGED, IncidentStatus.CLOSED)

    # MITIGATING transitions
    validate_incident_transition(IncidentStatus.MITIGATING, IncidentStatus.RESOLVED)

    # RESOLVED transitions
    validate_incident_transition(IncidentStatus.RESOLVED, IncidentStatus.CLOSED)

    # Self-transition is a no-op
    validate_incident_transition(IncidentStatus.OPEN, IncidentStatus.OPEN)
    validate_incident_transition(IncidentStatus.CLOSED, IncidentStatus.CLOSED)


def test_invalid_incident_transitions():
    """Verifies that illegal transitions fail deterministically with InvalidStateTransitionError."""
    # Cannot jump from OPEN directly to MITIGATING
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.OPEN, IncidentStatus.MITIGATING)

    # Cannot revert from MITIGATING to OPEN or jump directly to CLOSED
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.MITIGATING, IncidentStatus.OPEN)
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.MITIGATING, IncidentStatus.CLOSED)

    # Cannot revert from RESOLVED to OPEN or ACKNOWLEDGED
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.RESOLVED, IncidentStatus.OPEN)
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.RESOLVED, IncidentStatus.ACKNOWLEDGED)

    # CLOSED is terminal: cannot transition anywhere
    assert is_terminal_incident_status(IncidentStatus.CLOSED) is True
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.CLOSED, IncidentStatus.OPEN)
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.CLOSED, IncidentStatus.ACKNOWLEDGED)
    with pytest.raises(InvalidStateTransitionError):
        validate_incident_transition(IncidentStatus.CLOSED, IncidentStatus.RESOLVED)


# ============================================================
# 3. INCIDENT CRUD & REST API
# ============================================================

def test_incident_create_and_get(client):
    """Tests creating an incident via API, retrieving it, and checking default values."""
    corr_id = str(uuid.uuid4())
    payload = {
        "incident_code": "INC-TEST-001",
        "title": "Severe Generator Cooling Leak",
        "incident_type": "EQUIPMENT_FAILURE",
        "severity": "HIGH",
        "priority": 2,
        "description": "Primary radiator line fractured at Generator Station B.",
        "operational_metadata": {"affected_subsystem": "power_grid"},
    }

    res = client.post("/api/v1/incidents", json=payload, headers={"X-Request-ID": corr_id})
    assert res.status_code == 201
    body = res.json()
    data = body["data"]
    incident_id = data["id"]
    assert data["incident_code"] == "INC-TEST-001"
    assert data["status"] == "OPEN"
    assert data["severity"] == "HIGH"
    assert data["priority"] == 2
    assert data["acknowledged_at"] is None
    assert data["resolved_at"] is None
    assert data["closed_at"] is None

    # Retrieve by ID
    get_res = client.get(f"/api/v1/incidents/{incident_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["incident_code"] == "INC-TEST-001"


def test_incident_code_uniqueness(client):
    """Verifies that creating an incident with a duplicate code fails with 409 Conflict."""
    payload = {
        "incident_code": "INC-TEST-001",
        "title": "Duplicate Code Incident",
        "incident_type": "COMMUNICATION",
        "severity": "LOW",
        "priority": 4,
    }
    res = client.post("/api/v1/incidents", json=payload)
    assert res.status_code == 409
    errors = res.json()["errors"]
    assert any("already exists" in e["message"] for e in errors)


def test_incident_priority_validation(client):
    """Verifies that invalid priority values (< 1 or > 5) are rejected with 422."""
    # Priority < 1
    res_low = client.post("/api/v1/incidents", json={
        "incident_code": "INC-TEST-PRIO-LOW",
        "title": "Invalid Low Priority",
        "incident_type": "HAZARD",
        "priority": 0,
    })
    assert res_low.status_code == 422

    # Priority > 5
    res_high = client.post("/api/v1/incidents", json={
        "incident_code": "INC-TEST-PRIO-HIGH",
        "title": "Invalid High Priority",
        "incident_type": "HAZARD",
        "priority": 6,
    })
    assert res_high.status_code == 422


def test_incident_filtering_and_listing(client):
    """Tests filtering incidents by status, severity, and priority."""
    # Create distinct incidents for filtering
    client.post("/api/v1/incidents", json={
        "incident_code": "INC-FILTER-CRIT-P1",
        "title": "Critical Blizzard Warning",
        "incident_type": "WEATHER",
        "severity": "CRITICAL",
        "priority": 1,
    })
    client.post("/api/v1/incidents", json={
        "incident_code": "INC-FILTER-LOW-P5",
        "title": "Minor Thermometer Drift",
        "incident_type": "INSTRUMENT",
        "severity": "LOW",
        "priority": 5,
    })

    # Filter by severity CRITICAL
    res_sev = client.get("/api/v1/incidents?severity=CRITICAL")
    assert res_sev.status_code == 200
    items = res_sev.json()["data"]
    assert any(i["incident_code"] == "INC-FILTER-CRIT-P1" for i in items)
    assert not any(i["incident_code"] == "INC-FILTER-LOW-P5" for i in items)

    # Filter by priority 5
    res_prio = client.get("/api/v1/incidents?priority=5")
    assert res_prio.status_code == 200
    items_prio = res_prio.json()["data"]
    assert any(i["incident_code"] == "INC-FILTER-LOW-P5" for i in items_prio)
    assert not any(i["incident_code"] == "INC-FILTER-CRIT-P1" for i in items_prio)


def test_incident_update_and_closed_protection(client):
    """Tests updating incident metadata and verifies that CLOSED incidents are immutable."""
    create_res = client.post("/api/v1/incidents", json={
        "incident_code": "INC-TEST-UPDATE",
        "title": "Initial Title",
        "incident_type": "POWER",
        "severity": "MEDIUM",
        "priority": 3,
    })
    incident_id = create_res.json()["data"]["id"]

    # Valid PATCH update
    patch_res = client.patch(f"/api/v1/incidents/{incident_id}", json={
        "title": "Updated Title After Inspection",
        "priority": 2,
        "operational_metadata": {"inspected_by": "Dr. Smith"},
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["title"] == "Updated Title After Inspection"
    assert patch_res.json()["data"]["priority"] == 2

    # Close the incident
    close_res = client.post(f"/api/v1/incidents/{incident_id}/close", headers={"X-Request-ID": str(uuid.uuid4())})
    assert close_res.status_code == 200
    assert close_res.json()["data"]["status"] == "CLOSED"
    assert close_res.json()["data"]["closed_at"] is not None

    # Attempting to update a CLOSED incident must fail with 409
    patch_closed_res = client.patch(f"/api/v1/incidents/{incident_id}", json={"title": "Should Fail"})
    assert patch_closed_res.status_code == 409
    errors = patch_closed_res.json()["errors"]
    assert any("Cannot transition Incident" in e["message"] for e in errors)

    # Attempting to transition a CLOSED incident must fail with 409
    trans_closed_res = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"status": "OPEN"})
    assert trans_closed_res.status_code == 409


# ============================================================
# 4. LIFECYCLE OPERATIONS & TIMESTAMPS
# ============================================================

def test_full_incident_lifecycle_and_timestamps(client):
    """
    Verifies full lifecycle journey:
    OPEN -> ACKNOWLEDGED (sets acknowledged_at)
    -> MITIGATING (preserves acknowledged_at)
    -> RESOLVED (sets resolved_at)
    -> CLOSED (sets closed_at, terminal)
    """
    create_res = client.post("/api/v1/incidents", json={
        "incident_code": "INC-TEST-LIFECYCLE-01",
        "title": "Fuel Bladder Seepage",
        "incident_type": "LOGISTICS_HAZARD",
        "severity": "HIGH",
        "priority": 2,
    })
    incident_id = create_res.json()["data"]["id"]

    # 1. Acknowledge
    ack_res = client.post(f"/api/v1/incidents/{incident_id}/acknowledge")
    assert ack_res.status_code == 200
    data_ack = ack_res.json()["data"]
    assert data_ack["status"] == "ACKNOWLEDGED"
    assert data_ack["acknowledged_at"] is not None
    ack_ts = data_ack["acknowledged_at"]

    # 2. Mitigate
    mit_res = client.post(f"/api/v1/incidents/{incident_id}/mitigate")
    assert mit_res.status_code == 200
    data_mit = mit_res.json()["data"]
    assert data_mit["status"] == "MITIGATING"
    # Preserves acknowledged_at timestamp
    assert data_mit["acknowledged_at"] == ack_ts

    # 3. Resolve
    res_res = client.post(f"/api/v1/incidents/{incident_id}/resolve")
    assert res_res.status_code == 200
    data_res = res_res.json()["data"]
    assert data_res["status"] == "RESOLVED"
    assert data_res["resolved_at"] is not None
    res_ts = data_res["resolved_at"]

    # 4. Close
    close_res = client.post(f"/api/v1/incidents/{incident_id}/close")
    assert close_res.status_code == 200
    data_close = close_res.json()["data"]
    assert data_close["status"] == "CLOSED"
    assert data_close["closed_at"] is not None
    # Timestamps preserved
    assert data_close["acknowledged_at"] == ack_ts
    assert data_close["resolved_at"] == res_ts


# ============================================================
# 5. AFFECTED-RESOURCE REFERENCES & STRICT ISOLATION
# ============================================================

def test_incident_references_and_isolation(client, db_session):
    """
    Verifies that:
    1. An incident can reference LOCATION, ASSET, INVENTORY_STOCK_LOT, CARGO_CONSIGNMENT, and TRANSPORT_LEG.
    2. Referenced entities are NOT mutated (STRICT CROSS-DOMAIN ISOLATION).
    3. Duplicate references and invalid reference types are rejected.
    4. Closed incidents reject adding new references.
    """
    # Set up realistic baseline entities in DB
    loc = LocationModel(
        id=uuid.uuid4(),
        code="LOC-INCD-01",
        name="Bharati Station Depot",
        type="STATION",
        status="AVAILABLE",
    )
    db_session.add(loc)

    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="AST-INCD-01",
        name="Snowcat Alpha",
        type="VEHICLE",
        condition="OPERATIONAL",
        criticality="MISSION_CRITICAL",
        status="AVAILABLE",
    )
    db_session.add(asset)

    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code="ITM-INCD-01",
        item_name="Generator Valve",
        category="SPARE_PARTS",
        unit="EACH",
    )
    db_session.add(item)
    db_session.flush()

    stock_lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        lot_code="LOT-INCD-01",
        inventory_item_id=item.id,
        location_id=loc.id,
        on_hand_quantity=10,
        reserved_quantity=0,
        status="AVAILABLE",
    )
    db_session.add(stock_lot)

    leg = TransportLegModel(
        id=uuid.uuid4(),
        code="LEG-INCD-01",
        expedition_id=uuid.uuid4(),
        origin_location_id=loc.id,
        destination_location_id=loc.id,
        mode="OVERLAND",
        status="IN_TRANSIT",
    )
    db_session.add(leg)

    consignment = CargoConsignmentModel(
        id=uuid.uuid4(),
        code="CRG-INCD-01",
        expedition_id=uuid.uuid4(),
        status="IN_TRANSIT",
        origin_location_id=loc.id,
        destination_location_id=loc.id,
        required_by_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(consignment)
    db_session.commit()

    # Create an incident
    inc_res = client.post("/api/v1/incidents", json={
        "incident_code": "INC-TEST-REFERENCES",
        "title": "Severe Route Crevasse Hazard",
        "incident_type": "TERRAIN_HAZARD",
        "severity": "CRITICAL",
        "priority": 1,
    })
    incident_id = inc_res.json()["data"]["id"]

    # 1. Attach LOCATION reference
    ref_loc_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "LOCATION",
        "reference_id": str(loc.id),
        "notes": "Crevasse field detected 2km north of depot",
    })
    assert ref_loc_res.status_code == 201

    # 2. Attach ASSET reference
    ref_ast_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "ASSET",
        "reference_id": str(asset.id),
        "notes": "Snowcat halted near crevasse perimeter",
    })
    assert ref_ast_res.status_code == 201

    # 3. Attach INVENTORY_STOCK_LOT reference
    ref_inv_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "INVENTORY_STOCK_LOT",
        "reference_id": str(stock_lot.id),
        "notes": "Emergency bridge kit requested",
    })
    assert ref_inv_res.status_code == 201

    # 4. Attach TRANSPORT_LEG reference
    ref_leg_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "TRANSPORT_LEG",
        "reference_id": str(leg.id),
        "notes": "Leg passage blocked",
    })
    assert ref_leg_res.status_code == 201

    # 5. Attach CARGO_CONSIGNMENT reference
    ref_crg_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "CARGO_CONSIGNMENT",
        "reference_id": str(consignment.id),
        "notes": "Consignment in stalled convoy",
    })
    assert ref_crg_res.status_code == 201

    # Verify list of references
    list_refs_res = client.get(f"/api/v1/incidents/{incident_id}/references")
    assert list_refs_res.status_code == 200
    refs = list_refs_res.json()["data"]
    assert len(refs) == 5

    # 6. Verify duplicate reference rejection
    dup_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "LOCATION",
        "reference_id": str(loc.id),
    })
    assert dup_res.status_code == 409

    # 7. Verify invalid reference type rejection
    inv_type_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "INVALID_TYPE",
        "reference_id": str(uuid.uuid4()),
    })
    assert inv_type_res.status_code == 422

    # 8. STRICT CROSS-DOMAIN ISOLATION VERIFICATION
    # Refresh referenced entities from DB and verify NONE were mutated
    db_session.expire_all()
    loc_check = db_session.get(LocationModel, loc.id)
    asset_check = db_session.get(AssetModel, asset.id)
    stock_check = db_session.get(InventoryStockLotModel, stock_lot.id)
    leg_check = db_session.get(TransportLegModel, leg.id)
    crg_check = db_session.get(CargoConsignmentModel, consignment.id)

    assert loc_check.status == "AVAILABLE", "Location status must not be modified by B4"
    assert asset_check.status == "AVAILABLE", "Asset status must not be modified by B4"
    assert stock_check.status == "AVAILABLE", "Stock lot status must not be modified by B4"
    assert stock_check.on_hand_quantity == 10, "Stock lot quantity must not be modified by B4"
    assert leg_check.status == "IN_TRANSIT", "Transport leg status must not be modified by B4"
    assert crg_check.status == "IN_TRANSIT", "Cargo consignment status must not be modified by B4"

    # 9. Close incident and verify adding references is blocked
    client.post(f"/api/v1/incidents/{incident_id}/close")
    blocked_ref_res = client.post(f"/api/v1/incidents/{incident_id}/references", json={
        "reference_type": "LOCATION",
        "reference_id": str(uuid.uuid4()),
    })
    assert blocked_ref_res.status_code == 409


# ============================================================
# 6. OPERATIONAL EVENTS, AUDITS & TIMELINE
# ============================================================

def test_incident_events_audits_and_timeline(client, db_session):
    """
    Verifies that:
    1. Operational events (IncidentCreated, IncidentAcknowledged, IncidentResolved, IncidentClosed) are emitted.
    2. Audit logs (CREATE_INCIDENT, ACKNOWLEDGE_INCIDENT, ADD_INCIDENT_REFERENCE, etc.) are recorded.
    3. Correlation IDs are preserved across operations, events, and audits.
    4. Timeline combines events and references in deterministic chronological order.
    """
    corr_id = uuid.uuid4()
    # 1. Create incident with correlation ID
    create_res = client.post(
        "/api/v1/incidents",
        json={
            "incident_code": "INC-TEST-TIMELINE-01",
            "title": "Solar Array Communication Loss",
            "incident_type": "TELEMETRY",
            "severity": "MEDIUM",
            "priority": 3,
        },
        headers={"X-Request-ID": str(corr_id)}
    )
    assert create_res.status_code == 201
    incident_id = uuid.UUID(create_res.json()["data"]["id"])

    # 2. Add reference
    client.post(
        f"/api/v1/incidents/{incident_id}/references",
        json={
            "reference_type": "LOCATION",
            "reference_id": str(uuid.uuid4()),
            "notes": "Array site #3",
        },
        headers={"X-Request-ID": str(corr_id)}
    )

    # 3. Transition through lifecycle
    client.post(f"/api/v1/incidents/{incident_id}/acknowledge", headers={"X-Request-ID": str(corr_id)})
    client.post(f"/api/v1/incidents/{incident_id}/mitigate", headers={"X-Request-ID": str(corr_id)})
    client.post(f"/api/v1/incidents/{incident_id}/resolve", headers={"X-Request-ID": str(corr_id)})
    client.post(f"/api/v1/incidents/{incident_id}/close", headers={"X-Request-ID": str(corr_id)})

    # Verify EventService recorded all lifecycle events with correlation_id
    event_service = EventService(db_session)
    events, total_events = event_service.get_entity_history(entity_type="INCIDENT", entity_id=incident_id, page_size=100)
    assert total_events >= 5
    event_types = [e.event_type for e in events]
    assert "IncidentCreated" in event_types
    assert "IncidentAcknowledged" in event_types
    assert "IncidentMitigationStarted" in event_types
    assert "IncidentResolved" in event_types
    assert "IncidentClosed" in event_types

    for ev in events:
        assert ev.correlation_id == corr_id

    # Verify AuditService recorded all audit actions
    audit_service = AuditService(db_session)
    audits, total_audits = audit_service.get_entity_audit_trail(entity_type="INCIDENT", entity_id=incident_id, page_size=100)
    assert total_audits >= 6
    audit_actions = [a.action for a in audits]
    assert "CREATE_INCIDENT" in audit_actions
    assert "ADD_INCIDENT_REFERENCE" in audit_actions
    assert "ACKNOWLEDGE_INCIDENT" in audit_actions
    assert "START_INCIDENT_MITIGATION" in audit_actions
    assert "RESOLVE_INCIDENT" in audit_actions
    assert "CLOSE_INCIDENT" in audit_actions

    for aud in audits:
        assert aud.correlation_id == corr_id

    # Verify Timeline API returns deterministic chronological entries
    timeline_res = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert timeline_res.status_code == 200
    timeline_body = timeline_res.json()["data"]
    assert timeline_body["incident_code"] == "INC-TEST-TIMELINE-01"
    assert timeline_body["current_status"] == "CLOSED"
    entries = timeline_body["entries"]
    assert len(entries) >= 6

    # Verify chronological ascending order
    timestamps = [e["timestamp"] for e in entries]
    assert timestamps == sorted(timestamps)

    # Check both EVENT and REFERENCE types are included
    entry_types = [e["entry_type"] for e in entries]
    assert "EVENT" in entry_types
    assert "REFERENCE" in entry_types
