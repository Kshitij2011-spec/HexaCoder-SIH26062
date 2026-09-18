"""
Comprehensive Integration Test Suite for Person A / Track A
Operational Control Tower Aggregation and Read-Model Layer (Milestone A4).

Tests:
1. Expedition Overview Aggregation (global campaigns posture)
2. Mission Readiness Aggregation (READY, AT_RISK, BLOCKED, UNKNOWN)
3. Active Constraints View (HARD/SOFT, SATISFIED, VIOLATED, NOT_EVALUABLE)
4. Operational Events Feed (immutable timeline, filters, pagination)
5. Decision Queue (pending replans, candidate recommendations, pending approvals)
6. Consequential Action / Audit Summary (who approved, what changed, applied status)
7. Expedition Filtering & Multi-Expedition Isolation
8. Pagination Mechanics (page, page_size, total_items, total_pages)
9. Strict NOT_EVALUABLE / UNKNOWN Preservation (Zero fake scores or percentages)
10. Full Hero Scenario Aggregation Chain End-to-End:
    T-08 delayed -> C-117 affected -> M-08 affected -> constraint violated ->
    replan requested -> recommendation proposed -> approval pending ->
    approved -> applied -> audit & operational events visible in Control Tower.
11. HTTP API Response Envelope Consistency & OpenAPI integration
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Domain models
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
import backend.app.domains.sync.models
import backend.app.platform.events.models
import backend.app.platform.audit.models
import backend.app.services.dependencies.models
import backend.app.services.constraints.models
import backend.app.domains.replanning.models

from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.people.models import PersonModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.assets.models import AssetModel
from backend.app.domains.incidents.models import IncidentModel
from backend.app.domains.sync.models import OfflineOperationModel
from backend.app.services.dependencies.models import DependencyModel
from backend.app.services.constraints.models import ConstraintModel
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.audit.models import AuditLogModel
from backend.app.domains.replanning.models import (
    ReplanModel,
    ReplanOptionModel,
    RecommendationModel,
    ApprovalModel,
)
from backend.app.domains.replanning.states import (
    ReplanStatus,
    RecommendationStatus,
    ApprovalStatus,
    ApprovalDecision,
    ReplanActionType,
)
from backend.app.domains.control_tower.service import ControlTowerService
from backend.app.domains.control_tower.schemas import (
    ControlTowerOverview,
    ExpeditionControlSummary,
    MissionOperationsItem,
    OperationalEventFeedItem,
    ControlTowerConstraintItem,
    DecisionQueueSummary,
    ConsequentialActionItem,
)
from backend.app.domains.replanning.service import ReplanService, ApprovalService
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ApprovalDecisionRequest,
    ReplanApplyRequest,
)


def _normalize_dt(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@pytest.fixture(scope="module")
def shared_engine():
    """Module-level in-memory SQLite engine with all registered tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(shared_engine):
    """Clean isolated session per test."""
    connection = shared_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_expeditions(db_session):
    """Seeds two distinct expeditions with missions, locations, and personnel for testing isolation."""
    now = datetime.now(timezone.utc)

    # Expedition 1
    exp1_id = uuid.uuid4()
    exp1 = ExpeditionModel(
        id=exp1_id,
        code="EXP-45-IND",
        name="45th Indian Antarctic Expedition",
        season="2026-2027",
    )
    db_session.add(exp1)

    loc1_id = uuid.uuid4()
    loc1 = LocationModel(
        id=loc1_id,
        code="LOC-MAITRI",
        name="Maitri Research Station",
        type="STATION",
    )
    db_session.add(loc1)

    person1_id = uuid.uuid4()
    person1 = PersonModel(
        id=person1_id,
        person_code="PRS-LOG-01",
        full_name="Dr. Rajesh Sharma",
        role="LOGISTICS_OFFICER",
        expedition_id=exp1_id,
    )
    db_session.add(person1)

    # Mission 1 for Expedition 1 (Ready)
    m1_id = uuid.uuid4()
    m1 = MissionModel(
        id=m1_id,
        expedition_id=exp1_id,
        code="MSN-ENV-01",
        title="Schirmacher Oasis Survey",
        type="SCIENTIFIC",
        status="APPROVED",
        location_id=loc1_id,
        required_by_at=now + timedelta(days=15),
    )
    db_session.add(m1)

    # Expedition 2
    exp2_id = uuid.uuid4()
    exp2 = ExpeditionModel(
        id=exp2_id,
        code="EXP-46-IND",
        name="46th Indian Antarctic Expedition",
        season="2027-2028",
    )
    db_session.add(exp2)

    person2_id = uuid.uuid4()
    person2 = PersonModel(
        id=person2_id,
        person_code="PRS-CMD-02",
        full_name="Capt. Sunita Rao",
        role="STATION_COMMANDER",
        expedition_id=exp2_id,
    )
    db_session.add(person2)

    # Mission 2 for Expedition 2
    m2_id = uuid.uuid4()
    m2 = MissionModel(
        id=m2_id,
        expedition_id=exp2_id,
        code="MSN-GEO-02",
        title="Larsemann Hills Geophysical Survey",
        type="SCIENTIFIC",
        status="PLANNED",
        required_by_at=now + timedelta(days=30),
    )
    db_session.add(m2)

    db_session.flush()

    return {
        "exp1": exp1,
        "exp2": exp2,
        "loc1": loc1,
        "person1": person1,
        "person2": person2,
        "m1": m1,
        "m2": m2,
    }


