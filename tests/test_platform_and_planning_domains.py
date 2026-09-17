"""
Comprehensive Test Suite for Person A / Track A:
- FastAPI Platform & Error Handling
- Envelope Compliance (docs/API_CONTRACT_POLICY.md)
- Request Correlation ID (X-Request-ID)
- Expedition Domain & Transitions
- Mission Domain & Transitions & Cross-domain Contracts
- Personnel Domain & Dual-State (Readiness & Movement)
- Teams Domain & Invariants (Same Expedition, Leader)
- Time Windows Domain & Temporal Bounds (close_at > open_at)
- Operational Events Foundation & Immutability
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.errors import (
    InvalidStateTransitionError,
    DomainValidationError,
)
from backend.app.domains.expeditions.transitions import (
    validate_expedition_transition,
    ALLOWED_EXPEDITION_TRANSITIONS,
)
from backend.app.domains.missions.transitions import (
    validate_mission_transition,
    ALLOWED_MISSION_TRANSITIONS,
)
from backend.app.domains.people.transitions import (
    validate_readiness_transition,
    validate_movement_transition,
)
from backend.app.domains.teams.transitions import validate_team_transition
from backend.app.shared.types.states import (
    ExpeditionStatus,
    MissionStatus,
    PersonReadiness,
    PersonMovement,
    TeamStatus,
    HardSoftConstraint,
)
from backend.app.shared.schemas.envelope import (
    create_success_response,
    create_error_response,
    ApiErrorItem,
)


from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Import all models so Base knows all tables for test harness
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.people.models
import backend.app.domains.teams.models
import backend.app.domains.time_windows.models
import backend.app.platform.events.models
import backend.app.platform.audit.models


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture with isolated in-memory test database."""
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


# ============================================================
# 1. PLATFORM & HEALTH TESTS
# ============================================================

def test_root_health_endpoint(client):
    """Verifies GET /health returns safe operational diagnostics."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] is None
    assert "data" in body
    data = body["data"]
    assert "application" in data
    assert "status" in data
    assert "database" in data
    # Credentials must NOT be exposed
    raw_text = response.text.lower()
    assert "password" not in raw_text or "password=******" in raw_text
    assert "service_role" not in raw_text


def test_api_v1_health_endpoint(client):
    """Verifies GET /api/v1/health returns versioned operational diagnostics."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] is None
    data = body["data"]
    assert data["api_prefix"] == "/api/v1"
    assert data["status"] in ["HEALTHY", "DEGRADED"]


def test_request_id_correlation_middleware(client):
    """Verifies X-Request-ID propagation and auto-generation."""
    custom_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id
    body = response.json()
    assert body["meta"]["correlation_id"] == custom_id

    # Auto-generation when absent
    response_auto = client.get("/health")
    auto_id = response_auto.headers.get("X-Request-ID")
    assert auto_id is not None
    assert len(auto_id) > 10


def test_standard_envelope_formatting():
    """Verifies envelope conforms exactly to docs/API_CONTRACT_POLICY.md."""
    # Success Envelope
    success = create_success_response(data={"item": 1}, correlation_id="req-123")
    assert success["data"] == {"item": 1}
    assert success["meta"]["correlation_id"] == "req-123"
    assert success["meta"]["version"] == "v1"
    assert success["errors"] is None

    # Error Envelope
    err = ApiErrorItem(code="TEST_CODE", message="Test message", field="test_field")
    error_env = create_error_response([err], correlation_id="req-456")
    assert error_env["data"] is None
    assert error_env["meta"]["correlation_id"] == "req-456"
    assert len(error_env["errors"]) == 1
    assert error_env["errors"][0]["code"] == "TEST_CODE"


