"""
Comprehensive Test Suite for Person A / Track A Reasoning Engine:
- Semantic Dependency Graph & Bounded Traversal (Depth 1..5)
- Cycle Safety & Termination Guarantees
- Multi-Hop Operational Impact Propagation
- Deterministic Constraint Evaluation & Tri-State Outcomes (SATISFIED, VIOLATED, NOT_EVALUABLE)
- Evidence-Aware Mission Readiness (READY, AT_RISK, BLOCKED, zero fake percentages)
- Campaign-Wide Expedition Readiness Roll-Up
- Operational Event Integration via OperationalImpactProcessor
- Hero Scenario: Transport Delay Impact Chain (T-08 -> C-117 -> I-42 -> M-08)
- API Contract Verification for all Reasoning Endpoints
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Ensure all models are loaded
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.people.models
import backend.app.domains.teams.models
import backend.app.domains.time_windows.models
import backend.app.platform.events.models
import backend.app.platform.audit.models
import backend.app.services.dependencies.models
import backend.app.services.constraints.models

from backend.app.services.dependencies.models import DependencyModel
from backend.app.services.dependencies.service import DependencyService
from backend.app.services.constraints.models import ConstraintModel
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.impact.service import ImpactService
from backend.app.services.impact.processor import OperationalImpactProcessor
from backend.app.services.readiness.mission import MissionReadinessService
from backend.app.services.readiness.expedition import ExpeditionReadinessService
from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.people.models import PersonModel
from backend.app.domains.time_windows.models import TimeWindowModel
from backend.app.platform.events.models import OperationalEventModel
from backend.app.shared.types.reasoning import (
    DependencyRelationship,
    ConstraintSeverity,
    ConstraintState,
    ReadinessState,
    TraversalDirection,
)
from backend.app.shared.types.states import (
    ExpeditionStatus,
    MissionStatus,
    PersonReadiness,
    PersonMovement,
    TeamStatus,
    HardSoftConstraint,
)


@pytest.fixture(scope="module")
def shared_engine():
    """Module-level in-memory SQLite engine with core and mock tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    # Add mock schema tables for Person B domains to enable multi-domain reasoning tests
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                asset_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                model TEXT,
                condition TEXT DEFAULT 'OPERATIONAL',
                location_id TEXT,
                custodian_person_id TEXT,
                assigned_mission_id TEXT,
                maintenance_state TEXT DEFAULT 'SERVICEABLE',
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                required_spare_item_id TEXT,
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cargo_consignments (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                expedition_id TEXT NOT NULL,
                origin_location_id TEXT,
                destination_location_id TEXT,
                priority INTEGER DEFAULT 3,
                required_by_at TIMESTAMP NOT NULL,
                estimated_arrival_at TIMESTAMP,
                status TEXT DEFAULT 'REQUESTED',
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                id TEXT PRIMARY KEY,
                item_code TEXT UNIQUE NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                criticality TEXT DEFAULT 'CRITICAL',
                description TEXT,
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO'
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory_stock_lots (
                id TEXT PRIMARY KEY,
                inventory_item_id TEXT NOT NULL,
                lot_code TEXT,
                location_id TEXT,
                on_hand_quantity NUMERIC(12,2) DEFAULT 0,
                reserved_quantity NUMERIC(12,2) DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO'
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                document_code TEXT UNIQUE NOT NULL,
                document_type TEXT NOT NULL,
                subject_type TEXT,
                subject_id TEXT,
                status TEXT NOT NULL DEFAULT 'APPROVED',
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO'
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS transport_legs (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                expedition_id TEXT,
                mode TEXT NOT NULL,
                capacity NUMERIC(12,2) DEFAULT 1000,
                capacity_unit TEXT DEFAULT 'KG',
                status TEXT DEFAULT 'PLANNED',
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO'
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cargo_packages (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                consignment_id TEXT,
                description TEXT,
                status TEXT DEFAULT 'PACKED',
                data_provenance TEXT DEFAULT 'SYNTHETIC_DEMO'
            );
        """))
    return engine


@pytest.fixture
def db_session(shared_engine):
    """Function-level test database session with automatic cleanup."""
    TestingSessionLocal = sessionmaker(bind=shared_engine, class_=Session, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="module")
def client(shared_engine):
    """FastAPI TestClient wired to the shared test database."""
    TestingSessionLocal = sessionmaker(bind=shared_engine, class_=Session, autocommit=False, autoflush=False)

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
# 1. DEPENDENCY GRAPH TESTS
# ============================================================

def test_direct_dependencies_query(db_session):
    """Tests outgoing and incoming dependency queries using canonical relationships."""
    dep_service = DependencyService(db_session)

    m_id = uuid.uuid4()
    a_id = uuid.uuid4()

    # Create M-08 REQUIRES I-42
    dep = DependencyModel(
        id=uuid.uuid4(),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m_id,
        target_entity_type="ASSET",
        target_entity_id=a_id,
        criticality="CRITICAL"
    )
    db_session.add(dep)
    db_session.commit()

    # Outgoing from mission
    outgoing = dep_service.get_outgoing_dependencies("MISSION", m_id)
    assert len(outgoing) == 1
    assert outgoing[0].relationship == DependencyRelationship.REQUIRES
    assert outgoing[0].target_entity_id == a_id
    assert outgoing[0].direction == "OUTGOING"

    # Incoming to asset
    incoming = dep_service.get_incoming_dependencies("ASSET", a_id)
    assert len(incoming) == 1
    assert incoming[0].relationship == DependencyRelationship.REQUIRES
    assert incoming[0].source_entity_id == m_id
    assert incoming[0].direction == "INCOMING"


def test_semantic_relationship_filtering(db_session):
    """Tests that dependencies can be filtered strictly by canonical relationship type."""
    dep_service = DependencyService(db_session)

    m_id = uuid.uuid4()
    t_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    db_session.add(DependencyModel(
        id=uuid.uuid4(),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m_id,
        target_entity_type="TEAM",
        target_entity_id=t_id
    ))
    db_session.add(DependencyModel(
        id=uuid.uuid4(),
        relationship_type="LOCATED_AT",
        source_entity_type="MISSION",
        source_entity_id=m_id,
        target_entity_type="LOCATION",
        target_entity_id=loc_id
    ))
    db_session.commit()

    requires_only = dep_service.get_outgoing_dependencies("MISSION", m_id, relationship_type="REQUIRES")
    assert len(requires_only) == 1
    assert requires_only[0].relationship == DependencyRelationship.REQUIRES

    located_only = dep_service.get_outgoing_dependencies("MISSION", m_id, relationship_type="LOCATED_AT")
    assert len(located_only) == 1
    assert located_only[0].relationship == DependencyRelationship.LOCATED_AT


def test_bounded_traversal_depth(db_session):
    """Tests that graph traversal depth is bounded and respects max clamp (5)."""
    dep_service = DependencyService(db_session)

    # Construct linear 6-hop chain: N0 -> N1 -> N2 -> N3 -> N4 -> N5 -> N6
    nodes = [uuid.uuid4() for _ in range(7)]
    for i in range(6):
        db_session.add(DependencyModel(
            id=uuid.uuid4(),
            relationship_type="DEPENDS_ON",
            source_entity_type="ASSET",
            source_entity_id=nodes[i],
            target_entity_type="ASSET",
            target_entity_id=nodes[i+1]
        ))
    db_session.commit()

    # Verify class constants conform strictly to contract
    assert DependencyService.DEFAULT_TRAVERSAL_DEPTH == 3
    assert DependencyService.MAX_TRAVERSAL_DEPTH == 5

    # Traversal without max_depth argument must use DEFAULT_TRAVERSAL_DEPTH = 3
    res_default = dep_service.traverse_graph("ASSET", nodes[0])
    assert res_default.depth_limit == 3
    default_terminals = [p.terminal_entity_id for p in res_default.paths]
    assert nodes[1] in default_terminals
    assert nodes[2] in default_terminals
    assert nodes[3] in default_terminals
    assert nodes[4] not in default_terminals  # Depth 4 excluded under default=3

    # Traversal requesting explicit depth=2
    res2 = dep_service.traverse_graph("ASSET", nodes[0], max_depth=2)
    assert res2.depth_limit == 2
    terminal_ids = [p.terminal_entity_id for p in res2.paths]
    assert nodes[1] in terminal_ids
    assert nodes[2] in terminal_ids
    assert nodes[3] not in terminal_ids

    # Traversal requesting depth=10 should be clamped to MAX_TRAVERSAL_DEPTH (5)
    res_clamped = dep_service.traverse_graph("ASSET", nodes[0], max_depth=10)
    assert res_clamped.depth_limit == 5
    clamped_terminals = [p.terminal_entity_id for p in res_clamped.paths]
    assert nodes[5] in clamped_terminals
    assert nodes[6] not in clamped_terminals  # Depth 6 must be excluded under max=5


def test_cycle_safety_termination(db_session):
    """Tests that circular dependency graphs terminate cleanly without infinite loops."""
    dep_service = DependencyService(db_session)

    # Create cycle: NodeA -> NodeB -> NodeC -> NodeA
    nA, nB, nC = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="SUPPORTS", source_entity_type="ASSET", source_entity_id=nA, target_entity_type="ASSET", target_entity_id=nB))
    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="SUPPORTS", source_entity_type="ASSET", source_entity_id=nB, target_entity_type="ASSET", target_entity_id=nC))
    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="SUPPORTS", source_entity_type="ASSET", source_entity_id=nC, target_entity_type="ASSET", target_entity_id=nA))
    db_session.commit()

    # Traversal starting at nA must terminate and visit each node once
    result = dep_service.traverse_graph("ASSET", nA, max_depth=5)
    visited_terminals = {p.terminal_entity_id for p in result.paths}
    assert nB in visited_terminals
    assert nC in visited_terminals
    assert result.total_nodes_visited == 3


# ============================================================
# 2. IMPACT PROPAGATION TESTS
# ============================================================

def test_impact_service_multi_hop(db_session):
    """Tests impact propagation and deterministic structured reason formulation."""
    impact_service = ImpactService(db_session)

    # Setup chain: Transport T1 -> Cargo C1 -> Instrument I1
    t1_id, c1_id, i1_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="MOVES_VIA", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c1_id, target_entity_type="TRANSPORT_LEG", target_entity_id=t1_id))
    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c1_id, target_entity_type="ASSET", target_entity_id=i1_id))
    db_session.commit()

    impact = impact_service.calculate_impact(
        entity_type="TRANSPORT_LEG",
        entity_id=t1_id,
        change_summary="Transport leg delayed 48 hours",
        depth=3
    )

    assert impact.source_entity_type == "TRANSPORT_LEG"
    assert impact.total_affected_entities >= 2
    affected_types = [ae.entity_type for ae in impact.affected_entities]
    assert "CARGO_CONSIGNMENT" in affected_types
    assert "ASSET" in affected_types

    assert len(impact.reasons) > 0
    assert any("CARGO_CONSIGNMENT" in r for r in impact.reasons)


def test_operational_impact_processor(db_session):
    """Tests processing an operational event through the OperationalImpactProcessor."""
    processor = OperationalImpactProcessor(db_session)

    target_asset = uuid.uuid4()
    correlation_id = uuid.uuid4()
    event_model = OperationalEventModel(
        event_id=uuid.uuid4(),
        event_type="AssetStatusChanged",
        entity_type="ASSET",
        entity_id=target_asset,
        previous_state="OPERATIONAL",
        new_state="DAMAGED",
        occurred_at=datetime.now(timezone.utc),
        source="SYSTEM",
        correlation_id=correlation_id
    )
    db_session.add(event_model)
    db_session.commit()

    impact_res = processor.process_operational_event(event_model.event_id)
    assert impact_res.source_entity_type == "ASSET"
    assert impact_res.source_entity_id == target_asset
    assert "status changed from 'OPERATIONAL' to 'DAMAGED'" in impact_res.change_summary
    assert impact_res.correlation_id == correlation_id


# ============================================================
# 3. CONSTRAINT EVALUATION TESTS
# ============================================================

def test_constraint_mission_required_by_satisfied_and_violated(db_session):
    """Tests MISSION_REQUIRED_BY rule under satisfied and violated deadlines."""
    constraint_service = ConstraintService(db_session)

    exp_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-REQ-{uuid.uuid4().hex[:6]}", name="Test Expedition", season="2026-2027"))

    # Mission with deadline Dec 24
    deadline = datetime(2026, 12, 24, 0, 0, tzinfo=timezone.utc)
    m_id = uuid.uuid4()
    db_session.add(MissionModel(
        id=m_id,
        expedition_id=exp_id,
        code=f"M-REQ-{uuid.uuid4().hex[:6]}",
        title="Survey Mission",
        type="SURVEY",
        required_by_at=deadline
    ))

    # Time window closing on Dec 20 (before deadline -> SATISFIED)
    tw_good = TimeWindowModel(
        id=uuid.uuid4(),
        type="FIELD_DEPLOYMENT",
        open_at=datetime(2026, 12, 10, 0, 0, tzinfo=timezone.utc),
        close_at=datetime(2026, 12, 20, 0, 0, tzinfo=timezone.utc),
        subject_type="MISSION",
        subject_id=m_id,
        status="OPEN"
    )
    db_session.add(tw_good)

    c_model = ConstraintModel(
        id=uuid.uuid4(),
        code=f"CONST-REQ-{uuid.uuid4().hex[:6]}",
        name="Mission Schedule Check",
        type="SCHEDULE",
        rule_code="MISSION_REQUIRED_BY",
        subject_type="MISSION",
        subject_id=m_id,
        hard_or_soft="HARD"
    )
    db_session.add(c_model)
    db_session.commit()

    # Evaluate: Satisfied
    res_sat = constraint_service.evaluate_constraint(c_model)
    assert res_sat.state == ConstraintState.SATISFIED

    # Add a time window closing after deadline Dec 28 -> VIOLATED
    tw_bad = TimeWindowModel(
        id=uuid.uuid4(),
        type="DEMOBILIZATION",
        open_at=datetime(2026, 12, 20, 0, 0, tzinfo=timezone.utc),
        close_at=datetime(2026, 12, 28, 0, 0, tzinfo=timezone.utc),
        subject_type="MISSION",
        subject_id=m_id,
        status="OPEN"
    )
    db_session.add(tw_bad)
    db_session.commit()

    res_viol = constraint_service.evaluate_constraint(c_model)
    assert res_viol.state == ConstraintState.VIOLATED
    assert "closes after required_by_at deadline" in res_viol.reason


def test_constraint_personnel_staffing(db_session):
    """Tests PERSONNEL_STAFFING evaluation for minimum headcounts and readiness."""
    constraint_service = ConstraintService(db_session)

    exp_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-STAFF-{uuid.uuid4().hex[:6]}", name="Staff Exp", season="2026-2027"))

    t_id = uuid.uuid4()
    db_session.add(TeamModel(id=t_id, code=f"TEAM-{uuid.uuid4().hex[:6]}", name="Alpha Field Team", expedition_id=exp_id))

    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    db_session.add(PersonModel(id=p1, person_code=f"P1-{uuid.uuid4().hex[:4]}", full_name="Alice", role="SCIENTIST", expedition_id=exp_id, team_id=t_id, readiness_state="READY"))
    db_session.add(PersonModel(id=p2, person_code=f"P2-{uuid.uuid4().hex[:4]}", full_name="Bob", role="SAFETY_OFFICER", expedition_id=exp_id, team_id=t_id, readiness_state="READY"))

    c_staffing = ConstraintModel(
        id=uuid.uuid4(),
        code=f"CONST-STAFF-{uuid.uuid4().hex[:6]}",
        name="Minimum Crew of 2",
        type="COMPLIANCE",
        rule_code="PERSONNEL_STAFFING",
        subject_type="TEAM",
        subject_id=t_id,
        parameters={"min_personnel": 2}
    )
    db_session.add(c_staffing)
    db_session.commit()

    # 1. Satisfied with 2 ready members
    res = constraint_service.evaluate_constraint(c_staffing)
    assert res.state == ConstraintState.SATISFIED

    # 2. Member becomes UNAVAILABLE -> VIOLATED
    person2 = db_session.query(PersonModel).filter_by(id=p2).first()
    person2.readiness_state = "UNAVAILABLE"
    db_session.commit()

    res_unavail = constraint_service.evaluate_constraint(c_staffing)
    assert res_unavail.state == ConstraintState.VIOLATED
    assert "unavailable readiness" in res_unavail.reason


def test_constraint_not_evaluable_rule(db_session):
    """Tests that unknown rule code returns NOT_EVALUABLE rather than throwing or claiming satisfied."""
    constraint_service = ConstraintService(db_session)

    c_unknown = ConstraintModel(
        id=uuid.uuid4(),
        code=f"CONST-FUT-{uuid.uuid4().hex[:6]}",
        name="Hypothetical Future Rule",
        type="EXPERIMENTAL",
        rule_code="FUTURE_UNSUPPORTED_RULE",
        subject_type="MISSION",
        subject_id=uuid.uuid4()
    )
    res = constraint_service.evaluate_constraint(c_unknown)
    assert res.state == ConstraintState.NOT_EVALUABLE
    assert "No verified rule evaluator registered" in res.reason


# ============================================================
# 4. MISSION & EXPEDITION READINESS TESTS
# ============================================================

def test_mission_readiness_baseline_ready(db_session):
    """Verifies that a fully satisfied mission evaluates deterministically to READY."""
    readiness_service = MissionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    t_id = uuid.uuid4()
    a_id = uuid.uuid4()

    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-B-{uuid.uuid4().hex[:6]}", name="Base Exp", season="2026-2027"))
    db_session.add(MissionModel(id=m_id, expedition_id=exp_id, code=f"M-B-{uuid.uuid4().hex[:6]}", title="Base Mission", type="SCIENCE", status="APPROVED"))
    db_session.add(TeamModel(id=t_id, code=f"T-B-{uuid.uuid4().hex[:6]}", name="Base Team", expedition_id=exp_id))
    db_session.add(PersonModel(id=uuid.uuid4(), person_code=f"P-B-{uuid.uuid4().hex[:4]}", full_name="Explorer 1", role="LEAD", expedition_id=exp_id, team_id=t_id, readiness_state="READY"))

    # Asset in mock table
    with db_session.bind.begin() as conn:
        conn.execute(text("INSERT INTO assets (id, asset_code, name, type, status) VALUES (:id, :code, :name, 'ROVER', 'AVAILABLE')"),
                     {"id": str(a_id), "code": f"ROV-{uuid.uuid4().hex[:6]}", "name": "Polar Rover"})

    # Dependencies: M-BASE REQUIRES T-BASE, M-BASE REQUIRES ROVER
    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m_id, target_entity_type="TEAM", target_entity_id=t_id))
    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m_id, target_entity_type="ASSET", target_entity_id=a_id))

    # Time Window: OPEN
    db_session.add(TimeWindowModel(
        id=uuid.uuid4(),
        type="SURVEY_WINDOW",
        open_at=datetime.now(timezone.utc) - timedelta(days=1),
        close_at=datetime.now(timezone.utc) + timedelta(days=10),
        subject_type="MISSION",
        subject_id=m_id,
        status="OPEN"
    ))
    db_session.commit()

    result = readiness_service.evaluate(m_id)
    assert result.state == ReadinessState.READY
    assert len(result.blockers) == 0
    assert len(result.satisfied_requirements) >= 2


def test_mission_readiness_blocked_by_unavailable_asset(db_session):
    """Verifies that an unavailable required asset triggers BLOCKED readiness."""
    readiness_service = MissionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    a_id = uuid.uuid4()

    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-FAIL-{uuid.uuid4().hex[:6]}", name="Fail Exp", season="2026-2027"))
    db_session.add(MissionModel(id=m_id, expedition_id=exp_id, code=f"M-AFAIL-{uuid.uuid4().hex[:6]}", title="Failed Asset Mission", type="SURVEY", status="APPROVED"))

    with db_session.bind.begin() as conn:
        conn.execute(text("INSERT INTO assets (id, asset_code, name, type, status) VALUES (:id, :code, :name, 'RADAR', 'DAMAGED')"),
                     {"id": str(a_id), "code": f"RADAR-{uuid.uuid4().hex[:6]}", "name": "Broken Radar"})

    db_session.add(DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m_id, target_entity_type="ASSET", target_entity_id=a_id))
    db_session.commit()

    result = readiness_service.evaluate(m_id)
    assert result.state == ReadinessState.BLOCKED
    assert len(result.blockers) > 0
    assert any(b.type == "ASSET" for b in result.blockers)


def test_mission_readiness_blocked_by_hard_constraint(db_session):
    """Verifies that a hard constraint violation deterministically blocks mission readiness."""
    readiness_service = MissionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-HC-{uuid.uuid4().hex[:6]}", name="HC Exp", season="2026-2027"))
    db_session.add(MissionModel(
        id=m_id,
        expedition_id=exp_id,
        code=f"M-HC-{uuid.uuid4().hex[:6]}",
        title="Hard Constraint Mission",
        type="SCIENCE",
        required_by_at=datetime(2026, 12, 1, tzinfo=timezone.utc),
        status="APPROVED"
    ))
    # Time window closing past deadline -> VIOLATES MISSION_REQUIRED_BY
    db_session.add(TimeWindowModel(
        id=uuid.uuid4(),
        type="FIELD_DEPLOYMENT",
        open_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
        close_at=datetime(2026, 12, 10, tzinfo=timezone.utc),
        subject_type="MISSION",
        subject_id=m_id,
        status="OPEN"
    ))
    # Hard constraint
    db_session.add(ConstraintModel(
        id=uuid.uuid4(),
        code=f"CONST-HARD-{uuid.uuid4().hex[:6]}",
        name="Hard Deadline Rule",
        type="SCHEDULE",
        rule_code="MISSION_REQUIRED_BY",
        subject_type="MISSION",
        subject_id=m_id,
        hard_or_soft="HARD"
    ))
    db_session.commit()

    result = readiness_service.evaluate(m_id)
    assert result.state == ReadinessState.BLOCKED
    assert len(result.blockers) > 0
    assert any("Hard constraint" in b.reason for b in result.blockers)


def test_mission_readiness_at_risk_by_soft_constraint(db_session):
    """Verifies that a soft constraint violation sets mission readiness to AT_RISK, not BLOCKED."""
    readiness_service = MissionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-SC-{uuid.uuid4().hex[:6]}", name="SC Exp", season="2026-2027"))
    db_session.add(MissionModel(
        id=m_id,
        expedition_id=exp_id,
        code=f"M-SC-{uuid.uuid4().hex[:6]}",
        title="Soft Constraint Mission",
        type="SCIENCE",
        required_by_at=datetime(2026, 12, 1, tzinfo=timezone.utc),
        status="APPROVED"
    ))
    # Time window closing past deadline
    db_session.add(TimeWindowModel(
        id=uuid.uuid4(),
        type="FIELD_DEPLOYMENT",
        open_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
        close_at=datetime(2026, 12, 10, tzinfo=timezone.utc),
        subject_type="MISSION",
        subject_id=m_id,
        status="OPEN"
    ))
    # Soft constraint
    db_session.add(ConstraintModel(
        id=uuid.uuid4(),
        code=f"CONST-SOFT-{uuid.uuid4().hex[:6]}",
        name="Soft Target Date Advisory",
        type="SCHEDULE",
        rule_code="MISSION_REQUIRED_BY",
        subject_type="MISSION",
        subject_id=m_id,
        hard_or_soft="SOFT"
    ))
    db_session.commit()

    result = readiness_service.evaluate(m_id)
    assert result.state == ReadinessState.AT_RISK
    assert len(result.blockers) == 0
    assert len(result.warnings) > 0
    assert any("Soft constraint" in w.reason for w in result.warnings)


def test_mission_readiness_unknown_dependency_prevents_ready(db_session):
    """
    CRITICAL INVARIANT: A mission requiring an asset or dependency that is NOT_EVALUABLE / UNKNOWN
    (e.g., Track B asset record not yet present or constraint unevaluable)
    must NEVER be reported as READY. It must evaluate to AT_RISK with unknown_requirements populated.
    """
    readiness_service = MissionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    missing_asset_id = uuid.uuid4()

    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-UNK-{uuid.uuid4().hex[:6]}", name="Unknown Exp", season="2026-2027"))
    db_session.add(MissionModel(
        id=m_id,
        expedition_id=exp_id,
        code=f"M-UNK-{uuid.uuid4().hex[:6]}",
        title="Unknown Dependency Mission",
        type="SCIENCE",
        status="APPROVED"
    ))

    # Mission REQUIRES an asset that does NOT exist in the assets table (Track B pending)
    db_session.add(DependencyModel(
        id=uuid.uuid4(),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m_id,
        target_entity_type="ASSET",
        target_entity_id=missing_asset_id
    ))
    db_session.commit()

    result = readiness_service.evaluate(m_id)

    # Must NOT be READY!
    assert result.state != ReadinessState.READY
    assert result.state == ReadinessState.AT_RISK
    assert len(result.unknown_requirements) > 0
    assert any(u.category == "ASSET" for u in result.unknown_requirements)


def test_mission_readiness_m08_seeded_baseline(db_session):
    """
    Verifies that the canonical hero mission M-08 seeded baseline
    evaluates deterministically to READY using actual domain relationships.
    """
    readiness_service = MissionReadinessService(db_session)

    m08_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    exp_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    r04_team_id = uuid.UUID("30000000-0000-0000-0000-000000000001")
    i42_asset_id = uuid.UUID("90000000-0000-0000-0000-000000000001")
    tw_id = uuid.UUID("d0000000-0000-0000-0000-000000000001")

    # Seed M-08 and its related hero entities (idempotent get-or-create)
    exp = db_session.get(ExpeditionModel, exp_id)
    if not exp:
        db_session.add(ExpeditionModel(id=exp_id, code="EXP-26-A", name="45th Indian Antarctic Expedition", season="2026-2027"))
    mission = db_session.get(MissionModel, m08_id)
    if not mission:
        db_session.add(MissionModel(id=m08_id, expedition_id=exp_id, code="M-08", title="Coastal Geophysics Survey", type="SCIENTIFIC", status="READY"))
    team = db_session.get(TeamModel, r04_team_id)
    if not team:
        db_session.add(TeamModel(id=r04_team_id, code="R-04", name="Field Survey Team", expedition_id=exp_id))

    person = db_session.execute(select(PersonModel).where(PersonModel.team_id == r04_team_id)).scalars().first()
    if not person:
        db_session.add(PersonModel(id=uuid.uuid4(), person_code="P-101", full_name="Survey Lead", role="LEAD", expedition_id=exp_id, team_id=r04_team_id, readiness_state="READY"))

    db_session.execute(text("DELETE FROM assets WHERE id = :id OR asset_code = 'I-42'"), {"id": str(i42_asset_id)})
    db_session.execute(text("INSERT INTO assets (id, asset_code, name, type, status) VALUES (:id, 'I-42', 'Cryo-Seismic Profiler', 'INSTRUMENT', 'AVAILABLE')"),
                 {"id": str(i42_asset_id)})

    tw = db_session.get(TimeWindowModel, tw_id)
    if not tw:
        db_session.add(TimeWindowModel(
            id=tw_id,
            type="MISSION_WINDOW",
            open_at=datetime(2026, 12, 20, 0, 0, tzinfo=timezone.utc),
            close_at=datetime(2027, 1, 10, 0, 0, tzinfo=timezone.utc),
            subject_type="MISSION",
            subject_id=m08_id,
            status="OPEN"
        ))

    # Dependencies: M-08 REQUIRES I-42, M-08 REQUIRES R-04
    for did in ("d1000000-0000-0000-0000-000000000001", "d1000000-0000-0000-0000-000000000002"):
        existing_dep = db_session.get(DependencyModel, uuid.UUID(did))
        if existing_dep:
            db_session.delete(existing_dep)
    db_session.flush()

    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000001"),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m08_id,
        target_entity_type="ASSET",
        target_entity_id=i42_asset_id
    ))
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000002"),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m08_id,
        target_entity_type="TEAM",
        target_entity_id=r04_team_id
    ))
    db_session.commit()

    result = readiness_service.evaluate(m08_id)
    assert result.state == ReadinessState.READY
    assert len(result.blockers) == 0
    assert len(result.warnings) == 0
    assert len(result.unknown_requirements) == 0


def test_expedition_readiness_aggregation(db_session):
    """Verifies campaign-wide expedition readiness rollup from individual missions."""
    exp_service = ExpeditionReadinessService(db_session)

    exp_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-ROLL-{uuid.uuid4().hex[:6]}", name="Rollup Expedition", season="2026-2027"))

    # Mission 1: READY
    m1_id = uuid.uuid4()
    db_session.add(MissionModel(id=m1_id, expedition_id=exp_id, code=f"M-OK-{uuid.uuid4().hex[:6]}", title="OK Mission", type="SCIENCE", status="APPROVED"))

    # Mission 2: BLOCKED (due to closed time window)
    m2_id = uuid.uuid4()
    m2_code = f"M-BLK-{uuid.uuid4().hex[:6]}"
    db_session.add(MissionModel(id=m2_id, expedition_id=exp_id, code=m2_code, title="Blocked Mission", type="LOGISTICS", status="APPROVED"))
    db_session.add(TimeWindowModel(
        id=uuid.uuid4(),
        type="DEPLOYMENT",
        open_at=datetime.now(timezone.utc) - timedelta(days=10),
        close_at=datetime.now(timezone.utc) - timedelta(days=1),
        subject_type="MISSION",
        subject_id=m2_id,
        status="CLOSED"
    ))
    db_session.commit()

    exp_res = exp_service.evaluate(exp_id)
    assert exp_res.state == ReadinessState.BLOCKED
    assert exp_res.blocked_missions >= 1
    assert m2_code in exp_res.explanation


# ============================================================
# 5. HERO SCENARIO: TRANSPORT DELAY IMPACT CHAIN
# ============================================================

def test_hero_transport_delay_impact_propagation(db_session):
    """
    Hero Test: Proves reasoning engine can consume a transport delay event on T-08
    and trace downstream impact through Cargo C-117, Package PKG-117-01, Instrument I-42, to Mission M-08.
    Uses the exact canonical seeded UUIDs and relationships declared in seed.sql:
    T-08 <-[MOVES_VIA]- C-117 -[CONTAINS]-> PKG-117-01 -[CONTAINS]-> I-42 <-[REQUIRES]- M-08
    Also C-117 -[SUPPORTS]-> M-08.
    Does not require Person B domain code; uses the semantic dependency graph!
    """
    impact_service = ImpactService(db_session)

    # Canonical seeded UUIDs from supabase/seed.sql
    exp_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    m08_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    c117_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    t08_id = uuid.UUID("60000000-0000-0000-0000-000000000001")
    pkg_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
    i42_id = uuid.UUID("90000000-0000-0000-0000-000000000001")

    exp = db_session.get(ExpeditionModel, exp_id)
    if not exp:
        db_session.add(ExpeditionModel(id=exp_id, code="EXP-26-A", name="45th Indian Antarctic Expedition", season="2026-2027"))
    mission = db_session.get(MissionModel, m08_id)
    if not mission:
        db_session.add(MissionModel(id=m08_id, expedition_id=exp_id, code="M-08", title="Coastal Geophysics Survey", type="SCIENTIFIC", status="APPROVED"))

    # Register in mock tables for code lookups matching canonical seed records
    db_session.execute(text("DELETE FROM transport_legs WHERE id = :id OR code = 'T-08'"), {"id": str(t08_id)})
    db_session.execute(text("DELETE FROM cargo_consignments WHERE id = :id OR code = 'C-117'"), {"id": str(c117_id)})
    db_session.execute(text("DELETE FROM cargo_packages WHERE id = :id OR code = 'PKG-117-01'"), {"id": str(pkg_id)})
    db_session.execute(text("DELETE FROM assets WHERE id = :id OR asset_code = 'I-42'"), {"id": str(i42_id)})

    db_session.execute(text("INSERT INTO transport_legs (id, code, mode, status) VALUES (:id, 'T-08', 'VESSEL', 'DELAYED')"),
                 {"id": str(t08_id)})
    db_session.execute(text("INSERT INTO cargo_consignments (id, code, expedition_id, required_by_at, status) VALUES (:id, 'C-117', :eid, CURRENT_TIMESTAMP, 'DELAYED')"),
                 {"id": str(c117_id), "eid": str(exp_id)})
    db_session.execute(text("INSERT INTO cargo_packages (id, code, consignment_id, description, status) VALUES (:id, 'PKG-117-01', :cid, 'Seismic sensor kit', 'PACKED')"),
                 {"id": str(pkg_id), "cid": str(c117_id)})
    db_session.execute(text("INSERT INTO assets (id, asset_code, name, type, status) VALUES (:id, 'I-42', 'Cryo-Seismic Profiler', 'INSTRUMENT', 'AVAILABLE')"),
                 {"id": str(i42_id)})

    # Delete existing hero dependency IDs if present from previous test
    hero_dep_ids = [
        "d1000000-0000-0000-0000-000000000001",
        "d1000000-0000-0000-0000-000000000002",
        "d1000000-0000-0000-0000-000000000003",
        "d1000000-0000-0000-0000-000000000004",
        "d1000000-0000-0000-0000-000000000014",
        "d1000000-0000-0000-0000-000000000015",
    ]
    for did in hero_dep_ids:
        existing_dep = db_session.get(DependencyModel, uuid.UUID(did))
        if existing_dep:
            db_session.delete(existing_dep)
    db_session.flush()

    # Connect canonical chain from seed.sql:
    # 1. C-117 MOVES_VIA T-08 (seed d1000000-0000-0000-0000-000000000004)
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000004"),
        relationship_type="MOVES_VIA",
        source_entity_type="CARGO_CONSIGNMENT",
        source_entity_id=c117_id,
        target_entity_type="TRANSPORT_LEG",
        target_entity_id=t08_id,
        criticality="CRITICAL"
    ))
    # 2. C-117 CONTAINS PKG-117-01 (seed d1000000-0000-0000-0000-000000000015)
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000015"),
        relationship_type="CONTAINS",
        source_entity_type="CARGO_CONSIGNMENT",
        source_entity_id=c117_id,
        target_entity_type="CARGO_PACKAGE",
        target_entity_id=pkg_id,
        criticality="CRITICAL"
    ))
    # 3. PKG-117-01 CONTAINS I-42 (seed d1000000-0000-0000-0000-000000000014)
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000014"),
        relationship_type="CONTAINS",
        source_entity_type="CARGO_PACKAGE",
        source_entity_id=pkg_id,
        target_entity_type="ASSET",
        target_entity_id=i42_id,
        criticality="CRITICAL"
    ))
    # 4. M-08 REQUIRES I-42 (seed d1000000-0000-0000-0000-000000000001)
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000001"),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=m08_id,
        target_entity_type="ASSET",
        target_entity_id=i42_id,
        criticality="CRITICAL"
    ))
    # 5. C-117 SUPPORTS M-08 (seed d1000000-0000-0000-0000-000000000003)
    db_session.add(DependencyModel(
        id=uuid.UUID("d1000000-0000-0000-0000-000000000003"),
        relationship_type="SUPPORTS",
        source_entity_type="CARGO_CONSIGNMENT",
        source_entity_id=c117_id,
        target_entity_type="MISSION",
        target_entity_id=m08_id,
        criticality="CRITICAL"
    ))
    db_session.commit()

    # Calculate impact starting from delayed transport T-08 with depth 5
    impact = impact_service.calculate_impact(
        entity_type="TRANSPORT_LEG",
        entity_id=t08_id,
        change_summary="Vessel T-08 delayed due to pack ice encroachment",
        depth=5
    )

    affected_codes = [ae.entity_code for ae in impact.affected_entities if ae.entity_code]
    assert "C-117" in affected_codes
    assert "PKG-117-01" in affected_codes
    assert "I-42" in affected_codes
    assert "M-08" in affected_codes

    # Verify hop 1: C-117 reached via incoming MOVES_VIA at depth 1
    c117_entry = next(ae for ae in impact.affected_entities if ae.entity_code == "C-117")
    assert c117_entry.depth == 1
    assert c117_entry.relationship == "MOVES_VIA"
    assert c117_entry.direction == "INCOMING"

    # Verify hop 2: PKG-117-01 reached via outgoing CONTAINS from C-117 at depth 2
    pkg_entry = next(ae for ae in impact.affected_entities if ae.entity_code == "PKG-117-01")
    assert pkg_entry.depth == 2
    assert pkg_entry.relationship == "CONTAINS"

    # Verify hop 3: I-42 reached via outgoing CONTAINS from PKG-117-01 at depth 3
    i42_entry = next(ae for ae in impact.affected_entities if ae.entity_code == "I-42")
    assert i42_entry.depth == 3
    assert i42_entry.relationship == "CONTAINS"

    # Verify downstream impact reaches Mission M-08
    m08_entry = next(ae for ae in impact.affected_entities if ae.entity_code == "M-08")
    assert "M-08" in m08_entry.reason


def test_side_effect_safety_read_only(db_session):
    """
    Verifies that reasoning engine reads (dependencies, impact, readiness, constraints)
    are strictly side-effect free and never mutate authoritative primary domain state
    or emit spurious operational events.
    """
    dep_service = DependencyService(db_session)
    impact_service = ImpactService(db_session)
    constraint_service = ConstraintService(db_session)
    mission_service = MissionReadinessService(db_session)
    exp_service = ExpeditionReadinessService(db_session)

    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    exp = ExpeditionModel(id=exp_id, code=f"EXP-SAFE-{uuid.uuid4().hex[:6]}", name="Safe Exp", season="2026-2027", status="PLANNED")
    mission = MissionModel(id=m_id, expedition_id=exp_id, code=f"M-SAFE-{uuid.uuid4().hex[:6]}", title="Safe Mission", type="SCIENCE", status="SCHEDULED")
    db_session.add(exp)
    db_session.add(mission)
    db_session.commit()

    # Record baseline state
    initial_exp_status = exp.status
    initial_mission_status = mission.status
    initial_events_count = db_session.execute(text("SELECT COUNT(*) FROM operational_events")).scalar()

    # Perform all reasoning operations
    _ = dep_service.get_dependencies("MISSION", m_id)
    _ = dep_service.traverse_graph("MISSION", m_id, direction=TraversalDirection.BOTH, max_depth=3)
    _ = impact_service.calculate_impact("MISSION", m_id, "Hypothetical schedule risk", depth=3)
    _ = constraint_service.evaluate_for_entity("MISSION", m_id)
    _ = constraint_service.evaluate_all()
    _ = mission_service.evaluate(m_id)
    _ = exp_service.evaluate(exp_id)

    # Invalidate session cache to force fresh DB fetch
    db_session.expire_all()

    fresh_exp = db_session.get(ExpeditionModel, exp_id)
    fresh_mission = db_session.get(MissionModel, m_id)
    fresh_events_count = db_session.execute(text("SELECT COUNT(*) FROM operational_events")).scalar()

    # Assert zero side-effects
    assert fresh_exp.status == initial_exp_status
    assert fresh_mission.status == initial_mission_status
    assert fresh_events_count == initial_events_count


# ============================================================
# 6. API ENDPOINTS INTEGRATION TESTS
# ============================================================

def test_api_entity_dependencies(client, db_session):
    """Tests GET /api/v1/entities/{type}/{id}/dependencies endpoint."""
    e1, e2 = uuid.uuid4(), uuid.uuid4()
    db_session.add(DependencyModel(
        id=uuid.uuid4(),
        relationship_type="REQUIRES",
        source_entity_type="MISSION",
        source_entity_id=e1,
        target_entity_type="TEAM",
        target_entity_id=e2
    ))
    db_session.commit()

    resp = client.get(f"/api/v1/entities/MISSION/{e1}/dependencies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    data = body["data"]
    assert len(data) == 1
    assert data[0]["relationship"] == "REQUIRES"
    assert data[0]["target_entity_id"] == str(e2)


def test_api_entity_impact(client):
    """Tests GET /api/v1/entities/{type}/{id}/impact endpoint."""
    source_id = uuid.uuid4()
    resp = client.get(f"/api/v1/entities/TRANSPORT_LEG/{source_id}/impact?depth=3")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    data = body["data"]
    assert data["source_entity_type"] == "TRANSPORT_LEG"
    assert data["depth_limit"] == 3


def test_api_mission_readiness(client, db_session):
    """Tests GET /api/v1/missions/{id}/readiness endpoint."""
    exp_id = uuid.uuid4()
    m_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-APIM-{uuid.uuid4().hex[:6]}", name="API Mission Exp", season="2026-2027"))
    db_session.add(MissionModel(id=m_id, expedition_id=exp_id, code=f"M-APIM-{uuid.uuid4().hex[:6]}", title="API Readiness Mission", type="SCIENCE", status="APPROVED"))
    db_session.commit()

    resp = client.get(f"/api/v1/missions/{m_id}/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    data = body["data"]
    assert data["mission_id"] == str(m_id)
    assert data["state"] in ("READY", "AT_RISK", "BLOCKED")
    # Must NOT have fake percentage
    assert "readiness_percentage" not in data
    assert "score" not in data


def test_api_expedition_readiness(client, db_session):
    """Tests GET /api/v1/expeditions/{id}/readiness endpoint."""
    exp_id = uuid.uuid4()
    db_session.add(ExpeditionModel(id=exp_id, code=f"EXP-APIE-{uuid.uuid4().hex[:6]}", name="API Readiness Exp", season="2026-2027"))
    db_session.commit()

    resp = client.get(f"/api/v1/expeditions/{exp_id}/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    data = body["data"]
    assert data["expedition_id"] == str(exp_id)
    assert data["state"] in ("READY", "AT_RISK", "BLOCKED")
    assert "explanation" in data


def test_api_constraints_list_and_evaluate(client, db_session):
    """Tests GET /api/v1/constraints and GET /api/v1/constraints/evaluate."""
    c_id = uuid.uuid4()
    c_code = f"CONST-APITEST-{uuid.uuid4().hex[:6]}"
    db_session.add(ConstraintModel(
        id=c_id,
        code=c_code,
        name="API Constraint Test",
        type="OPERATIONAL",
        rule_code="MISSION_RESOURCE_REQUIRED",
        subject_type="MISSION",
        subject_id=uuid.uuid4()
    ))
    db_session.commit()

    # 1. List constraints
    resp_list = client.get("/api/v1/constraints")
    assert resp_list.status_code == 200
    list_body = resp_list.json()
    assert any(c["code"] == c_code for c in list_body["data"])

    # 2. Evaluate all constraints
    resp_eval = client.get("/api/v1/constraints/evaluate")
    assert resp_eval.status_code == 200
    eval_body = resp_eval.json()
    assert any(c["code"] == c_code for c in eval_body["data"])