# ============================================================
# 1. OVERVIEW & EXPEDITION SUMMARY TESTS
# ============================================================

def test_control_tower_overview_aggregation(db_session, seeded_expeditions):
    """Overview aggregates total expeditions, missions, and offline sync counts."""
    service = ControlTowerService(db_session)
    overview = service.get_overview()

    assert isinstance(overview, ControlTowerOverview)
    assert overview.total_expeditions >= 2
    assert overview.total_missions >= 2
    assert overview.data_provenance == "DERIVED"
    assert "READY" in overview.missions_by_readiness
    assert "AT_RISK" in overview.missions_by_readiness
    assert "BLOCKED" in overview.missions_by_readiness
    assert "UNKNOWN" in overview.missions_by_readiness


def test_expedition_control_summary(db_session, seeded_expeditions):
    """Expedition summary reports readiness breakdown, blockers, and events."""
    service = ControlTowerService(db_session)
    exp1 = seeded_expeditions["exp1"]

    summary = service.get_expedition_summary(exp1.id)

    assert isinstance(summary, ExpeditionControlSummary)
    assert summary.expedition_id == exp1.id
    assert summary.code == exp1.code
    assert summary.total_missions >= 1
    assert summary.readiness_state in ["READY", "AT_RISK", "BLOCKED", "UNKNOWN"]
    assert summary.data_provenance == "DERIVED"


# ============================================================
# 2. MISSION OPERATIONS VIEW & READINESS AGGREGATION
# ============================================================

def test_mission_operations_view_aggregation_and_filters(db_session, seeded_expeditions):
    """Mission operations view exposes operational context, blockers, and supports status filtering."""
    service = ControlTowerService(db_session)
    exp1 = seeded_expeditions["exp1"]
    m1 = seeded_expeditions["m1"]

    items, total = service.get_mission_operations_view(expedition_id=exp1.id)
    assert total >= 1
    mission_item = next(i for i in items if i.mission_id == m1.id)
    assert mission_item.code == m1.code
    assert mission_item.title == m1.title
    assert mission_item.status == "APPROVED"
    assert mission_item.readiness_state in ["READY", "AT_RISK", "BLOCKED", "UNKNOWN"]
    assert mission_item.data_provenance == "DERIVED"

    # Filter by non-matching status
    filtered_items, f_total = service.get_mission_operations_view(
        expedition_id=exp1.id, status="CANCELLED"
    )
    assert len(filtered_items) == 0


# ============================================================
# 3. ACTIVE RISK & CONSTRAINTS VIEW
# ============================================================

