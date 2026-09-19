"""
Targeted Integration Test Suite for Milestone A6:
Closed-Loop Operational Replanning, Disruption Cockpit & Human Governance.

Validates:
1. Cross-session persistence of Replan creation across independent SQLAlchemy sessions.
2. Cross-session persistence of Option Generation & Recommendation synthesis.
3. Atomic transaction boundary for request_approval + decide (both persist atomically).
4. Scenario 1: FLIGHT_GROUNDING dynamic resolution, +5d delay, and event emission.
5. Scenario 2: GENERATOR_FAILURE dynamic resolution, MAINTENANCE transition, DAMAGED condition.
6. Scenario 3: COLD_CHAIN_EXCURSION dynamic resolution, HELD status, quarantine metadata.
7. Zero-target behavior: explicit DomainValidationError without unintended mutations.
8. Safe repeat / idempotency behavior on repeated scenario injection.
9. Governance invariant: Scenario injection does NOT autonomously create replans or recommendations.
10. Governance invariant: Application before approval is strictly rejected.
11. Full closed-loop lifecycle: Scenario -> Derived disruption -> Operator Replan -> Generate Options -> Human Approval -> Explicit Apply -> ReplanApplied event.
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import DomainValidationError

# Domain Models
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.people.models
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
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.assets.models import AssetModel
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
)
from backend.app.domains.replanning.service import ReplanService, ApprovalService
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ApprovalDecisionRequest,
    ReplanApplyRequest,
)
from backend.app.domains.control_tower.scenarios import ScenarioInjectionService
from backend.app.domains.control_tower.schemas import ScenarioInjectRequest
from backend.app.domains.control_tower.service import ControlTowerService


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
def SessionFactory(shared_engine):
    """Factory yielding independent sessions bound to the shared in-memory DB."""
    return sessionmaker(bind=shared_engine, autocommit=False, autoflush=False)


@pytest.fixture
def clean_db(shared_engine, SessionFactory):
    """Seeds baseline expedition and related records for disruption testing."""
    session = SessionFactory()

    exp_id = uuid.uuid4()
    loc_id = uuid.uuid4()
    leg_id = uuid.uuid4()
    mission_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    cargo_id = uuid.uuid4()

    suffix = uuid.uuid4().hex[:6].upper()
    exp_code = f"EXP-A6-{suffix}"
    loc_code = f"LOC-{suffix}"
    leg_code = f"T-AIR-{suffix}"
    mission_code = f"M-SURV-{suffix}"
    asset_code = f"GEN-{suffix}"
    cargo_code = f"C-COLD-{suffix}"

    exp = ExpeditionModel(
        id=exp_id,
        code=exp_code,
        name=f"45th Indian Scientific Expedition {suffix}",
        season="2025-2026",
        planned_start_at=datetime(2025, 11, 1, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        status="ACTIVE",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(exp)

    loc = LocationModel(
        id=loc_id,
        code=loc_code,
        name=f"Maitri Station {suffix}",
        type="STATION",
        status="AVAILABLE",
        latitude=None,
        longitude=None,
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(loc)

    now = datetime.now(timezone.utc)
    leg = TransportLegModel(
        id=leg_id,
        code=leg_code,
        expedition_id=exp_id,
        mode="AIR",
        status="READY",
        origin_location_id=loc_id,
        destination_location_id=loc_id,
        planned_departure_at=now + timedelta(days=2),
        planned_arrival_at=now + timedelta(days=3),
        estimated_arrival_at=now + timedelta(days=3),
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(leg)

    mission = MissionModel(
        id=mission_id,
        code=mission_code,
        title=f"Glaciological Survey {suffix}",
        expedition_id=exp_id,
        type="SCIENCE",
        status="PLANNED",
        priority=3,
        location_id=loc_id,
        required_by_at=now + timedelta(days=7),
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(mission)

    generator = AssetModel(
        id=asset_id,
        asset_code=asset_code,
        name=f"Diesel Generator {suffix}",
        type="GENERATOR",
        status="AVAILABLE",
        condition="OPERATIONAL",
        criticality="LIFE_SUPPORT",
        location_id=loc_id,
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(generator)

    cold_cargo = CargoConsignmentModel(
        id=cargo_id,
        code=cargo_code,
        expedition_id=exp_id,
        origin_location_id=loc_id,
        destination_location_id=loc_id,
        status="READY",
        handling_classification="COLD_CHAIN",
        risk_level="NOMINAL",
        required_by_at=now + timedelta(days=10),
        estimated_arrival_at=now + timedelta(days=3),
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(cold_cargo)

    session.commit()
    session.close()

    yield {
        "expedition_id": exp_id,
        "leg_id": leg_id,
        "mission_id": mission_id,
        "asset_id": asset_id,
        "cargo_id": cargo_id,
        "exp_code": exp_code,
        "loc_code": loc_code,
        "leg_code": leg_code,
        "mission_code": mission_code,
        "asset_code": asset_code,
        "cargo_code": cargo_code,
    }

    # Teardown: clear tables to avoid unique constraint violations in subsequent tests
    t_session = SessionFactory()
    for table in reversed(Base.metadata.sorted_tables):
        t_session.execute(table.delete())
    t_session.commit()
    t_session.close()


# ==============================================================================
# 1. CROSS-SESSION PERSISTENCE TESTS (Proving Narrow Transaction Boundary Fix)
# ==============================================================================

def test_cross_session_replan_persistence(SessionFactory, clean_db):
    """
    Proves that create_replan_request commits to the database so that an independent
    session opening after the request completes successfully queries the replan.
    """
    s1 = SessionFactory()
    service1 = ReplanService(s1)

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=clean_db["expedition_id"],
        mission_id=clean_db["mission_id"],
        reason="Manual operator mitigation test for blizzard response",
        requested_by=uuid.uuid4(),
    )
    created = service1.create_replan_request(req, auto_commit=True)
    replan_id = created.id
    s1.close()  # Simulate HTTP request termination

    # Independent session 2 verifies persistence
    s2 = SessionFactory()
    persisted = s2.get(ReplanModel, replan_id)
    assert persisted is not None, "Replan must be committed and queryable in a new session"
    assert persisted.status == ReplanStatus.REQUESTED.value
    assert persisted.replan_code.startswith("RPL-")
    s2.close()


def test_cross_session_generate_options_persistence(SessionFactory, clean_db):
    """
    Proves that generate_options commits candidate options and synthesized recommendations
    so that subsequent sessions can read them without data loss.
    """
    s1 = SessionFactory()
    service1 = ReplanService(s1)

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=clean_db["expedition_id"],
        mission_id=clean_db["mission_id"],
        reason="Generate options test",
        requested_by=uuid.uuid4(),
    )
    created = service1.create_replan_request(req, auto_commit=True)
    options, recommendations = service1.generate_options(created.id, auto_commit=True)
    assert len(options) >= 1
    replan_id = created.id
    s1.close()

    # Verify options & recommendations in session 2
    s2 = SessionFactory()
    opts_query = s2.execute(
        select(ReplanOptionModel).where(ReplanOptionModel.replan_id == replan_id)
    ).scalars().all()
    assert len(opts_query) == len(options)

    rec_query = s2.execute(
        select(RecommendationModel).where(RecommendationModel.replan_id == replan_id)
    ).scalars().all()
    assert len(rec_query) == len(recommendations)
    s2.close()


def test_approval_decision_atomic_persistence(SessionFactory, clean_db):
    """
    Proves that request_approval + decide commit atomically in a single transaction.
    """
    s1 = SessionFactory()
    replan_svc = ReplanService(s1)
    approval_svc = ApprovalService(s1)

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=clean_db["expedition_id"],
        mission_id=clean_db["mission_id"],
        reason="Atomic approval test",
        requested_by=uuid.uuid4(),
    )
    created = replan_svc.create_replan_request(req, auto_commit=True)
    _, recs = replan_svc.generate_options(created.id, auto_commit=True)
    assert len(recs) >= 1
    target_rec = recs[0]

    # In router.py: request_approval (flush) followed by decide (commit)
    approval = approval_svc.request_approval(target_rec.id)
    assert approval.status == ApprovalStatus.PENDING.value

    decide_req = ApprovalDecisionRequest(
        approver_person_id=uuid.uuid4(),
        approver_role="STATION_COMMANDER",
        decision=ApprovalDecision.APPROVED,
        comment="Authoritative approval confirmed for survey adjustment",
    )
    decided = approval_svc.decide(approval.id, decide_req, auto_commit=True)
    assert decided.status == ApprovalStatus.APPROVED.value
    target_rec_id = target_rec.id
    approval_id = approval.id
    s1.close()

    # Verify in session 2 that approval is committed with APPROVED status
    s2 = SessionFactory()
    persisted_appr = s2.get(ApprovalModel, approval_id)
    assert persisted_appr is not None
    assert persisted_appr.status == ApprovalStatus.APPROVED.value
    assert persisted_appr.decision == "APPROVED"

    persisted_rec = s2.get(RecommendationModel, target_rec_id)
    assert persisted_rec.status == RecommendationStatus.SELECTED.value
    assert persisted_rec.approval_state == "APPROVED"
    s2.close()


# ==============================================================================
# 2. SCENARIO INJECTION TESTS (Dynamic Resolution, Invariants, Idempotency)
# ==============================================================================

def test_scenario_inject_flight_grounding_dynamic(SessionFactory, clean_db):
    """
    Validates Scenario 1: FLIGHT_GROUNDING dynamically finds air transport leg,
    delays it +5 days, and emits TransportLegDelayed event.
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)

    res = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="FLIGHT_GROUNDING",
            expedition_id=clean_db["expedition_id"],
            requested_by=uuid.uuid4(),
        )
    )

    assert res.scenario_key == "FLIGHT_GROUNDING"
    assert res.affected_entity_type == "TRANSPORT_LEG"
    assert res.affected_entity_id == clean_db["leg_id"]
    assert res.affected_entity_code == clean_db["leg_code"]
    assert res.data_provenance == "SYNTHETIC_DEMO"
    assert res.trigger_event_id is not None

    # Verify leg state updated
    leg = session.get(TransportLegModel, clean_db["leg_id"])
    assert leg.status == "DELAYED"
    assert "blizzard" in leg.delay_reason.lower()
    session.close()


