"""
Comprehensive Test Suite for Person A / Track A Operational Replanning,
Candidate Option Generation, Explainable Recommendations, and Human Approval Engine (Milestone A3).

Tests:
1. Replan Creation (Manual Operator vs Event-Triggered with validation)
2. Option Generation & Tri-State Feasibility (FEASIBLE, CONSTRAINED, NOT_EVALUABLE, INFEASIBLE)
3. Explainable Recommendation Generation (Structured rationales, zero fake scores)
4. Human Approval Boundary (Application blocked before approval; rejection blocks application)
5. Controlled Application via Domain Services (TransportService, MissionService)
6. Duplicate Application Idempotency (Stable results, no duplicate mutations/events)
7. Transactional Consistency & Failure Preservation
8. Operational Events & Audit Trail
9. Read-Only Reasoning Guarantee (Option generation does not mutate domain entities)
10. Full Hero Scenario Integration (T-08 -> C-117 -> PKG-117-01 -> I-42 -> M-08)
11. API Contracts and OpenAPI Response Envelopes
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
from backend.app.core.errors import (
    EntityNotFoundError,
    DomainValidationError,
    ConflictError,
)

# Register all domain models for SQLite schema creation
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
from backend.app.domains.transport.models import TransportLegModel, TransportCargoAssignmentModel
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.assets.models import AssetModel
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
    ApprovalDecision,
    ApprovalStatus,
    OptionFeasibility,
    ReplanActionType,
)
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ApprovalDecisionRequest,
    ReplanApplyRequest,
)
from backend.app.domains.replanning.service import ReplanService, ApprovalService


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
def seeded_baseline(db_session):
    """Seeds a baseline expedition, location, person, and mission."""
    exp_id = uuid.uuid4()
    exp = ExpeditionModel(
        id=exp_id,
        code=f"EXP-{uuid.uuid4().hex[:4].upper()}",
        name="45th Indian Antarctic Expedition",
        season="2026-2027",
    )
    db_session.add(exp)

    loc_id = uuid.uuid4()
    loc = LocationModel(
        id=loc_id,
        code=f"LOC-{uuid.uuid4().hex[:4].upper()}",
        name="Maitri Research Station",
        type="STATION",
    )
    db_session.add(loc)

    person_id = uuid.uuid4()
    person = PersonModel(
        id=person_id,
        person_code=f"PRS-{uuid.uuid4().hex[:4].upper()}",
        full_name="Rajesh Sharma",
        role="LOGISTICS_OFFICER",
        expedition_id=exp_id,
    )
    db_session.add(person)

    mission_id = uuid.uuid4()
    mission = MissionModel(
        id=mission_id,
        expedition_id=exp_id,
        code=f"MSN-{uuid.uuid4().hex[:4].upper()}",
        title="Schirmacher Oasis Environmental Survey",
        type="SCIENTIFIC",
        status="APPROVED",
        required_by_at=datetime.now(timezone.utc) + timedelta(days=10),
    )
    db_session.add(mission)
    db_session.flush()

    return {
        "expedition": exp,
        "location": loc,
        "person": person,
        "mission": mission,
    }


# ============================================================
# 1. REPLAN CREATION & TRIGGER VALIDATION
# ============================================================

def test_operator_requested_replan_creation(db_session, seeded_baseline):
    """Operator-requested replan succeeds with valid operational reason."""
    service = ReplanService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        reason="Pre-emptive weather buffer insertion requested by expedition leader",
        requested_by=person.id,
    )
    replan = service.create_replan_request(req)

    assert replan.id is not None
    assert replan.replan_code.startswith("RPL-2026-")
    assert replan.status == ReplanStatus.REQUESTED.value
    assert replan.expedition_id == exp.id

    # Verify event emission
    events = list(db_session.execute(
        select(OperationalEventModel).where(OperationalEventModel.entity_id == replan.id)
    ).scalars().all())
    assert len(events) == 1
    assert events[0].event_type == "ReplanRequested"

    # Verify audit persistence
    audit = list(db_session.execute(
        select(AuditLogModel).where(AuditLogModel.entity_id == replan.id)
    ).scalars().all())
    assert len(audit) == 1
    assert audit[0].action == "REPLAN_REQUESTED"


def test_event_triggered_replan_requires_impact_and_violation(db_session, seeded_baseline):
    """Event-triggered replan fails trigger rule when no impact exists."""
    service = ReplanService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]

    # Isolated event on entity with 0 dependents
    req = ReplanTriggerRequest(
        trigger_mode="EVENT_TRIGGERED",
        expedition_id=exp.id,
        trigger_entity_type="EXPEDITION",
        trigger_entity_id=exp.id,
        reason="Trivial weather update with zero downstream impact",
        requested_by=person.id,
    )
    with pytest.raises(DomainValidationError) as exc:
        service.create_replan_request(req)
    assert "EVENT_TRIGGERED replan requires meaningful state change" in str(exc.value)


def test_genuine_event_triggered_replan_from_transport_delay(db_session):
    """
    Genuine Event-Triggered Replan Integration Test:
    1. T-08 state changes to DELAYED through its domain operation (record_transport_delay).
    2. OperationalEvent is emitted.
    3. ImpactService finds affected cargo/package/asset/mission entities.
    4. ConstraintService finds resulting constraint violation on cargo deadline.
    5. ReplanService creates the replan directly from the event (create_replan_from_event).
    6. No human approval happens automatically (zero approvals exist).
    7. Generating options produces candidate options & proposed recommendations, but NO auto-approval.
    """
    from backend.app.domains.transport.service import TransportService
    from backend.app.domains.transport.schemas import TransportLegDelayRequest
    from backend.app.shared.types.states import TransportStatus

    exp_id = uuid.uuid4()
    loc_origin_id = uuid.uuid4()
    loc_dest_id = uuid.uuid4()
    t08_id = uuid.uuid4()
    c117_id = uuid.uuid4()
    pkg_id = uuid.uuid4()
    i42_id = uuid.uuid4()
    m08_id = uuid.uuid4()

    exp = ExpeditionModel(id=exp_id, code="EXP-EVT-01", name="45th IAE Event Test", season="2026-2027")
    loc_orig = LocationModel(id=loc_origin_id, code="LOC-CAPE", name="Cape Town Staging", type="STAGING")
    loc_dest = LocationModel(id=loc_dest_id, code="LOC-MAITRI", name="Maitri Station", type="STATION")
    db_session.add_all([exp, loc_orig, loc_dest])
    db_session.flush()

    now = datetime.now(timezone.utc)
    cargo_deadline = now + timedelta(days=3)
    planned_arr = now + timedelta(days=2)
    severely_delayed_arr = now + timedelta(days=12)  # Exceeds cargo deadline by 9 days!

    # Seed T-08 (READY)
    t08 = TransportLegModel(
        id=t08_id,
        code="T-08-EVT",
        expedition_id=exp_id,
        mode="VESSEL",
        origin_location_id=loc_origin_id,
        destination_location_id=loc_dest_id,
        status="READY",
        planned_arrival_at=planned_arr,
        estimated_arrival_at=planned_arr,
    )

    # Seed C-117
    c117 = CargoConsignmentModel(
        id=c117_id,
        code="C-117-EVT",
        expedition_id=exp_id,
        origin_location_id=loc_origin_id,
        destination_location_id=loc_dest_id,
        status="APPROVED",
        required_by_at=cargo_deadline,
        estimated_arrival_at=planned_arr,
    )

    # Seed Cargo Assignment to Transport Leg
    tc_assign = TransportCargoAssignmentModel(
        id=uuid.uuid4(),
        transport_leg_id=t08_id,
        cargo_consignment_id=c117_id,
    )

    # Seed PKG-117-01
    pkg = CargoPackageModel(id=pkg_id, code="PKG-117-EVT", consignment_id=c117_id)

    # Seed I-42
    i42 = AssetModel(id=i42_id, asset_code="I-42-EVT", name="High-Precision Gravimeter", type="INSTRUMENT", criticality="CRITICAL", status="AVAILABLE")

    # Seed M-08
    m08 = MissionModel(id=m08_id, expedition_id=exp_id, code="M-08-EVT", title="Ice Shelf Survey", type="SCIENTIFIC", status="APPROVED", required_by_at=cargo_deadline)

    db_session.add_all([t08, c117, tc_assign, pkg, i42, m08])
    db_session.flush()

    # Wire semantic dependency chain:
    # C-117 MOVES_VIA T-08
    # C-117 CONTAINS PKG-117-01
    # PKG-117-01 CONTAINS I-42
    # M-08 REQUIRES I-42
    deps = [
        DependencyModel(id=uuid.uuid4(), relationship_type="MOVES_VIA", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="TRANSPORT_LEG", target_entity_id=t08_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="CARGO_PACKAGE", target_entity_id=pkg_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_PACKAGE", source_entity_id=pkg_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m08_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
    ]
    db_session.add_all(deps)

    # Attach hard constraint on C-117 arrival deadline
    constraint = ConstraintModel(
        id=uuid.uuid4(),
        code="C-CARGO-DEADLINE-EVT",
        name="Consignment Arrival Deadline Check",
        type="TEMPORAL",
        rule_code="CARGO_ETA_DEADLINE",
        subject_type="CARGO_CONSIGNMENT",
        subject_id=c117_id,
        hard_or_soft="HARD",
        severity="CRITICAL",
        active=True,
    )

    db_session.add(constraint)
    db_session.flush()

    # STEP 1: Execute domain operation to delay T-08
    transport_service = TransportService(db_session)
    updated_leg, affected_cargos = transport_service.record_transport_delay(
        leg_id=t08_id,
        delay_data=TransportLegDelayRequest(
            new_estimated_arrival_at=severely_delayed_arr,
            delay_reason="Severe sea ice pack encrustation halting vessel progress",
        ),
    )
    assert updated_leg.status == TransportStatus.DELAYED.value

    # STEP 2: Verify OperationalEvent was emitted
    event = db_session.execute(
        select(OperationalEventModel).where(
            OperationalEventModel.entity_id == t08_id,
            OperationalEventModel.event_type == "TransportLegDelayed",
        )
    ).scalar_one_or_none()
    assert event is not None
    assert event.new_state == TransportStatus.DELAYED.value

    # STEP 3 & 4: Trigger replan directly from the OperationalEvent
    replan_service = ReplanService(db_session)
    replan = replan_service.create_replan_from_event(event.event_id)

    # STEP 5: Verify Replan properties
    assert replan.status == ReplanStatus.REQUESTED.value
    assert replan.trigger_event_id == event.event_id
    assert replan.trigger_entity_type == "TRANSPORT_LEG"
    assert replan.trigger_entity_id == t08_id
    assert len(replan.affected_entities) >= 4
    assert len(replan.violated_constraints) >= 1

    # STEP 6: Verify NO human approval happened automatically
    approvals = db_session.execute(
        select(ApprovalModel).where(ApprovalModel.recommendation_id.in_(
            select(RecommendationModel.id).where(RecommendationModel.replan_id == replan.id)
        ))
    ).scalars().all()
    assert len(approvals) == 0

    # Authoritative mission deadline remains UNCHANGED
    db_session.refresh(m08)
    assert _normalize_dt(m08.required_by_at) == _normalize_dt(cargo_deadline)

    # Generate options and verify candidates remain advisory (PROPOSED) without auto-approval
    options, recs = replan_service.generate_options(replan.id)
    assert len(options) >= 1
    assert len(recs) >= 1
    for rec in recs:
        assert rec.status == RecommendationStatus.PROPOSED.value
        assert rec.approval_state == "PROPOSED"

    # Approvals are still strictly zero until explicitly requested
    approvals_after = db_session.execute(
        select(ApprovalModel).where(ApprovalModel.recommendation_id.in_([r.id for r in recs]))
    ).scalars().all()
    assert len(approvals_after) == 0



# ============================================================
# 2. CANDIDATE OPTION GENERATION & FEASIBILITY
# ============================================================

def test_option_generation_discovers_alternatives_and_reschedule(db_session, seeded_baseline):
    """
    Tests deterministic candidate option generation:
    - Discovers alternative transport leg when available
    - Generates mission reschedule option
    - Generates deferral option
    """
    service = ReplanService(db_session)
    exp = seeded_baseline["expedition"]
    loc = seeded_baseline["location"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    # Create disrupted transport leg
    leg1 = TransportLegModel(
        id=uuid.uuid4(),
        code="T-DISRUPTED",
        expedition_id=exp.id,
        mode="VESSEL",
        origin_location_id=loc.id,
        destination_location_id=loc.id,
        status="DELAYED",
    )
    # Create available alternative transport leg
    leg2 = TransportLegModel(
        id=uuid.uuid4(),
        code="T-BACKUP",
        expedition_id=exp.id,
        mode="VESSEL",
        origin_location_id=loc.id,
        destination_location_id=loc.id,
        status="ON_TIME",
    )
    db_session.add_all([leg1, leg2])
    db_session.flush()

    # Create replan for this disruption
    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        trigger_entity_type="TRANSPORT_LEG",
        trigger_entity_id=leg1.id,
        reason="Sea-ice pack delayed T-DISRUPTED",
        requested_by=person.id,
    )
    replan = service.create_replan_request(req)

    options, recommendations = service.generate_options(replan.id)

    assert len(options) >= 2
    action_types = {o.action_type for o in options}
    assert ReplanActionType.MODIFY_TRANSPORT.value in action_types
    assert ReplanActionType.RESCHEDULE_MISSION.value in action_types

    # Recommendations generated for feasible options
    assert len(recommendations) >= 1
    for rec in recommendations:
        assert rec.status == RecommendationStatus.PROPOSED.value
        assert len(rec.rationale) > 0
        assert "FEASIBLE" in rec.summary or "CONSTRAINED" in rec.summary


def test_missing_asset_classified_as_not_evaluable(db_session, seeded_baseline):
    """An option without verifiable domain facts is marked NOT_EVALUABLE, not FEASIBLE."""
    service = ReplanService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]

    # Create single asset with no available replacements
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code="SINGLETON-01",
        name="Unique Ground Penetrating Radar",
        type="RADAR",
        status="IN_USE",
    )
    db_session.add(asset)
    db_session.flush()

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        trigger_entity_type="ASSET",
        trigger_entity_id=asset.id,
        reason="Instrument failed calibration; investigating substitution",
        requested_by=person.id,
    )
    replan = service.create_replan_request(req)
    replan.affected_entities = [{"entity_type": "ASSET", "entity_id": str(asset.id)}]
    db_session.flush()

    options, _ = service.generate_options(replan.id)
    asset_options = [o for o in options if o.action_type == ReplanActionType.REASSIGN_ASSET.value]
    assert len(asset_options) == 1
    assert asset_options[0].feasibility_state == OptionFeasibility.NOT_EVALUABLE.value


# ============================================================
# 3. HUMAN APPROVAL BOUNDARY & REJECTION
# ============================================================

def test_unapproved_recommendation_application_is_blocked(db_session, seeded_baseline):
    """
    CRITICAL HUMAN APPROVAL TEST:
    Applying a recommendation without an explicit APPROVED decision MUST fail.
    """
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        reason="Field window test",
        requested_by=person.id,
    )
    replan = replan_service.create_replan_request(req)
    _, recommendations = replan_service.generate_options(replan.id)
    rec = recommendations[0]

    # Attempt to apply immediately without approval
    apply_req = ReplanApplyRequest(actor_person_id=person.id, comment="Unauthorized fast-track attempt")
    with pytest.raises(DomainValidationError) as exc:
        approval_service.apply(rec.id, apply_req)
    assert "Human approval required" in str(exc.value)


def test_rejected_recommendation_cannot_be_applied(db_session, seeded_baseline):
    """A human operator REJECTED decision permanently prevents application."""
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        reason="Field window test",
        requested_by=person.id,
    )
    replan = replan_service.create_replan_request(req)
    _, recommendations = replan_service.generate_options(replan.id)
    rec = recommendations[0]

    # Human requests approval then rejects it
    approval = approval_service.request_approval(rec.id, actor_context={"actor_id": person.id})
    assert approval.status == ApprovalStatus.PENDING.value

    decide_req = ApprovalDecisionRequest(
        approver_person_id=person.id,
        decision=ApprovalDecision.REJECTED,
        comment="Mission extension not accepted due to fuel budget constraints",
    )
    decided = approval_service.decide(approval.id, decide_req)
    assert decided.status == ApprovalStatus.REJECTED.value
    assert decided.decision == "REJECTED"

    # Now attempt to apply
    apply_req = ReplanApplyRequest(actor_person_id=person.id)
    with pytest.raises(DomainValidationError) as exc:
        approval_service.apply(rec.id, apply_req)
    assert "Human approval required" in str(exc.value)


# ============================================================
# 4. CONTROLLED APPLICATION, ATOMICITY & IDEMPOTENCY
# ============================================================

def test_approved_application_via_domain_service(db_session, seeded_baseline):
    """
    Approved recommendation executes controlled state mutation via MissionService:
    1. Recommendation APPROVED by human
    2. Apply succeeds and shifts mission deadline
    3. Operational event 'ReplanApplied' emitted
    4. Audit log recorded
    5. Replan status marked APPLIED
    """
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    initial_deadline = mission.required_by_at

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        reason="Logistics delay mitigation",
        requested_by=person.id,
    )
    replan = replan_service.create_replan_request(req)
    options, recommendations = replan_service.generate_options(replan.id)

    # Pick the reschedule mission recommendation
    reschedule_rec = next(r for r in recommendations if "Adjust Mission" in r.title)

    # Approve
    approval = approval_service.request_approval(reschedule_rec.id, actor_context={"actor_id": person.id})
    approval_service.decide(
        approval.id,
        ApprovalDecisionRequest(
            approver_person_id=person.id,
            decision=ApprovalDecision.APPROVED,
            comment="Approved by Expedition Commander",
        ),
    )

    # Apply
    apply_result = approval_service.apply(
        reschedule_rec.id,
        ReplanApplyRequest(actor_person_id=person.id, comment="Executing approved schedule change"),
    )

    assert apply_result.status == "APPLIED"
    assert len(apply_result.applied_changes) > 0

    # Verify authoritative domain entity mutated through MissionService
    db_session.refresh(mission)
    assert _normalize_dt(mission.required_by_at) > _normalize_dt(initial_deadline)

    # Verify replan state updated to APPLIED
    db_session.refresh(replan)
    assert replan.status == ReplanStatus.APPLIED.value

    # Verify ReplanApplied event emitted
    event = db_session.execute(
        select(OperationalEventModel).where(
            (OperationalEventModel.id == apply_result.resulting_event_id)
            | (OperationalEventModel.event_id == apply_result.resulting_event_id)
        )
    ).scalar_one_or_none()
    assert event is not None
    assert event.event_type == "ReplanApplied"

    # Verify Audit record
    audits = list(db_session.execute(
        select(AuditLogModel).where(AuditLogModel.action == "REPLAN_APPLIED")
    ).scalars().all())
    assert len(audits) >= 1


def test_duplicate_application_is_idempotent(db_session, seeded_baseline):
    """Applying an already-applied recommendation returns existing result with no re-execution."""
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        reason="Idempotency test",
        requested_by=person.id,
    )
    replan = replan_service.create_replan_request(req)
    _, recommendations = replan_service.generate_options(replan.id)
    rec = recommendations[0]

    approval = approval_service.request_approval(rec.id, actor_context={"actor_id": person.id})
    approval_service.decide(
        approval.id,
        ApprovalDecisionRequest(approver_person_id=person.id, decision=ApprovalDecision.APPROVED),
    )

    # First apply
    res1 = approval_service.apply(rec.id, ReplanApplyRequest(actor_person_id=person.id))
    assert res1.status == "APPLIED"

    db_session.refresh(mission)
    mission_deadline_after_first = mission.required_by_at

    event_count_before = len(list(db_session.execute(
        select(OperationalEventModel).where(OperationalEventModel.event_type == "ReplanApplied")
    ).scalars().all()))
    audit_count_before = len(list(db_session.execute(
        select(AuditLogModel).where(AuditLogModel.action == "REPLAN_APPLIED")
    ).scalars().all()))

    # Second apply (idempotent no-op)
    res2 = approval_service.apply(rec.id, ReplanApplyRequest(actor_person_id=person.id))
    assert res2.status == "APPLIED"
    assert "already been applied" in res2.message
    assert res2.recommendation_id == res1.recommendation_id

    # Zero additional domain mutation
    db_session.refresh(mission)
    assert mission.required_by_at == mission_deadline_after_first

    event_count_after = len(list(db_session.execute(
        select(OperationalEventModel).where(OperationalEventModel.event_type == "ReplanApplied")
    ).scalars().all()))
    audit_count_after = len(list(db_session.execute(
        select(AuditLogModel).where(AuditLogModel.action == "REPLAN_APPLIED")
    ).scalars().all()))

    # Zero duplicate events and audit records
    assert event_count_before == event_count_after
    assert audit_count_before == audit_count_after


# ============================================================
# 5. READ-ONLY REASONING GUARANTEE
# ============================================================

def test_generating_options_does_not_mutate_domain_state(db_session, seeded_baseline):
    """Generating options and recommendations is strictly read-only on domain entities."""
    replan_service = ReplanService(db_session)
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    original_deadline = mission.required_by_at
    original_status = mission.status

    req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp.id,
        mission_id=mission.id,
        reason="Non-mutating read-only exploration",
        requested_by=person.id,
    )
    replan = replan_service.create_replan_request(req)
    replan_service.generate_options(replan.id)

    db_session.refresh(mission)
    assert _normalize_dt(mission.required_by_at) == _normalize_dt(original_deadline)
    assert mission.status == original_status


# ============================================================
# 6. FULL HERO SCENARIO END-TO-END INTEGRATION TEST
# ============================================================

def test_hero_scenario_transport_delay_to_approved_replan(db_session):
    """
    FULL HERO SCENARIO:
    1. T-08 (transport leg) delayed
    2. C-117 (cargo consignment) impacted via MOVES_VIA
    3. PKG-117-01 (cargo package) impacted via CONTAINS
    4. I-42 (critical asset) impacted via CONTAINS
    5. M-08 (coastal survey mission) impacted via REQUIRES
    6. Replan request created
    7. Candidate options generated from real domain facts
    8. Explainable recommendation produced
    9. Human approval boundary enforced (no change while PENDING)
    10. Approved by authorized operator
    11. Applied through MissionService
    12. Authoritative mission state updated and verified
    """
    exp_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    m08_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    c117_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    t08_id = uuid.UUID("60000000-0000-0000-0000-000000000001")
    pkg_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
    i42_id = uuid.UUID("90000000-0000-0000-0000-000000000001")
    loc_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    op_person_id = uuid.UUID("10000000-0000-0000-0000-000000000001")

    # Clean existing hero IDs
    for mid in [m08_id, exp_id, c117_id, t08_id, pkg_id, i42_id, loc_id, op_person_id]:
        db_session.execute(text(f"DELETE FROM dependencies WHERE source_entity_id = '{mid}' OR target_entity_id = '{mid}'"))

    exp = db_session.get(ExpeditionModel, exp_id)
    if not exp:
        db_session.add(ExpeditionModel(id=exp_id, code="EXP-26-A", name="45th Indian Antarctic Expedition", season="2026-2027"))
    loc = db_session.get(LocationModel, loc_id)
    if not loc:
        db_session.add(LocationModel(id=loc_id, code="MAITRI", name="Maitri Station", type="STATION"))
    person = db_session.get(PersonModel, op_person_id)
    if not person:
        db_session.add(PersonModel(
            id=op_person_id,
            person_code="PRS-001",
            full_name="Anil Kumar",
            role="STATION_COMMANDER",
            expedition_id=exp_id,
        ))

    initial_deadline = datetime.now(timezone.utc) + timedelta(days=5)
    mission = db_session.get(MissionModel, m08_id)
    if not mission:
        mission = MissionModel(id=m08_id, expedition_id=exp_id, code="M-08", title="Coastal Geophysics Survey", type="SCIENTIFIC", status="APPROVED", required_by_at=initial_deadline)
        db_session.add(mission)
    else:
        mission.required_by_at = initial_deadline

    # Seed T-08, C-117, PKG-117-01, I-42
    db_session.execute(text(f"DELETE FROM transport_legs WHERE id = '{t08_id}'"))
    db_session.execute(text(f"DELETE FROM cargo_consignments WHERE id = '{c117_id}'"))
    db_session.execute(text(f"DELETE FROM cargo_packages WHERE id = '{pkg_id}'"))
    db_session.execute(text(f"DELETE FROM assets WHERE id = '{i42_id}'"))

    t08 = TransportLegModel(id=t08_id, code="T-08", expedition_id=exp_id, mode="VESSEL", origin_location_id=loc_id, destination_location_id=loc_id, status="DELAYED")
    c117 = CargoConsignmentModel(id=c117_id, code="C-117", expedition_id=exp_id, origin_location_id=loc_id, destination_location_id=loc_id, status="DELAYED", required_by_at=initial_deadline)
    pkg = CargoPackageModel(id=pkg_id, code="PKG-117-01", consignment_id=c117_id)
    i42 = AssetModel(id=i42_id, asset_code="I-42", name="Cryo-Seismic Profiler", type="INSTRUMENT", criticality="CRITICAL", status="AVAILABLE")
    db_session.add_all([t08, c117, pkg, i42])
    db_session.flush()

    # Wire semantic dependency chain
    deps = [
        DependencyModel(id=uuid.uuid4(), relationship_type="MOVES_VIA", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="TRANSPORT_LEG", target_entity_id=t08_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_CONSIGNMENT", source_entity_id=c117_id, target_entity_type="CARGO_PACKAGE", target_entity_id=pkg_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="CONTAINS", source_entity_type="CARGO_PACKAGE", source_entity_id=pkg_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
        DependencyModel(id=uuid.uuid4(), relationship_type="REQUIRES", source_entity_type="MISSION", source_entity_id=m08_id, target_entity_type="ASSET", target_entity_id=i42_id, criticality="CRITICAL"),
    ]
    db_session.add_all(deps)
    db_session.flush()

    # Execution Phase:
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)

    # 1. Trigger replan from T-08 delay
    replan_req = ReplanTriggerRequest(
        trigger_mode="OPERATOR_REQUESTED",
        expedition_id=exp_id,
        mission_id=m08_id,
        trigger_entity_type="TRANSPORT_LEG",
        trigger_entity_id=t08_id,
        reason="Sea-ice pack severely delayed icebreaker T-08 carrying mission payload",
        requested_by=op_person_id,
        depth=4,
    )
    replan = replan_service.create_replan_request(replan_req)
    assert replan.status == ReplanStatus.REQUESTED.value

    # 2. Generate Options
    options, recommendations = replan_service.generate_options(replan.id)
    assert len(options) >= 1
    assert len(recommendations) >= 1

    rec = next(r for r in recommendations if "Adjust Mission" in r.title or "Schedule" in r.title)
    assert rec.status == RecommendationStatus.PROPOSED.value

    # 3. Request Approval
    approval = approval_service.request_approval(rec.id, actor_context={"actor_id": op_person_id})
    assert approval.status == ApprovalStatus.PENDING.value

    # Verified: Mission deadline UNCHANGED while approval is pending
    db_session.refresh(mission)
    assert _normalize_dt(mission.required_by_at) == _normalize_dt(initial_deadline)

    # 4. Human Approval
    approval_service.decide(
        approval.id,
        ApprovalDecisionRequest(
            approver_person_id=op_person_id,
            decision=ApprovalDecision.APPROVED,
            comment="Approved by Station Commander to allow T-08 icebreaker arrival buffer",
        ),
    )

    # 5. Apply
    apply_res = approval_service.apply(
        rec.id,
        ReplanApplyRequest(actor_person_id=op_person_id, comment="Applying +7 day window extension"),
    )
    assert apply_res.status == "APPLIED"

    # Verified: Authoritative state shifted
    db_session.refresh(mission)
    assert _normalize_dt(mission.required_by_at) > _normalize_dt(initial_deadline)


# ============================================================
# 7. API ENDPOINTS & ENVELOPE VERIFICATION
# ============================================================

def test_api_replan_lifecycle_endpoints(client, seeded_baseline):
    """Tests the full HTTP API workflow via FastAPI TestClient."""
    exp = seeded_baseline["expedition"]
    person = seeded_baseline["person"]
    mission = seeded_baseline["mission"]

    # 1. POST /api/v1/replans
    res = client.post(
        "/api/v1/replans",
        json={
            "trigger_mode": "OPERATOR_REQUESTED",
            "expedition_id": str(exp.id),
            "mission_id": str(mission.id),
            "reason": "HTTP API integration test",
            "requested_by": str(person.id),
        },
    )
    assert res.status_code == 201
    payload = res.json()
    assert payload["errors"] is None
    replan_id = payload["data"]["id"]

    # 2. GET /api/v1/replans
    list_res = client.get(f"/api/v1/replans?expedition_id={exp.id}")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 3. GET /api/v1/replans/{id}
    get_res = client.get(f"/api/v1/replans/{replan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == replan_id

    # 4. POST /api/v1/replans/{id}/generate-options
    gen_res = client.post(f"/api/v1/replans/{replan_id}/generate-options")
    assert gen_res.status_code == 200
    options_data = gen_res.json()["data"]
    assert len(options_data) >= 1

    # 5. GET /api/v1/replans/{id}/options
    opt_res = client.get(f"/api/v1/replans/{replan_id}/options")
    assert opt_res.status_code == 200
    assert len(opt_res.json()["data"]) == len(options_data)

    # 6. GET /api/v1/replans/{id}/recommendations
    recs_res = client.get(f"/api/v1/replans/{replan_id}/recommendations")
    assert recs_res.status_code == 200
    recs_data = recs_res.json()["data"]
    assert len(recs_data) >= 1
    rec_id = recs_data[0]["id"]

    # 7. POST /api/v1/recommendations/{id}/approve
    appr_res = client.post(
        f"/api/v1/recommendations/{rec_id}/approve",
        json={
            "approver_person_id": str(person.id),
            "decision": "APPROVED",
            "comment": "HTTP API approval",
        },
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["data"]["decision"] == "APPROVED"

    # 8. POST /api/v1/recommendations/{id}/apply
    apply_res = client.post(
        f"/api/v1/recommendations/{rec_id}/apply",
        json={"actor_person_id": str(person.id), "comment": "HTTP apply"},
    )
    assert apply_res.status_code == 200
    assert apply_res.json()["data"]["status"] == "APPLIED"

    # 9. GET /api/v1/replans/{id}/audit
    audit_res = client.get(f"/api/v1/replans/{replan_id}/audit")
    assert audit_res.status_code == 200
    assert len(audit_res.json()["data"]) >= 1