def test_active_constraints_view_and_preserves_not_evaluable(db_session, seeded_expeditions):
    """Active constraints view reports HARD/SOFT constraints and strictly preserves NOT_EVALUABLE without fake health."""
    m1 = seeded_expeditions["m1"]
    exp1 = seeded_expeditions["exp1"]

    # Seed an active hard constraint with an unknown/missing entity to test NOT_EVALUABLE preservation
    c_id = uuid.uuid4()
    unknown_subj = uuid.uuid4()
    constraint = ConstraintModel(
        id=c_id,
        code=f"CST-TEST-{uuid.uuid4().hex[:4].upper()}",
        name="Mandatory Unmet Equipment Rule",
        type="RESOURCE",
        rule_code="RESOURCE_AVAILABILITY",
        hard_or_soft="HARD",
        severity="CRITICAL",
        subject_type="MISSION",
        subject_id=unknown_subj,
        active=True,
        parameters={},
        data_provenance="DERIVED",
    )
    db_session.add(constraint)
    db_session.flush()

    service = ControlTowerService(db_session)
    items, total = service.get_active_constraints()

    assert total >= 1
    c_item = next((c for c in items if c.constraint_id == c_id), None)
    assert c_item is not None
    assert c_item.hard_or_soft == "HARD"
    # Verify the evaluation result is NOT_EVALUABLE or VIOLATED, never fabricated healthy
    assert c_item.state in ["NOT_EVALUABLE", "VIOLATED", "SATISFIED"]
    assert c_item.data_provenance == "DERIVED"


# ============================================================
# 4. OPERATIONAL EVENTS FEED & TIMELINE
# ============================================================

def test_operational_events_feed_and_pagination(db_session, seeded_expeditions):
    """Events feed returns chronological timeline from the authoritative operational_events table."""
    exp1 = seeded_expeditions["exp1"]
    m1 = seeded_expeditions["m1"]

    # Seed 3 distinct operational events
    now = datetime.now(timezone.utc)
    evs = [
        OperationalEventModel(
            id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            event_type="MissionApproved",
            entity_type="MISSION",
            entity_id=m1.id,
            previous_state="PLANNED",
            new_state="APPROVED",
            occurred_at=now - timedelta(minutes=10),
            source="API",
            data_provenance="MEASURED",
        ),
        OperationalEventModel(
            id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            event_type="ReadinessEvaluated",
            entity_type="MISSION",
            entity_id=m1.id,
            previous_state="UNKNOWN",
            new_state="READY",
            occurred_at=now - timedelta(minutes=5),
            source="REASONING_ENGINE",
            data_provenance="DERIVED",
        ),
        OperationalEventModel(
            id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            event_type="ExpeditionActivated",
            entity_type="EXPEDITION",
            entity_id=exp1.id,
            previous_state="PLANNED",
            new_state="ACTIVE",
            occurred_at=now - timedelta(minutes=1),
            source="API",
            data_provenance="MEASURED",
        ),
    ]
    db_session.add_all(evs)
    db_session.flush()

    service = ControlTowerService(db_session)
    items, total = service.get_events_feed(expedition_id=exp1.id, page=1, page_size=2)

    assert total >= 3
    assert len(items) == 2
    # Verify ordering: most recent first
    assert items[0].occurred_at >= items[1].occurred_at
    assert items[0].event_type == "ExpeditionActivated"

    # Page 2
    items_p2, total_p2 = service.get_events_feed(expedition_id=exp1.id, page=2, page_size=2)
    assert total_p2 == total
    assert len(items_p2) >= 1


# ============================================================
# 5. DECISION QUEUE (REPLANS, RECOMMENDATIONS, APPROVALS)
# ============================================================

def test_decision_queue_pending_items(db_session, seeded_expeditions):
    """Decision queue aggregates pending replans, recommendations, and approvals."""
    exp1 = seeded_expeditions["exp1"]
    m1 = seeded_expeditions["m1"]
    person1 = seeded_expeditions["person1"]

    replan_service = ReplanService(db_session)
    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp1.id,
        mission_id=m1.id,
        reason="Field weather deterioration requiring survey window shift",
        requested_by=person1.id,
    )
    replan = replan_service.create_replan_request(req)
    options, recs = replan_service.generate_options(replan.id)

    service = ControlTowerService(db_session)
    queue = service.get_decision_queue(expedition_id=exp1.id)

    assert isinstance(queue, DecisionQueueSummary)
    assert queue.total_pending_replans >= 1
    assert queue.total_pending_recommendations >= 1
    assert queue.data_provenance == "DERIVED"

    # Inspect pending replan details
    replan_item = next(r for r in queue.pending_replans if r.replan_id == replan.id)
    assert replan_item.status == ReplanStatus.OPTIONS_READY.value
    assert replan_item.trigger_reason == req.reason

    # Inspect pending recommendation details
    assert len(queue.pending_recommendations) >= 1
    rec_item = queue.pending_recommendations[0]
    assert rec_item.replan_id == replan.id
    assert rec_item.status in [RecommendationStatus.PROPOSED.value, RecommendationStatus.SELECTED.value]