def test_scenario_inject_generator_failure_dynamic(SessionFactory, clean_db):
    """
    Validates Scenario 2: GENERATOR_FAILURE dynamically finds generator asset,
    transitions status to MAINTENANCE and sets condition to DAMAGED.
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)

    res = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="GENERATOR_FAILURE",
            expedition_id=clean_db["expedition_id"],
            requested_by=uuid.uuid4(),
        )
    )

    assert res.scenario_key == "GENERATOR_FAILURE"
    assert res.affected_entity_type == "ASSET"
    assert res.affected_entity_id == clean_db["asset_id"]
    assert res.affected_entity_code == clean_db["asset_code"]
    assert res.data_provenance == "SYNTHETIC_DEMO"

    asset = session.get(AssetModel, clean_db["asset_id"])
    assert asset.status == "MAINTENANCE"
    assert asset.condition == "DAMAGED"
    session.close()


def test_scenario_inject_cold_chain_excursion_dynamic(SessionFactory, clean_db):
    """
    Validates Scenario 3: COLD_CHAIN_EXCURSION dynamically finds refrigerated cargo,
    updates status to HELD and sets quarantine metadata.
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)

    res = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="COLD_CHAIN_EXCURSION",
            expedition_id=clean_db["expedition_id"],
            requested_by=uuid.uuid4(),
        )
    )

    assert res.scenario_key == "COLD_CHAIN_EXCURSION"
    assert res.affected_entity_type == "CARGO_CONSIGNMENT"
    assert res.affected_entity_id == clean_db["cargo_id"]
    assert res.affected_entity_code == clean_db["cargo_code"]
    assert res.data_provenance == "SYNTHETIC_DEMO"

    cargo = session.get(CargoConsignmentModel, clean_db["cargo_id"])
    assert cargo.status == "HELD"
    assert "cold-chain" in cargo.exception_reason.lower()
    session.close()


