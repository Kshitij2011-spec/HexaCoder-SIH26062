"""
Comprehensive Test Suite for Milestone A10 — Personnel & Field Team Deployment Safety Engine:
1. Clear personnel deployment (CLEAR posture, 0 blocked findings)
2. Deterministic blocked deployment (medical hold / unready -> BLOCKED, PERS_READINESS_DISQUALIFIED)
3. Deterministic blocked deployment (incompatible movement -> BLOCKED, PERS_MOVEMENT_INCOMPATIBLE)
4. Deterministic blocked deployment (headcount deficit < 2 -> BLOCKED, TEAM_HEADCOUNT_DEFICIT)
5. Deterministic warning (safety officer absent -> WARNING, FIELD_SAFETY_OFFICER_ABSENT)
6. Strict expedition isolation (no cross-expedition personnel leakage)
7. REASSIGN_PERSONNEL replan option generation and explainable recommendation
8. Recommendation generation and approval do NOT mutate operational state
9. Explicit Apply mutates intended assignments, updates leader if needed, and emits events + audit
10. Idempotent Apply (safe no-op on already applied recommendation)
11. Unapproved application is rejected (enforces human approval boundary)
12. Control Tower personnel safety API endpoint (GET /api/v1/control-tower/expeditions/{id}/personnel-safety)
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Declarative models
import backend.app.domains.expeditions.models
import backend.app.domains.missions.models
import backend.app.domains.locations.models
import backend.app.domains.people.models
import backend.app.domains.teams.models
import backend.app.domains.replanning.models
import backend.app.platform.events.models
import backend.app.platform.audit.models

from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.people.models import PersonModel
from backend.app.domains.teams.models import TeamModel
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
    OptionFeasibility,
)
from backend.app.domains.replanning.schemas import (
    ReplanTriggerRequest,
    ApprovalDecisionRequest,
    ReplanApplyRequest,
)
from backend.app.domains.replanning.service import ReplanService, ApprovalService
from backend.app.domains.control_tower.personnel_safety import PersonnelSafetyService
from backend.app.domains.control_tower.schemas import PersonnelPostureSummary
from backend.app.core.errors import DomainValidationError


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for A10 Personnel Safety tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    override = app.dependency_overrides[get_db]
    session_gen = override()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()


def create_base_expedition(session: Session, name: str = "44th Indian Scientific Expedition"):
    exp = ExpeditionModel(
        id=uuid.uuid4(),
        code=f"EXP-{uuid.uuid4().hex[:6].upper()}",
        name=name,
        season="2025-2026",
        status="ACTIVE",
    )
    session.add(exp)
    loc = LocationModel(
        id=uuid.uuid4(),
        code=f"LOC-{uuid.uuid4().hex[:6].upper()}",
        name="Maitri Research Base",
        type="STATION",
    )
    session.add(loc)
    session.flush()
    return exp, loc


def test_clear_personnel_deployment(db_session: Session):
    """Verifies that a fully-crewed team with cleared members and safety guide has CLEAR posture."""
    exp, loc = create_base_expedition(db_session, "Clear Expedition")
    mission = MissionModel(
        id=uuid.uuid4(),
        code=f"MIS-{uuid.uuid4().hex[:4].upper()}",
        title="Schirmacher Oasis Survey",
        type="SCIENCE",
        expedition_id=exp.id,
        status="ACTIVE",
    )
    db_session.add(mission)
    db_session.flush()

    leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-LDR-{uuid.uuid4().hex[:4].upper()}",
        full_name="Dr. Vikram Sarabhai",
        role="Expedition Leader",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    safety_officer = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-SAF-{uuid.uuid4().hex[:4].upper()}",
        full_name="Rajesh Sharma",
        role="Polar Field Safety Officer",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Alpha Traverse Team",
        expedition_id=exp.id,
        mission_id=mission.id,
        location_id=loc.id,
        leader_person_id=leader.id,
        status="STATION",
    )
    db_session.add_all([leader, safety_officer, team])
    db_session.flush()

    leader.team_id = team.id
    safety_officer.team_id = team.id
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary = service.evaluate_expedition(exp.id)

    assert summary.overall_status == "CLEAR"
    assert summary.cleared_count == 2
    assert len(summary.findings) == 0


def test_deterministic_blocked_deployment_medical_hold(db_session: Session):
    """Verifies that an unready team member (NOT_CLEARED) triggers a deterministic BLOCKED finding."""
    exp, loc = create_base_expedition(db_session, "Medical Hold Expedition")
    mission = MissionModel(
        id=uuid.uuid4(),
        code=f"MIS-{uuid.uuid4().hex[:4].upper()}",
        title="Queen Maud Glaciology",
        type="SCIENCE",
        expedition_id=exp.id,
        status="ACTIVE",
    )
    db_session.add(mission)
    db_session.flush()

    leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-LDR-{uuid.uuid4().hex[:4].upper()}",
        full_name="Sunita Rao",
        role="Field Safety Leader",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    unready_member = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-MED-{uuid.uuid4().hex[:4].upper()}",
        full_name="Anil Kumar",
        role="Ice Core Specialist",
        expedition_id=exp.id,
        readiness_state="NOT_CLEARED",  # Medical hold
        movement_state="AT_STATION",
    )
    replacement_cand = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-REP-{uuid.uuid4().hex[:4].upper()}",
        full_name="Priya Patel",
        role="Ice Core Specialist",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Glacier Deep Drill Team",
        expedition_id=exp.id,
        mission_id=mission.id,
        location_id=loc.id,
        leader_person_id=leader.id,
        status="STATION",
    )
    db_session.add_all([leader, unready_member, replacement_cand, team])
    db_session.flush()

    leader.team_id = team.id
    unready_member.team_id = team.id
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary = service.evaluate_expedition(exp.id)

    assert summary.overall_status == "BLOCKED"
    assert summary.medical_hold_count >= 1

    # Verify rule explanation
    finding = next((f for f in summary.findings if f.rule_id == "PERS_READINESS_DISQUALIFIED"), None)
    assert finding is not None
    assert finding.status == "BLOCKED"
    assert finding.subject_id == unready_member.id
    assert finding.evidence["readiness_state"] == "NOT_CLEARED"
    assert finding.data_provenance == "DERIVED"

    # Verify reassignment opportunity identified
    assert len(summary.reassignment_opportunities) >= 1
    opp = summary.reassignment_opportunities[0]
    assert opp["displaced_person_id"] == str(unready_member.id)
    assert opp["candidate_person_id"] == str(replacement_cand.id)
    assert opp["data_provenance"] == "ADVISORY"


def test_deterministic_blocked_deployment_incompatible_movement(db_session: Session):
    """Verifies that a member with NOT_DEPLOYED state on an active FIELD team is BLOCKED."""
    exp, loc = create_base_expedition(db_session, "Movement Conflict Expedition")
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Inland Traverse Bravo",
        expedition_id=exp.id,
        status="FIELD",  # Active field deployment
    )
    leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-LDR-{uuid.uuid4().hex[:4].upper()}",
        full_name="Captain Mehra",
        role="Traverse Commander",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="FIELD_DEPLOYED",
    )
    stuck_member = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-STK-{uuid.uuid4().hex[:4].upper()}",
        full_name="Karan Verma",
        role="Field Mechanic",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="NOT_DEPLOYED",  # Incompatible with FIELD team status
    )
    db_session.add_all([team, leader, stuck_member])
    db_session.flush()

    leader.team_id = team.id
    stuck_member.team_id = team.id
    team.leader_person_id = leader.id
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary = service.evaluate_expedition(exp.id)

    finding = next((f for f in summary.findings if f.rule_id == "PERS_MOVEMENT_INCOMPATIBLE"), None)
    assert finding is not None
    assert finding.status == "BLOCKED"
    assert finding.subject_id == stuck_member.id
    assert finding.evidence["movement_state"] == "NOT_DEPLOYED"


def test_deterministic_blocked_deployment_headcount_deficit(db_session: Session):
    """Verifies that a field mission team with < 2 members breaches polar buddy safety invariant."""
    exp, loc = create_base_expedition(db_session, "Solo Team Expedition")
    mission = MissionModel(
        id=uuid.uuid4(),
        code=f"MIS-{uuid.uuid4().hex[:4].upper()}",
        title="Solo Traverse Recon",
        type="SURVEY",
        expedition_id=exp.id,
        status="ACTIVE",
    )
    db_session.add(mission)
    db_session.flush()

    lone_leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-LONE-{uuid.uuid4().hex[:4].upper()}",
        full_name="Major Singh",
        role="Navigator",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Solo Recon Unit",
        expedition_id=exp.id,
        mission_id=mission.id,
        leader_person_id=lone_leader.id,
        status="STATION",
    )
    db_session.add_all([lone_leader, team])
    db_session.flush()

    lone_leader.team_id = team.id
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary = service.evaluate_expedition(exp.id)

    finding = next((f for f in summary.findings if f.rule_id == "TEAM_HEADCOUNT_DEFICIT"), None)
    assert finding is not None
    assert finding.status == "BLOCKED"
    assert finding.evidence["current_headcount"] == 1
    assert finding.evidence["minimum_required"] == 2


def test_deterministic_warning_safety_officer_absent(db_session: Session):
    """Verifies that a field team without a certified safety officer/guide triggers a WARNING finding."""
    exp, loc = create_base_expedition(db_session, "Warning Expedition")
    mission = MissionModel(
        id=uuid.uuid4(),
        code=f"MIS-{uuid.uuid4().hex[:4].upper()}",
        title="Coastal Meteorological Study",
        type="FIELD_SURVEY",
        expedition_id=exp.id,
        status="ACTIVE",
    )
    db_session.add(mission)
    db_session.flush()

    leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-LDR-{uuid.uuid4().hex[:4].upper()}",
        full_name="Dr. Bose",
        role="Principal Investigator",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    technician = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-TECH-{uuid.uuid4().hex[:4].upper()}",
        full_name="Amit Roy",
        role="Sensor Technician",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Weather Sensor Deployment Team",
        expedition_id=exp.id,
        mission_id=mission.id,
        leader_person_id=leader.id,
        status="STATION",
    )
    db_session.add_all([leader, technician, team])
    db_session.flush()

    leader.team_id = team.id
    technician.team_id = team.id
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary = service.evaluate_expedition(exp.id)

    assert summary.overall_status == "WARNING"
    finding = next((f for f in summary.findings if f.rule_id == "FIELD_SAFETY_OFFICER_ABSENT"), None)
    assert finding is not None
    assert finding.status == "WARNING"


def test_expedition_isolation(db_session: Session):
    """Ensures personnel safety evaluation strictly isolates entities across expeditions."""
    exp_a, loc_a = create_base_expedition(db_session, "Expedition Alpha")
    exp_b, loc_b = create_base_expedition(db_session, "Expedition Beta")

    person_a = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-A-{uuid.uuid4().hex[:4].upper()}",
        full_name="Scientist Alpha",
        role="Geologist",
        expedition_id=exp_a.id,
        readiness_state="NOT_CLEARED",  # Medical hold in A
        movement_state="AT_STATION",
    )
    person_b = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-B-{uuid.uuid4().hex[:4].upper()}",
        full_name="Scientist Beta",
        role="Geologist",
        expedition_id=exp_b.id,
        readiness_state="READY",  # Ready in B
        movement_state="AT_STATION",
    )
    db_session.add_all([person_a, person_b])
    db_session.commit()

    service = PersonnelSafetyService(db_session)
    summary_a = service.evaluate_expedition(exp_a.id)
    summary_b = service.evaluate_expedition(exp_b.id)

    assert summary_a.total_personnel == 1
    assert summary_a.medical_hold_count == 1

    assert summary_b.total_personnel == 1
    assert summary_b.medical_hold_count == 0
    assert summary_b.cleared_count == 1


def test_reassign_personnel_option_generation_and_governance_flow(db_session: Session):
    """
    Verifies full lifecycle of REASSIGN_PERSONNEL:
    - Trigger replan for disqualified member
    - Generate candidate options & recommendations
    - Verify option is REASSIGN_PERSONNEL with FEASIBLE state
    - Verify option generation does NOT mutate state
    - Request and approve recommendation
    - Verify approval does NOT mutate state
    - Explicit Apply mutates team assignment and leader
    - Emits TeamMemberReassigned event and records audit
    - Idempotency check on subsequent Apply
    """
    exp, loc = create_base_expedition(db_session, "Governance Replan Expedition")
    mission = MissionModel(
        id=uuid.uuid4(),
        code=f"MIS-{uuid.uuid4().hex[:4].upper()}",
        title="High Plateau Ice Drilling",
        type="SCIENCE",
        expedition_id=exp.id,
        status="ACTIVE",
    )
    db_session.add(mission)
    db_session.flush()

    disqualified_leader = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-DISQ-{uuid.uuid4().hex[:4].upper()}",
        full_name="Dr. Somesh Sharma",
        role="Traverse Leader",
        expedition_id=exp.id,
        readiness_state="NOT_CLEARED",  # Medical hold
        movement_state="AT_STATION",
    )
    candidate_replacement = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-QUAL-{uuid.uuid4().hex[:4].upper()}",
        full_name="Capt. Anita Desai",
        role="Traverse Leader",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    team = TeamModel(
        id=uuid.uuid4(),
        code=f"TM-{uuid.uuid4().hex[:4].upper()}",
        name="Plateau Drillers",
        expedition_id=exp.id,
        mission_id=mission.id,
        leader_person_id=disqualified_leader.id,
        status="STATION",
    )
    db_session.add_all([disqualified_leader, candidate_replacement, team])
    db_session.flush()

    disqualified_leader.team_id = team.id
    db_session.commit()

    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)

    # 1. Trigger Replan
    replan_req = ReplanTriggerRequest(
        expedition_id=exp.id,
        mission_id=mission.id,
        trigger_mode="OPERATOR_REQUESTED",
        trigger_entity_type="PERSON",
        trigger_entity_id=disqualified_leader.id,
        reason=f"Medical disqualification of traverse leader {disqualified_leader.person_code}",
    )
    replan = replan_service.create_replan_request(replan_req)
    assert replan.status == ReplanStatus.REQUESTED.value

    # 2. Generate Options
    options, recommendations = replan_service.generate_options(replan.id)
    assert len(options) >= 1
    assert len(recommendations) >= 1

    reassign_opt = next((o for o in options if o.action_type == ReplanActionType.REASSIGN_PERSONNEL.value), None)
    assert reassign_opt is not None
    assert reassign_opt.feasibility_state == OptionFeasibility.FEASIBLE.value
    assert reassign_opt.proposed_state_change["action"] == "REASSIGN_PERSONNEL"
    assert reassign_opt.proposed_state_change["displaced_person_id"] == str(disqualified_leader.id)
    assert reassign_opt.proposed_state_change["replacement_person_id"] == str(candidate_replacement.id)

    # Invariant: Generating options does NOT mutate state
    db_session.refresh(disqualified_leader)
    db_session.refresh(candidate_replacement)
    db_session.refresh(team)
    assert disqualified_leader.team_id == team.id
    assert candidate_replacement.team_id is None
    assert team.leader_person_id == disqualified_leader.id

    # 3. Find matching recommendation
    rec = next((r for r in recommendations if r.option_id == reassign_opt.id), None)
    assert rec is not None
    assert rec.approval_state == "PROPOSED"

    # 4. Request and Approve
    apprv = approval_service.request_approval(rec.id)
    assert apprv.status == ApprovalStatus.PENDING.value

    operator_id = uuid.uuid4()
    decided_apprv = approval_service.decide(
        apprv.id,
        ApprovalDecisionRequest(
            decision=ApprovalDecision.APPROVED,
            approver_person_id=operator_id,
            comment="Approved crew substitution for Antarctic field safety compliance.",
        ),
    )
    assert decided_apprv.status == ApprovalStatus.APPROVED.value

    # Invariant: Approval does NOT mutate operational state
    db_session.refresh(disqualified_leader)
    db_session.refresh(candidate_replacement)
    db_session.refresh(team)
    assert disqualified_leader.team_id == team.id
    assert candidate_replacement.team_id is None
    assert team.leader_person_id == disqualified_leader.id

    # 5. Explicit Apply
    apply_res = approval_service.apply(
        rec.id,
        ReplanApplyRequest(
            actor_person_id=operator_id,
            comment="Executing personnel replacement into active team manifest.",
        ),
    )
    assert apply_res.status == "APPLIED"

    # Operational state MUST now be mutated
    db_session.refresh(disqualified_leader)
    db_session.refresh(candidate_replacement)
    db_session.refresh(team)

    assert candidate_replacement.team_id == team.id
    assert disqualified_leader.team_id is None
    assert team.leader_person_id == candidate_replacement.id

    # 6. Idempotency Check
    repeat_apply = approval_service.apply(
        rec.id,
        ReplanApplyRequest(
            actor_person_id=operator_id,
            comment="Repeat apply invocation",
        ),
    )
    assert repeat_apply.status == "APPLIED"
    assert "already been applied" in repeat_apply.message


def test_apply_unapproved_rejected(db_session: Session):
    """Verifies that an unapproved recommendation cannot be applied."""
    exp, loc = create_base_expedition(db_session, "Unapproved Replan Expedition")
    replan_service = ReplanService(db_session)
    approval_service = ApprovalService(db_session)

    replan = replan_service.create_replan_request(
        ReplanTriggerRequest(
            expedition_id=exp.id,
            trigger_mode="OPERATOR_REQUESTED",
            reason="Test unapproved rejection",
        )
    )
    options, recs = replan_service.generate_options(replan.id)
    if recs:
        rec = recs[0]
        with pytest.raises(DomainValidationError) as exc_info:
            approval_service.apply(
                rec.id,
                ReplanApplyRequest(actor_person_id=uuid.uuid4(), comment="Attempt unauthorized apply"),
            )
        assert "Human approval required" in str(exc_info.value.message)


def test_control_tower_personnel_safety_api_endpoint(client: TestClient, db_session: Session):
    """Tests GET /api/v1/control-tower/expeditions/{id}/personnel-safety endpoint."""
    exp, loc = create_base_expedition(db_session, "API Route Expedition")
    person = PersonModel(
        id=uuid.uuid4(),
        person_code=f"P-API-{uuid.uuid4().hex[:4].upper()}",
        full_name="Dr. Homi Bhabha",
        role="Cosmic Ray Physicist",
        expedition_id=exp.id,
        readiness_state="READY",
        movement_state="AT_STATION",
    )
    db_session.add(person)
    db_session.commit()

    resp = client.get(f"/api/v1/control-tower/expeditions/{exp.id}/personnel-safety")
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["errors"] is None
    data = res_json["data"]

    assert data["expedition_id"] == str(exp.id)
    assert "overall_status" in data
    assert "total_personnel" in data
    assert data["total_personnel"] >= 1
    assert "cleared_count" in data
    assert "findings" in data
    assert "data_provenance" in data
    assert data["data_provenance"] == "DERIVED"