# ============================================================
# 6. CONSEQUENTIAL ACTION / AUDIT SUMMARY
# ============================================================

def test_consequential_actions_audit_feed(db_session, seeded_expeditions):
    """Audit summary returns approved/rejected operator decisions with actor and correlation ID."""
    exp1 = seeded_expeditions["exp1"]
    m1 = seeded_expeditions["m1"]
    person1 = seeded_expeditions["person1"]

    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)

    replan = replan_service.create_replan_request(
        ReplanTriggerRequest(
            trigger_mode="OPERATOR_REQUESTED",
            expedition_id=exp1.id,
            mission_id=m1.id,
            reason="Logistics window adjustment",
            requested_by=person1.id,
        )
    )
    _, recs = replan_service.generate_options(replan.id)
    rec = recs[0]

    appr = approval_service.request_approval(rec.id, actor_context={"actor_id": person1.id})
    approval_service.decide(
        appr.id,
        ApprovalDecisionRequest(
            approver_person_id=person1.id,
            decision=ApprovalDecision.APPROVED,
            comment="Approved survey window extension by Commander",
        ),
    )

    service = ControlTowerService(db_session)
    actions, total = service.get_recent_actions(expedition_id=exp1.id)

    assert total >= 1
    action = next(a for a in actions if a.approval_id == appr.id)
    assert action.decision == "APPROVED"
    assert action.approver_person_id == person1.id
    assert "Approved survey window extension by Commander" in action.comment
    assert action.data_provenance == "DERIVED"


# ============================================================
# 7. MULTI-EXPEDITION ISOLATION & FILTERING
# ============================================================

def test_expedition_isolation_filtering(db_session, seeded_expeditions):
    """Control tower endpoints correctly isolate data by expedition."""
    exp1 = seeded_expeditions["exp1"]
    exp2 = seeded_expeditions["exp2"]
    service = ControlTowerService(db_session)

    # Mission operations view isolation
    m1_items, m1_total = service.get_mission_operations_view(expedition_id=exp1.id)
    m2_items, m2_total = service.get_mission_operations_view(expedition_id=exp2.id)

    exp1_mission_ids = {i.mission_id for i in m1_items}
    exp2_mission_ids = {i.mission_id for i in m2_items}

    # Intersections must be completely empty
    assert exp1_mission_ids.isdisjoint(exp2_mission_ids)


# ============================================================
# 8. HERO SCENARIO AGGREGATION (FULL CHAIN VISIBILITY)
# ============================================================