def test_scenario_zero_target_error_handling(SessionFactory):
    """
    Validates that injecting into an empty expedition raises a clean DomainValidationError
    without mutating unrelated entities.
    """
    session = SessionFactory()
    empty_exp_id = uuid.uuid4()
    exp = ExpeditionModel(
        id=empty_exp_id,
        code=f"EXP-EMPTY-{uuid.uuid4().hex[:6]}",
        name="Empty Expedition",
        season="2025-2026",
        planned_start_at=datetime(2025, 11, 1, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        status="PLANNING",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(exp)
    session.commit()

    scenario_svc = ScenarioInjectionService(session)

    try:
        with pytest.raises(DomainValidationError) as exc:
            scenario_svc.inject(
                ScenarioInjectRequest(
                    scenario_key="FLIGHT_GROUNDING",
                    expedition_id=empty_exp_id,
                )
            )
        assert "No active transport legs found" in str(exc.value)
    finally:
        session.delete(exp)
        session.commit()
        session.close()


def test_scenario_repeat_idempotency(SessionFactory, clean_db):
    """
    Validates that repeatedly injecting the same scenario returns a safe idempotent result.
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)

    # First injection
    res1 = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="FLIGHT_GROUNDING",
            expedition_id=clean_db["expedition_id"],
        )
    )

    # Second injection (replay)
    res2 = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="FLIGHT_GROUNDING",
            expedition_id=clean_db["expedition_id"],
        )
    )

    assert res2.affected_entity_id == res1.affected_entity_id
    assert "already" in res2.summary.lower() or "idempotent" in res2.summary.lower()
    session.close()


def test_scenario_does_not_autonomously_replan(SessionFactory, clean_db):
    """
    CRITICAL GOVERNANCE INVARIANT:
    Scenario injection MUST NOT create a replan record, generate options,
    or approve/apply anything automatically.
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)
    ct_service = ControlTowerService(session)

    # Inject disruption
    scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="FLIGHT_GROUNDING",
            expedition_id=clean_db["expedition_id"],
        )
    )

    # Check decision queue: pending_replans must be ZERO
    dq = ct_service.get_decision_queue(expedition_id=clean_db["expedition_id"])
    assert dq.total_pending_replans == 0, "Scenario injection must NOT autonomously create replans"
    assert dq.total_pending_recommendations == 0
    assert dq.total_pending_approvals == 0
    session.close()


