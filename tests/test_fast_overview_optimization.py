"""
Test Suite for Fast Control Tower Overview Optimization (Phase 2-5).
Verifies:
1. GET /api/v1/control-tower/overview/fast returns HTTP 200 with standard ApiResponse envelope
2. Correct expedition context and mission status rollups
3. Accurate incident, replan, recommendation, and approval counts
4. Offline sync summary and recent operational events
5. Strict expedition isolation when expedition_id is provided
6. Query count acceptance criterion: get_fast_overview() <= 8 SQL queries
7. Zero invocation of deep readiness, runway, or personnel safety services
8. Backward compatibility of legacy GET /api/v1/control-tower/overview
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.incidents.models import IncidentModel
from backend.app.domains.sync.models import OfflineOperationModel
from backend.app.platform.events.models import OperationalEventModel
from backend.app.domains.replanning.models import (
    ReplanModel,
    RecommendationModel,
    ApprovalModel,
)
from backend.app.domains.replanning.states import (
    ReplanStatus,
    RecommendationStatus,
    ApprovalStatus,
)
from backend.app.services.constraints.models import ConstraintModel
from backend.app.domains.control_tower.service import ControlTowerService
from backend.app.domains.control_tower.schemas import ControlTowerOverview


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    conn = engine.connect()
    trans = conn.begin()
    SessionLocal = sessionmaker(bind=conn)
    db = SessionLocal()

    yield db

    db.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_data(session):
    now = datetime.now(timezone.utc)

    # Expedition 1
    exp1_id = uuid.uuid4()
    exp1 = ExpeditionModel(
        id=exp1_id,
        code="EXP-TEST-1",
        name="45th Test Polar Campaign",
        season="2026-2027",
        status="ACTIVE",
    )
    session.add(exp1)

    # Expedition 2
    exp2_id = uuid.uuid4()
    exp2 = ExpeditionModel(
        id=exp2_id,
        code="EXP-TEST-2",
        name="46th Test Polar Campaign",
        season="2027-2028",
        status="PLANNED",
    )
    session.add(exp2)

    # Location
    loc1 = LocationModel(
        id=uuid.uuid4(),
        code="LOC-TEST-1",
        name="Maitri Main Station",
        type="STATION",
    )
    session.add(loc1)

    # Missions for Exp 1
    m1 = MissionModel(
        id=uuid.uuid4(),
        expedition_id=exp1_id,
        code="M-01",
        title="Glaciology Survey",
        type="SCIENTIFIC",
        status="READY",
        location_id=loc1.id,
    )
    m2 = MissionModel(
        id=uuid.uuid4(),
        expedition_id=exp1_id,
        code="M-02",
        title="Ice Core Drilling",
        type="SCIENTIFIC",
        status="BLOCKED",
        location_id=loc1.id,
    )
    session.add_all([m1, m2])

    # Mission for Exp 2
    m3 = MissionModel(
        id=uuid.uuid4(),
        expedition_id=exp2_id,
        code="M-03",
        title="Seismology Run",
        type="SCIENTIFIC",
        status="AT_RISK",
    )
    session.add(m3)

    # Incident for Exp 1
    inc1 = IncidentModel(
        id=uuid.uuid4(),
        expedition_id=exp1_id,
        incident_code="INC-001",
        title="Fuel Generator Warning",
        type="EQUIPMENT",
        status="ACTIVE",
        severity="MEDIUM",
    )
    session.add(inc1)

    # Replan, Rec, Approval for Exp 1
    rep1 = ReplanModel(
        id=uuid.uuid4(),
        expedition_id=exp1_id,
        replan_code="REP-001",
        status=ReplanStatus.REQUESTED.value,
        trigger_reason="Generator issue",
    )
    session.add(rep1)

    rec1 = RecommendationModel(
        id=uuid.uuid4(),
        replan_id=rep1.id,
        title="Reroute Generator Fuel",
        status=RecommendationStatus.PROPOSED.value,
        approval_state="PENDING",
    )
    session.add(rec1)

    from backend.app.domains.people.models import PersonModel
    person1 = PersonModel(
        id=uuid.uuid4(),
        person_code="PRS-TEST-1",
        full_name="Dr. Test User",
        role="OPERATIONS_DIRECTOR",
        expedition_id=exp1_id,
    )
    session.add(person1)

    appr1 = ApprovalModel(
        id=uuid.uuid4(),
        recommendation_id=rec1.id,
        approver_person_id=person1.id,
        approver_role="OPERATIONS_DIRECTOR",
        status=ApprovalStatus.PENDING.value,
    )
    session.add(appr1)

    # Offline sync operation
    sync1 = OfflineOperationModel(
        id=uuid.uuid4(),
        operation_id=uuid.uuid4(),
        entity_type="INVENTORY",
        operation_type="INVENTORY_COUNT",
        status="COMPLETED",
        payload={},
    )
    session.add(sync1)

    # Operational Event
    ev1 = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="EXPEDITION_STATUS_CHANGED",
        entity_type="EXPEDITION",
        entity_id=exp1_id,
        occurred_at=now,
        source="TEST",
    )
    session.add(ev1)

    session.flush()

    return {
        "exp1": exp1,
        "exp2": exp2,
        "m1": m1,
        "m2": m2,
        "m3": m3,
        "inc1": inc1,
        "rep1": rep1,
        "rec1": rec1,
        "appr1": appr1,
    }


def test_fast_overview_http_200_and_envelope(client, test_data):
    """Fast overview endpoint responds with HTTP 200 and standard envelope."""
    res = client.get("/api/v1/control-tower/overview/fast")
    assert res.status_code == 200

    payload = res.json()
    assert payload["errors"] is None
    assert payload["data"] is not None
    data = payload["data"]
    assert data["total_expeditions"] >= 2
    assert data["total_missions"] >= 3
    assert data["data_provenance"] == "DERIVED"


def test_fast_overview_expedition_context_and_mission_rollups(client, test_data):
    """Verifies expedition identity, status, and mission rollup counts in fast overview."""
    res = client.get("/api/v1/control-tower/overview/fast")
    assert res.status_code == 200
    data = res.json()["data"]

    expeditions = data["expeditions"]
    assert len(expeditions) >= 2
    codes = [e["code"] for e in expeditions]
    assert "EXP-TEST-1" in codes
    assert "EXP-TEST-2" in codes

    # Check mission counts
    assert data["missions_by_readiness"]["READY"] >= 1
    assert data["missions_by_readiness"]["BLOCKED"] >= 1
    assert data["missions_by_readiness"]["AT_RISK"] >= 1


def test_fast_overview_incident_replan_approval_counts(client, test_data):
    """Verifies counts for active incidents, pending replans, and approvals."""
    res = client.get("/api/v1/control-tower/overview/fast")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["active_incidents_count"] >= 1
    assert data["pending_replans_count"] >= 1
    assert data["pending_recommendations_count"] >= 1
    assert data["pending_approvals_count"] >= 1


def test_fast_overview_offline_sync_and_recent_events(client, test_data):
    """Verifies offline sync summary and recent operational events are present."""
    res = client.get("/api/v1/control-tower/overview/fast")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "COMPLETED" in data["offline_sync_summary"]
    assert len(data["recent_operational_events"]) >= 1


def test_fast_overview_expedition_isolation(client, test_data):
    """When expedition_id query param is passed, results are isolated to that campaign."""
    exp1 = test_data["exp1"]
    res = client.get(f"/api/v1/control-tower/overview/fast?expedition_id={exp1.id}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total_expeditions"] == 1
    assert data["expeditions"][0]["expedition_id"] == str(exp1.id)
    assert data["expeditions"][0]["code"] == "EXP-TEST-1"
    assert data["total_missions"] == 2  # Only M-01 and M-02
    assert data["active_incidents_count"] == 1


def test_fast_overview_query_count_under_threshold(session, test_data):
    """
    CRITICAL ACCEPTANCE TEST:
    ControlTowerService.get_fast_overview() MUST execute <= 8 SQL queries.
    """
    query_log = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        query_log.append(statement)

    event.listen(session.bind, "before_cursor_execute", before_cursor_execute)
    try:
        service = ControlTowerService(session)
        overview = service.get_fast_overview()
        assert isinstance(overview, ControlTowerOverview)
        assert len(query_log) <= 8, f"Query count exceeded threshold! Executed {len(query_log)} queries."
    finally:
        event.remove(session.bind, "before_cursor_execute", before_cursor_execute)


def test_fast_overview_does_not_invoke_expensive_services(session, test_data):
    """
    Verifies that get_fast_overview() NEVER invokes deep readiness,
    resource runway, or personnel safety services.
    """
    with patch("backend.app.services.readiness.mission.MissionReadinessService.evaluate") as mock_mission_eval, \
         patch("backend.app.services.readiness.expedition.ExpeditionReadinessService.evaluate") as mock_exp_eval, \
         patch("backend.app.domains.inventory.runway.ResourceRunwayService.get_expedition_runways") as mock_runway, \
         patch("backend.app.domains.control_tower.personnel_safety.PersonnelSafetyService.evaluate_expedition") as mock_safety:

        service = ControlTowerService(session)
        overview = service.get_fast_overview()

        assert mock_mission_eval.call_count == 0
        assert mock_exp_eval.call_count == 0
        assert mock_runway.call_count == 0
        assert mock_safety.call_count == 0
        assert overview.total_expeditions >= 2


def test_legacy_overview_endpoint_remains_functional(client, test_data):
    """Verifies that legacy GET /api/v1/control-tower/overview continues to work as expected."""
    res = client.get("/api/v1/control-tower/overview")
    assert res.status_code == 200
    payload = res.json()
    assert payload["errors"] is None
    assert payload["data"]["total_expeditions"] >= 2