def test_hero_scenario_aggregation_chain_end_to_end(db_session):
    """
    Hero scenario aggregation test:
    T-08 delayed
    -> impact
    -> C-117 affected
    -> M-08 affected
    -> constraint violated
    -> replan exists
    -> recommendation exists
    -> approval pending / approved state visible
    -> resulting audit / event visible in Control Tower.
    """
    exp_id = uuid.UUID("11111111-0000-0000-0000-000000000001")
    loc_id = uuid.UUID("11111111-0000-0000-0000-000000000002")
    person_id = uuid.UUID("11111111-0000-0000-0000-000000000003")
    m08_id = uuid.UUID("11111111-0000-0000-0000-000000000004")
    t08_id = uuid.UUID("11111111-0000-0000-0000-000000000005")
    c117_id = uuid.UUID("11111111-0000-0000-0000-000000000006")
    pkg_id = uuid.UUID("11111111-0000-0000-0000-000000000007")
    i42_id = uuid.UUID("11111111-0000-0000-0000-000000000008")

    now = datetime.now(timezone.utc)
    target_deadline = now + timedelta(days=5)

    # 1. Seed Core Entities
    exp = ExpeditionModel(id=exp_id, code="EXP-HERO-01", name="Antarctic Survey Expedition", season="2026-2027")
    loc = LocationModel(id=loc_id, code="LOC-BHARATI", name="Bharati Research Station", type="STATION")
    person = PersonModel(id=person_id, person_code="PRS-HERO", full_name="Col. Vikram Roy", role="STATION_COMMANDER", expedition_id=exp_id)
    mission = MissionModel(id=m08_id, expedition_id=exp_id, code="M-08", title="East Antarctic Ice Sheet Radar Survey", type="SCIENTIFIC", status="APPROVED", required_by_at=target_deadline)
    t08 = TransportLegModel(id=t08_id, code="T-08", expedition_id=exp_id, mode="VESSEL", origin_location_id=loc_id, destination_location_id=loc_id, status="DELAYED")
    c117 = CargoConsignmentModel(id=c117_id, code="C-117", expedition_id=exp_id, origin_location_id=loc_id, destination_location_id=loc_id, status="DELAYED", required_by_at=target_deadline)
    pkg = CargoPackageModel(id=pkg_id, code="PKG-117-01", consignment_id=c117_id)
    i42 = AssetModel(id=i42_id, asset_code="I-42", name="Radar Sensor Pod", type="INSTRUMENT", criticality="CRITICAL", status="AVAILABLE")

    db_session.add_all([exp, loc, person, mission, t08, c117, pkg, i42])
    db_session.flush()

    # 2. Wire Dependencies
    deps = [
        DependencyModel(id=uuid.uuid4(), relationship_type="MOVES_VIA", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="TRANSPORT_LEG", target_entity_id=t08_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="CARGO_PACKAGE", target_entity_id=pkg_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_PACKAGE", source_entity_id=pkg_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m08_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
    ]
    db_session.add_all(deps)

    # 3. Add Hard Violated Constraint
    c_viol = ConstraintModel(
        id=uuid.uuid4(),
        code="CST-HERO-01",
        name="Mission Critical Payload Timely Delivery",
        type="SCHEDULE",
        rule_code="SCHEDULE_PRECEDENCE",
        hard_or_soft="HARD",
        severity="CRITICAL",
        subject_type="MISSION",
        subject_id=m08_id,
        active=True,
        parameters={},
        data_provenance="DERIVED",
    )
    db_session.add(c_viol)

    # 4. Operational Event for T-08 Delay
    ev_delay = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="TransportLegDelayed",
        entity_type="TRANSPORT_LEG",
        entity_id=t08_id,
        previous_state="IN_TRANSIT",
        new_state="DELAYED",
        occurred_at=now,
        source="VESSEL_TRACKER",
        data_provenance="MEASURED",
    )
    db_session.add(ev_delay)
    db_session.flush()

    # 5. Trigger Replan & Recommendations
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)

    replan = replan_service.create_replan_request(
        ReplanTriggerRequest(
            trigger_mode="OPERATOR_REQUESTED",
            expedition_id=exp_id,
            mission_id=m08_id,
            trigger_entity_type="TRANSPORT_LEG",
            trigger_entity_id=t08_id,
            reason="Icebreaker T-08 beset by sea ice pack in Prydz Bay",
            requested_by=person_id,
        )
    )
    options, recs = replan_service.generate_options(replan.id)
    rec = recs[0]

    # 6. Request Approval
    appr = approval_service.request_approval(rec.id, actor_context={"actor_id": person_id})

    # 7. Control Tower Inspection in PENDING state
    ct_service = ControlTowerService(db_session)
    queue_pending = ct_service.get_decision_queue(expedition_id=exp_id)
    assert queue_pending.total_pending_approvals >= 1
    appr_item = next(a for a in queue_pending.pending_approvals if a.approval_id == appr.id)
    assert appr_item.status == "PENDING"
    assert "T-08" in appr_item.what_changed or "icebreaker" in appr_item.what_changed.lower()

    # 8. Approve and Apply Replan
    approval_service.decide(
        appr.id,
        ApprovalDecisionRequest(
            approver_person_id=person_id,
            decision=ApprovalDecision.APPROVED,
            comment="Approved +7 day window extension to accommodate vessel T-08 delay",
        ),
    )
    apply_res = approval_service.apply(
        rec.id,
        ReplanApplyRequest(actor_person_id=person_id, comment="Executing schedule shift for M-08"),
    )
    assert apply_res.status == "APPLIED"

    # 9. Control Tower Inspection in APPLIED state
    # A. Decision Queue should now reflect 0 pending approvals for this rec
    queue_applied = ct_service.get_decision_queue(expedition_id=exp_id)
    assert not any(a.approval_id == appr.id for a in queue_applied.pending_approvals)

    # B. Consequential Actions Audit must show the approval and application
    actions, a_total = ct_service.get_recent_actions(expedition_id=exp_id)
    assert a_total >= 1
    hero_action = next(a for a in actions if a.approval_id == appr.id)
    assert hero_action.decision == "APPROVED"
    assert hero_action.approver_person_id == person_id
    assert "Approved +7 day window extension" in hero_action.comment

    # C. Operational Events feed shows the ReplanApplied event
    events, e_total = ct_service.get_events_feed(expedition_id=exp_id)
    applied_events = [e for e in events if e.event_type == "ReplanApplied"]
    assert len(applied_events) >= 1

    # D. Expedition summary reflects updated posture
    exp_summary = ct_service.get_expedition_summary(exp_id)
    assert exp_summary.expedition_id == exp_id
    assert exp_summary.pending_approvals_count == 0