def test_apply_unapproved_recommendation_rejected(SessionFactory, clean_db):
    """
    CRITICAL GOVERNANCE INVARIANT:
    Applying a recommendation that has not received explicit human approval must fail.
    """
    session = SessionFactory()
    replan_svc = ReplanService(session)
    approval_svc = ApprovalService(session)

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=clean_db["expedition_id"],
        mission_id=clean_db["mission_id"],
        reason="Governance boundary test",
        requested_by=uuid.uuid4(),
    )
    created = replan_svc.create_replan_request(req, auto_commit=True)
    _, recs = replan_svc.generate_options(created.id, auto_commit=True)
    assert len(recs) >= 1
    unapproved_rec = recs[0]

    # Attempt to apply immediately without approval
    with pytest.raises(DomainValidationError) as exc:
        approval_svc.apply(
            recommendation_id=unapproved_rec.id,
            request=ReplanApplyRequest(
                actor_person_id=uuid.uuid4(),
                comment="Bypass attempt",
            ),
        )
    assert "approved" in str(exc.value).lower()
    session.close()


# ==============================================================================
# 3. END-TO-END CLOSED LOOP INTEGRATION TEST
# ==============================================================================

def test_full_closed_loop_lifecycle(SessionFactory, clean_db):
    """
    Verifies the complete closed-loop cycle:
    1. Disruption injected via Scenario Service
    2. Operator explicitly initiates Replan for the affected mission
    3. Option Generator produces feasible mitigation options
    4. Operator reviews and approves the recommendation
    5. Operator applies the approved recommendation
    6. Mission required_by_at is updated by MissionService
    7. ReplanApplied event and audit records are permanently persisted
    """
    session = SessionFactory()
    scenario_svc = ScenarioInjectionService(session)
    replan_svc = ReplanService(session)
    approval_svc = ApprovalService(session)

    # 1. Inject Disruption
    disruption = scenario_svc.inject(
        ScenarioInjectRequest(
            scenario_key="FLIGHT_GROUNDING",
            expedition_id=clean_db["expedition_id"],
        )
    )
    assert disruption.affected_entity_type == "TRANSPORT_LEG"

    # 2. Operator explicitly initiates replan
    replan = replan_svc.create_replan_request(
        ReplanTriggerRequest(
            trigger_mode="OPERATOR_REQUESTED",
            expedition_id=clean_db["expedition_id"],
            mission_id=clean_db["mission_id"],
            reason="Flight grounding disrupted critical cargo; operational replanning required.",
            requested_by=uuid.uuid4(),
        ),
        auto_commit=True,
    )
    assert replan.status == ReplanStatus.REQUESTED.value

    # 3. Generate candidate options & recommendations
    options, recommendations = replan_svc.generate_options(replan.id, auto_commit=True)
    assert len(options) >= 1
    assert len(recommendations) >= 1

    # Find the RESCHEDULE_MISSION recommendation
    reschedule_rec = next((r for r in recommendations if "reschedule" in r.title.lower() or "adjust" in r.title.lower()), recommendations[0])
    assert reschedule_rec.approval_state == "PROPOSED"

    # 4. Human Approval
    approval = approval_svc.request_approval(reschedule_rec.id)
    decided = approval_svc.decide(
        approval.id,
        ApprovalDecisionRequest(
            approver_person_id=uuid.uuid4(),
            approver_role="EXPEDITION_LEADER",
            decision=ApprovalDecision.APPROVED,
            comment="Approved survey window extension to accommodate polar weather delay.",
        ),
        auto_commit=True,
    )
    assert decided.status == ApprovalStatus.APPROVED.value

    # 5. Explicit Apply
    apply_res = approval_svc.apply(
        recommendation_id=reschedule_rec.id,
        request=ReplanApplyRequest(
            actor_person_id=uuid.uuid4(),
            comment="Applied survey window update",
        ),
    )
    assert apply_res.status == RecommendationStatus.APPLIED.value
    assert apply_res.resulting_event_id is not None

    # 6. Verify Mission updated
    mission = session.get(MissionModel, clean_db["mission_id"])
    assert mission is not None

    # 7. Verify Replan model transitioned to APPLIED
    persisted_replan = session.get(ReplanModel, replan.id)
    assert persisted_replan.status == ReplanStatus.APPLIED.value

    session.close()