def test_structured_404_error_envelope(client):
    """Verifies 404 returns structured error envelope."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/expeditions/{non_existent_id}")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["errors"] is not None
    assert len(body["errors"]) > 0
    assert body["errors"][0]["code"] == "EXPEDITION_NOT_FOUND"


# ============================================================
# 2. STATE TRANSITION UNIT TESTS
# ============================================================

def test_expedition_transition_rules():
    """Verifies deterministic expedition state machine."""
    # Valid transition
    evt = validate_expedition_transition("DRAFT", "PLANNED")
    assert evt == "ExpeditionPlanned"

    evt_active = validate_expedition_transition("MOBILIZATION", "ACTIVE")
    assert evt_active == "ExpeditionActivated"

    # Illegal transition: ARCHIVED -> ACTIVE
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_expedition_transition("ARCHIVED", "ACTIVE")
    assert exc_info.value.code == "EXPEDITION_STATE_TRANSITION_INVALID"
    assert "ARCHIVED" in exc_info.value.message


def test_mission_transition_rules():
    """Verifies deterministic mission state machine."""
    # Valid transition
    evt = validate_mission_transition("PROPOSED", "APPROVED")
    assert evt == "MissionApproved"

    evt_done = validate_mission_transition("IN_PROGRESS", "COMPLETED")
    assert evt_done == "MissionCompleted"

    # Exception transition
    evt_block = validate_mission_transition("APPROVED", "BLOCKED")
    assert evt_block == "MissionBlocked"

    # Strictly forbidden: COMPLETED -> IN_PROGRESS
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        validate_mission_transition("COMPLETED", "IN_PROGRESS")
    assert exc_info.value.code == "MISSION_STATE_TRANSITION_INVALID"


def test_personnel_transition_rules():
    """Verifies dual-state transitions for personnel."""
    # Readiness transition
    evt_r = validate_readiness_transition("NOMINATED", "CLEARANCE_PENDING")
    assert evt_r == "PersonClearancePending"

    evt_cleared = validate_readiness_transition("CLEARANCE_PENDING", "READY")
    assert evt_cleared == "PersonCleared"

    # Illegal readiness transition: READY -> NOT_CLEARED directly without CLEARANCE_PENDING
    with pytest.raises(InvalidStateTransitionError):
        validate_readiness_transition("READY", "NOT_CLEARED")

    # Movement transition
    evt_m = validate_movement_transition("NOT_DEPLOYED", "IN_TRANSIT")
    assert evt_m == "PersonDeparted"

    evt_field = validate_movement_transition("AT_STATION", "FIELD")
    assert evt_field == "PersonEnteredField"


def test_team_transition_rules():
    """Verifies team lifecycle transitions."""
    evt = validate_team_transition("FORMING", "READY")
    assert evt == "TeamReady"

    evt_field = validate_team_transition("DEPLOYED", "FIELD")
    assert evt_field == "TeamEnteredField"

    # Illegal transition: FIELD -> FORMING directly
    with pytest.raises(InvalidStateTransitionError):
        validate_team_transition("FIELD", "FORMING")


# ============================================================
# 3. EXPEDITION DOMAIN API INTEGRATION TESTS
# ============================================================

def test_expedition_crud_and_events(client):
    """Tests creating, fetching, updating, and summarizing expeditions with operational events."""
    unique_suffix = uuid.uuid4().hex[:6]
    code = f"EXP-TEST-{unique_suffix}"
    payload = {
        "code": code,
        "name": f"Test Expedition {unique_suffix}",
        "season": "2026-2027",
        "objective": "Validation of polar logistics backend",
        "status": "DRAFT",
        "priority": 1,
        "data_provenance": "SYNTHETIC_DEMO"
    }

    # 1. Create Expedition
    create_resp = client.post("/api/v1/expeditions", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()["data"]
    expedition_id = created_data["id"]
    assert created_data["code"] == code
    assert created_data["status"] == "DRAFT"

    # 2. Verify List Expeditions includes the created one
    list_resp = client.get(f"/api/v1/expeditions?season=2026-2027")
    assert list_resp.status_code == 200
    assert any(e["id"] == expedition_id for e in list_resp.json()["data"])
    assert list_resp.json()["meta"]["pagination"] is not None

    # 3. Valid State Transition: DRAFT -> PLANNED
    patch_resp = client.patch(f"/api/v1/expeditions/{expedition_id}", json={"status": "PLANNED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["status"] == "PLANNED"

    # 4. Invalid State Transition: PLANNED -> ARCHIVED (must be 409 conflict)
    invalid_patch = client.patch(f"/api/v1/expeditions/{expedition_id}", json={"status": "ARCHIVED"})
    assert invalid_patch.status_code == 409
    assert invalid_patch.json()["errors"][0]["code"] == "EXPEDITION_STATE_TRANSITION_INVALID"

    # 5. Verify Operational Events were emitted for the expedition
    events_resp = client.get(f"/api/v1/entities/EXPEDITION/{expedition_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["data"]
    assert len(events) >= 2  # ExpeditionCreated + ExpeditionPlanned
    event_types = [e["event_type"] for e in events]
    assert "ExpeditionCreated" in event_types
    assert "ExpeditionPlanned" in event_types

    # 6. Verify Summary View
    summary_resp = client.get(f"/api/v1/expeditions/{expedition_id}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()["data"]
    assert "mission_count" in summary
    assert "team_count" in summary
    assert "personnel_count" in summary
    assert "readiness_score" not in summary  # No fake scores rule!


# ============================================================
# 4. MISSION DOMAIN API INTEGRATION TESTS
# ============================================================

def test_mission_lifecycle_and_relationships(client):
    """Tests mission creation, transition, event emission, and cross-domain read endpoints."""
    # First get a valid expedition (EXP-26-A or our test expedition)
    exp_resp = client.get("/api/v1/expeditions")
    assert exp_resp.status_code == 200
    expeditions = exp_resp.json()["data"]
    assert len(expeditions) > 0
    expedition_id = expeditions[0]["id"]

    unique_suffix = uuid.uuid4().hex[:6]
    code = f"M-TEST-{unique_suffix}"
    mission_payload = {
        "code": code,
        "title": f"Scientific Core Drilling {unique_suffix}",
        "description": "Ice sheet thermal logging and sample extraction",
        "type": "FIELD_SCIENCE",
        "expedition_id": expedition_id,
        "status": "PROPOSED",
        "priority": 1,
        "data_provenance": "SYNTHETIC_DEMO"
    }

    # 1. Create Mission
    create_resp = client.post("/api/v1/missions", json=mission_payload)
    assert create_resp.status_code == 201
    mission_data = create_resp.json()["data"]
    mission_id = mission_data["id"]

    # 2. Valid Transition: PROPOSED -> APPROVED
    patch_resp = client.patch(f"/api/v1/missions/{mission_id}", json={"status": "APPROVED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["status"] == "APPROVED"

    # 3. Invalid Transition: APPROVED -> COMPLETED
    invalid_patch = client.patch(f"/api/v1/missions/{mission_id}", json={"status": "COMPLETED"})
    assert invalid_patch.status_code == 409
    assert invalid_patch.json()["errors"][0]["code"] == "MISSION_STATE_TRANSITION_INVALID"

    # 4. Cross-domain relationship read endpoint (Person B contract)
    rel_resp = client.get(f"/api/v1/missions/{mission_id}/relationships")
    assert rel_resp.status_code == 200
    assert isinstance(rel_resp.json()["data"], list)

    # 5. Cross-domain time windows read endpoint (Person B contract)
    tw_resp = client.get(f"/api/v1/missions/{mission_id}/time-windows")
    assert tw_resp.status_code == 200
    assert isinstance(tw_resp.json()["data"], list)

    # 6. Events emitted
    events_resp = client.get(f"/api/v1/entities/MISSION/{mission_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["data"]
    assert any(e["event_type"] == "MissionCreated" for e in events)
    assert any(e["event_type"] == "MissionApproved" for e in events)


# ============================================================
# 5. PERSONNEL DOMAIN API INTEGRATION TESTS
# ============================================================

def test_people_dual_state_and_updates(client):
    """Tests personnel enrollment, readiness changes, and movement changes."""
    exp_resp = client.get("/api/v1/expeditions")
    expedition_id = exp_resp.json()["data"][0]["id"]

    unique_suffix = uuid.uuid4().hex[:6]
    person_code = f"P-TEST-{unique_suffix}"
    payload = {
        "person_code": person_code,
        "full_name": f"Dr. Polar Scientist {unique_suffix}",
        "role": "Field Geophysicist",
        "organization": "National Polar Research Institute",
        "expedition_id": expedition_id,
        "readiness_state": "NOMINATED",
        "movement_state": "NOT_DEPLOYED",
        "data_provenance": "SYNTHETIC_DEMO"
    }

    # 1. Create Person
    create_resp = client.post("/api/v1/people", json=payload)
    assert create_resp.status_code == 201
    person_data = create_resp.json()["data"]
    person_id = person_data["id"]
    assert person_data["readiness_state"] == "NOMINATED"
    assert person_data["movement_state"] == "NOT_DEPLOYED"

    # 2. Update Readiness (Dedicated endpoint: NOMINATED -> CLEARANCE_PENDING)
    r_resp = client.patch(f"/api/v1/people/{person_id}/readiness", json={"readiness_state": "CLEARANCE_PENDING"})
    assert r_resp.status_code == 200
    assert r_resp.json()["data"]["readiness_state"] == "CLEARANCE_PENDING"

    # 3. Update Movement (Dedicated endpoint: NOT_DEPLOYED -> IN_TRANSIT)
    m_resp = client.patch(f"/api/v1/people/{person_id}/movement", json={"movement_state": "IN_TRANSIT"})
    assert m_resp.status_code == 200
    assert m_resp.json()["data"]["movement_state"] == "IN_TRANSIT"

    # 4. Verify Person Events
    events_resp = client.get(f"/api/v1/entities/PERSON/{person_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["data"]
    assert len(events) >= 3  # PersonNominated, PersonClearancePending, PersonDeparted
    event_types = [e["event_type"] for e in events]
    assert "PersonNominated" in event_types
    assert "PersonClearancePending" in event_types
    assert "PersonDeparted" in event_types


# ============================================================
# 6. TEAMS DOMAIN API & INVARIANT INTEGRATION TESTS
# ============================================================

def test_team_rules_and_invariants(client):
    """Tests team creation, same-expedition validation, and leader validation."""
    exp_resp = client.get("/api/v1/expeditions")
    expeditions = exp_resp.json()["data"]
    exp1_id = expeditions[0]["id"]

    unique_suffix = uuid.uuid4().hex[:6]
    team_code = f"T-TEST-{unique_suffix}"
    team_payload = {
        "code": team_code,
        "name": f"Deep Field Recon {unique_suffix}",
        "expedition_id": exp1_id,
        "status": "FORMING",
        "data_provenance": "SYNTHETIC_DEMO"
    }

    # 1. Create Team
    create_resp = client.post("/api/v1/teams", json=team_payload)
    assert create_resp.status_code == 201
    team_data = create_resp.json()["data"]
    team_id = team_data["id"]

    # 2. Create person in same expedition
    p_code = f"P-LEAD-{unique_suffix}"
    p_resp = client.post("/api/v1/people", json={
        "person_code": p_code,
        "full_name": "Team Leader Candidate",
        "role": "Traverse Commander",
        "expedition_id": exp1_id,
        "team_id": team_id
    })
    assert p_resp.status_code == 201
    leader_id = p_resp.json()["data"]["id"]

    # 3. Assign leader to team
    patch_resp = client.patch(f"/api/v1/teams/{team_id}", json={"leader_person_id": leader_id})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["leader_person_id"] == leader_id

    # 4. Verify team members list
    members_resp = client.get(f"/api/v1/teams/{team_id}/members")
    assert members_resp.status_code == 200
    members = members_resp.json()["data"]
    assert any(m["id"] == leader_id for m in members)


# ============================================================
# 7. TIME WINDOWS DOMAIN INTEGRATION TESTS
# ============================================================

def test_time_window_temporal_invariants(client):
    """Tests time window bounds checking (close_at > open_at is mandatory)."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=4)
    past = now - timedelta(hours=4)

    # Valid time window
    valid_payload = {
        "type": "WEATHER_WINDOW",
        "open_at": now.isoformat(),
        "close_at": future.isoformat(),
        "hard_or_soft": "HARD",
        "subject_type": "MISSION",
        "subject_id": str(uuid.uuid4()),
        "status": "OPEN",
        "description": "Clear polar sky flight window"
    }
    create_resp = client.post("/api/v1/time-windows", json=valid_payload)
    assert create_resp.status_code == 201
    window_id = create_resp.json()["data"]["id"]

    # Invalid time window: close_at is BEFORE open_at
    invalid_payload = {
        "type": "WEATHER_WINDOW",
        "open_at": now.isoformat(),
        "close_at": past.isoformat(),  # Invalid!
        "hard_or_soft": "HARD",
        "subject_type": "MISSION",
        "subject_id": str(uuid.uuid4()),
        "status": "OPEN",
        "description": "Impossible inverted window"
    }
    invalid_resp = client.post("/api/v1/time-windows", json=invalid_payload)
    assert invalid_resp.status_code == 422
    assert invalid_resp.json()["errors"][0]["code"] in ["DOMAIN_VALIDATION_FAILED", "REQUEST_VALIDATION_ERROR"]


# ============================================================
# 8. OPERATIONAL EVENTS PLATFORM & IMMUTABILITY TESTS
# ============================================================

def test_events_list_and_immutability(client):
    """Tests operational events querying and verifies no mutating endpoints exist."""
    list_resp = client.get("/api/v1/events?page=1&page_size=10")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["errors"] is None
    assert isinstance(body["data"], list)
    assert body["meta"]["pagination"] is not None

    if len(body["data"]) > 0:
        evt_id = body["data"][0]["id"]
        # GET single event
        single_resp = client.get(f"/api/v1/events/{evt_id}")
        assert single_resp.status_code == 200
        assert single_resp.json()["data"]["id"] == evt_id

    # IMMUTABILITY: POST / PATCH / DELETE must NOT be supported on /events
    assert client.post("/api/v1/events", json={}).status_code == 405
    assert client.delete("/api/v1/events/some-id").status_code == 405
    assert client.patch("/api/v1/events/some-id", json={}).status_code == 405