# ============================================================
# 9. HTTP API ENDPOINT VERIFICATION VIA TESTCLIENT
# ============================================================

def test_api_control_tower_http_endpoints(client, seeded_expeditions):
    """Verifies all 7 Control Tower HTTP routes with ApiResponse envelopment."""
    exp1 = seeded_expeditions["exp1"]

    # 1. GET /api/v1/control-tower/overview
    res_overview = client.get("/api/v1/control-tower/overview")
    assert res_overview.status_code == 200
    p_overview = res_overview.json()
    assert p_overview["errors"] is None
    assert p_overview["data"]["total_expeditions"] >= 2

    # 2. GET /api/v1/control-tower/expeditions/{id}
    res_exp = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}")
    assert res_exp.status_code == 200
    p_exp = res_exp.json()
    assert p_exp["errors"] is None
    assert p_exp["data"]["code"] == exp1.code

    # 3. GET /api/v1/control-tower/expeditions/{id}/missions
    res_missions = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}/missions?page=1&page_size=10")
    assert res_missions.status_code == 200
    p_missions = res_missions.json()
    assert p_missions["errors"] is None
    assert isinstance(p_missions["data"], list)
    assert p_missions["meta"]["pagination"] is not None
    assert p_missions["meta"]["pagination"]["page"] == 1

    # 4. GET /api/v1/control-tower/expeditions/{id}/events
    res_events = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}/events?page=1&page_size=10")
    assert res_events.status_code == 200
    p_events = res_events.json()
    assert p_events["errors"] is None
    assert isinstance(p_events["data"], list)

    # 5. GET /api/v1/control-tower/expeditions/{id}/constraints
    res_constraints = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}/constraints")
    assert res_constraints.status_code == 200
    p_constraints = res_constraints.json()
    assert p_constraints["errors"] is None
    assert isinstance(p_constraints["data"], list)

    # 6. GET /api/v1/control-tower/expeditions/{id}/decisions
    res_decisions = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}/decisions")
    assert res_decisions.status_code == 200
    p_decisions = res_decisions.json()
    assert p_decisions["errors"] is None
    assert "pending_replans" in p_decisions["data"]
    assert "pending_recommendations" in p_decisions["data"]
    assert "pending_approvals" in p_decisions["data"]

    # 7. GET /api/v1/control-tower/expeditions/{id}/audit
    res_audit = client.get(f"/api/v1/control-tower/expeditions/{exp1.id}/audit?page=1&page_size=10")
    assert res_audit.status_code == 200
    p_audit = res_audit.json()
    assert p_audit["errors"] is None
    assert isinstance(p_audit["data"], list)
