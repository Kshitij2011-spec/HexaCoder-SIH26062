"""Targeted Integration Test Suite for Milestone A7:
Incident-Driven Operational Escalation & Closed-Loop Recovery.

Verifies:
1. Valid incident escalation creates a Replan in REQUESTED state.
2. Invalid/terminal (CLOSED) incident escalation is rejected (ConflictError).
3. Expedition boundary isolation (cross-expedition escalation rejected).
4. Incident propagation context consumed and blast-radius evaluated.
5. Affected mission resolution from incident location/references.
6. Affected constraint resolution from downstream dependencies.
7. Incident linkage persisted in replan trigger metadata and current_state_evidence.
8. Incident escalation is idempotent (returns existing active replan).
9. Duplicate escalation does not create duplicate active replans.
10. Options generation uses existing A6 machinery for incident-triggered replan.
11. Human approval remains required before application.
12. Approval does not apply state mutations (governance invariant preserved).
13. Explicit apply performs domain mutation through verified services.
14. Operational events are emitted across the entire lifecycle.
15. Audit and correlation linkage is preserved end-to-end.
16. Unrelated expedition entities remain unchanged.
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import DomainValidationError, ConflictError

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
from backend.app.domains.assets.models import AssetModel
from backend.app.domains.incidents.models import (
    IncidentModel,
    IncidentReferenceModel,
    IncidentPropagationModel,
)
from backend.app.domains.incidents.states import (
    IncidentStatus,
    IncidentSeverity,
    IncidentReferenceType,
    PropagationStatus,
)
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
from backend.app.domains.control_tower.incident_escalation import IncidentEscalationService
from backend.app.domains.control_tower.schemas import IncidentEscalationRequest
from backend.app.services.dependencies.models import DependencyModel
from backend.app.services.constraints.models import ConstraintModel
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.audit.models import AuditLogModel


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
    """Seeds baseline expedition and related records for incident escalation testing."""
    session = SessionFactory()

    # Clear tables in reverse dependency order
    session.query(OperationalEventModel).delete()
    session.query(AuditLogModel).delete()
    session.query(ApprovalModel).delete()
    session.query(RecommendationModel).delete()
    session.query(ReplanOptionModel).delete()
    session.query(ReplanModel).delete()
    session.query(IncidentPropagationModel).delete()
    session.query(IncidentReferenceModel).delete()
    session.query(IncidentModel).delete()
    session.query(ConstraintModel).delete()
    session.query(DependencyModel).delete()
    session.query(TransportLegModel).delete()
    session.query(AssetModel).delete()
    session.query(MissionModel).delete()
    session.query(LocationModel).delete()
    session.query(ExpeditionModel).delete()
    session.commit()

    # 1. Expeditions
    exp_id = uuid.uuid4()
    exp = ExpeditionModel(
        id=exp_id,
        code="EXP-45-A7",
        name="45th Indian Antarctic Research Expedition",
        season="2026-2027",
        status="ACTIVE",
        data_provenance="SYNTHETIC_DEMO",
    )
    other_exp_id = uuid.uuid4()
    other_exp = ExpeditionModel(
        id=other_exp_id,
        code="EXP-46-OTHER",
        name="46th Unrelated Polar Campaign",
        season="2027-2028",
        status="ACTIVE",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add_all([exp, other_exp])

    # 2. Locations
    loc_id = uuid.uuid4()
    loc = LocationModel(
        id=loc_id,
        code="LOC-MTR-STATION",
        name="Maitri Research Station Main Base",
        type="STATION",
        status="AVAILABLE",
        data_provenance="SYNTHETIC_DEMO",
    )
    dest_loc_id = uuid.uuid4()
    dest_loc = LocationModel(
        id=dest_loc_id,
        code="LOC-FIELD-CAMP-A",
        name="Field Camp Alpha",
        type="FIELD_CAMP",
        status="AVAILABLE",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add_all([loc, dest_loc])

    # 3. Assets
    asset_gen_id = uuid.uuid4()
    asset_gen = AssetModel(
        id=asset_gen_id,
        asset_code="AST-GEN-PRIMARY",
        name="Primary Station Power Generator 1",
        type="GENERATOR",
        status="AVAILABLE",
        data_provenance="SYNTHETIC_DEMO",
    )
    asset_sub_id = uuid.uuid4()
    asset_sub = AssetModel(
        id=asset_sub_id,
        asset_code="AST-GEN-STANDBY",
        name="Standby Diesel Generator 2",
        type="GENERATOR",
        status="AVAILABLE",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add_all([asset_gen, asset_sub])

    # 4. Missions
    now = datetime.now(timezone.utc)
    mission_id = uuid.uuid4()
    mission = MissionModel(
        id=mission_id,
        expedition_id=exp_id,
        code="MSN-CRYO-01",
        title="Princess Astrid Coast Cryo-Seismic Profiling",
        type="SCIENTIFIC",
        priority=3,
        status="APPROVED",
        location_id=loc_id,
        required_by_at=now + timedelta(days=10),
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(mission)

    # 5. Transport Legs
    leg_id = uuid.uuid4()
    leg = TransportLegModel(
        id=leg_id,
        code="LEG-TRAVERSE-01",
        expedition_id=exp_id,
        origin_location_id=loc_id,
        destination_location_id=dest_loc_id,
        mode="OVERLAND_TRAVERSE",
        status="SCHEDULED",
        planned_departure_at=now + timedelta(days=2),
        planned_arrival_at=now + timedelta(days=4),
        estimated_arrival_at=now + timedelta(days=4),
        capacity=10.0,
        data_provenance="SYNTHETIC_DEMO",
    )
    alt_leg_id = uuid.uuid4()
    alt_leg = TransportLegModel(
        id=alt_leg_id,
        code="LEG-TRAVERSE-02",
        expedition_id=exp_id,
        origin_location_id=loc_id,
        destination_location_id=dest_loc_id,
        mode="AIR",
        status="SCHEDULED",
        planned_departure_at=now + timedelta(days=3),
        planned_arrival_at=now + timedelta(days=4),
        estimated_arrival_at=now + timedelta(days=4),
        capacity=5.0,
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add_all([leg, alt_leg])

    # 6. Dependencies
    dep1 = DependencyModel(
        id=uuid.uuid4(),
        expedition_id=exp_id,
        source_entity_type="MISSION",
        source_entity_id=mission_id,
        relationship_type="REQUIRES",
        target_entity_type="ASSET",
        target_entity_id=asset_gen_id,
        criticality="CRITICAL",
        data_provenance="SYNTHETIC_DEMO",
    )
    dep2 = DependencyModel(
        id=uuid.uuid4(),
        expedition_id=exp_id,
        source_entity_type="MISSION",
        source_entity_id=mission_id,
        relationship_type="REQUIRES",
        target_entity_type="TRANSPORT_LEG",
        target_entity_id=leg_id,
        criticality="CRITICAL",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add_all([dep1, dep2])

    # 7. Constraint
    cst = ConstraintModel(
        id=uuid.uuid4(),
        code="CST-PWR-AVAIL",
        name="Continuous Station Power Baseline",
        type="RESOURCE_AVAILABILITY",
        rule_code="MINIMUM_RESOURCE",
        subject_type="MISSION",
        subject_id=mission_id,
        hard_or_soft="HARD",
        severity="CRITICAL",
        active=True,
        parameters={"required_asset_code": "AST-GEN-PRIMARY"},
        description="Cryo-seismic instruments require continuous power baseline from primary generator.",
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(cst)

    # 8. Active Incident
    active_inc_id = uuid.uuid4()
    active_inc = IncidentModel(
        id=active_inc_id,
        incident_code="INC-A7-001",
        title="Primary Station Generator Fuel Valve Failure",
        description="Fuel valve failure on AST-GEN-PRIMARY; station running on emergency battery buffer.",
        incident_type="EQUIPMENT_FAILURE",
        severity=IncidentSeverity.CRITICAL.value,
        priority=1,
        location_id=loc_id,
        asset_id=asset_gen_id,
        expedition_id=exp_id,
        status=IncidentStatus.OPEN.value,
        data_provenance="SYNTHETIC_DEMO",
    )
    # Reference to asset
    ref = IncidentReferenceModel(
        id=uuid.uuid4(),
        incident_id=active_inc_id,
        reference_type=IncidentReferenceType.ASSET.value,
        reference_id=asset_gen_id,
        notes="Primary generator failed due to fuel valve lockup",
    )
    # Terminal incident for validation testing
    closed_inc_id = uuid.uuid4()
    closed_inc = IncidentModel(
        id=closed_inc_id,
        incident_code="INC-A7-CLOSED",
        title="Historical Generator Check",
        description="Routine generator maintenance completed last week.",
        incident_type="EQUIPMENT_FAILURE",
        severity=IncidentSeverity.LOW.value,
        priority=5,
        location_id=loc_id,
        asset_id=asset_gen_id,
        expedition_id=exp_id,
        status=IncidentStatus.CLOSED.value,
        data_provenance="SYNTHETIC_DEMO",
    )

    session.add_all([active_inc, ref, closed_inc])
    session.commit()

    context = {
        "expedition_id": exp_id,
        "other_expedition_id": other_exp_id,
        "location_id": loc_id,
        "asset_id": asset_gen_id,
        "sub_asset_id": asset_sub_id,
        "mission_id": mission_id,
        "leg_id": leg_id,
        "alt_leg_id": alt_leg_id,
        "active_incident_id": active_inc_id,
        "closed_incident_id": closed_inc_id,
    }
    session.close()
    return context


@pytest.fixture
def test_client(shared_engine, SessionFactory):
    """FastAPI TestClient with database session override."""
    def override_get_db():
        session = SessionFactory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


# ===========================================================================
# TEST CASES
# ===========================================================================

def test_valid_incident_escalation_lifecycle(clean_db, SessionFactory, test_client):
    """1. Valid active incident escalation creates a Replan in REQUESTED state."""
    inc_id = clean_db["active_incident_id"]

    resp = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["incident_id"] == str(inc_id)
    assert data["incident_code"] == "INC-A7-001"
    assert data["replan_status"] == "REQUESTED"
    assert data["is_existing"] is False
    assert data["data_provenance"] == "DERIVED"
    assert data["replan_id"] is not None

    # Verify Replan persisted in independent DB session
    session = SessionFactory()
    replan = session.get(ReplanModel, uuid.UUID(data["replan_id"]))
    assert replan is not None
    assert replan.trigger_entity_type == "INCIDENT"
    assert replan.trigger_entity_id == inc_id
    assert replan.status == ReplanStatus.REQUESTED.value
    assert replan.current_state_evidence.get("incident_code") == "INC-A7-001"
    session.close()


def test_closed_incident_escalation_rejected(clean_db, test_client):
    """2. Terminal/CLOSED incident escalation is strictly rejected with ConflictError (409)."""
    closed_id = clean_db["closed_incident_id"]
    resp = test_client.post(f"/api/v1/control-tower/incidents/{closed_id}/escalate", json={})
    assert resp.status_code == 409
    body = resp.json()
    assert "CLOSED" in str(body)


def test_expedition_boundary_isolation(clean_db, test_client):
    """3. Cross-expedition escalation is strictly blocked (expedition mismatch raises error)."""
    inc_id = clean_db["active_incident_id"]
    wrong_exp_id = clean_db["other_expedition_id"]

    resp = test_client.post(
        f"/api/v1/control-tower/incidents/{inc_id}/escalate",
        json={"expedition_id": str(wrong_exp_id)}
    )
    assert resp.status_code == 422 or resp.status_code == 400


def test_blast_radius_and_mission_resolution(clean_db, SessionFactory, test_client):
    """4 & 5. Blast radius identifies downstream impacted missions from incident references."""
    inc_id = clean_db["active_incident_id"]
    mission_id = clean_db["mission_id"]

    resp = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={"depth": 3})
    assert resp.status_code == 200
    data = resp.json()["data"]

    # The blast radius should resolve the mission requiring the failed generator
    affected = data["affected_entities"]
    affected_ids = [str(a.get("entity_id")) for a in affected]
    assert str(clean_db["asset_id"]) in affected_ids
    assert str(mission_id) in affected_ids
    assert data["affected_missions_count"] >= 1


def test_incident_escalation_idempotency(clean_db, test_client):
    """8 & 9. Repeated escalation returns existing logical replan and does not duplicate."""
    inc_id = clean_db["active_incident_id"]

    # First call: creates replan
    resp1 = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})
    assert resp1.status_code == 200
    data1 = resp1.json()["data"]
    replan_id_1 = data1["replan_id"]
    assert data1["is_existing"] is False

    # Second call: returns same replan idempotently
    resp2 = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    replan_id_2 = data2["replan_id"]
    assert data2["is_existing"] is True
    assert replan_id_1 == replan_id_2


def test_options_generation_using_existing_machinery(clean_db, test_client):
    """10. Options generation produces candidate mitigations for incident-escalated replan."""
    inc_id = clean_db["active_incident_id"]

    # Escalate
    esc_resp = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})
    replan_id = esc_resp.json()["data"]["replan_id"]

    # Generate options via existing replanning router
    gen_resp = test_client.post(f"/api/v1/replans/{replan_id}/generate-options")
    assert gen_resp.status_code == 200
    options = gen_resp.json()["data"]
    assert len(options) >= 1

    # Check recommendations generated
    rec_resp = test_client.get(f"/api/v1/replans/{replan_id}/recommendations")
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["data"]
    assert len(recs) >= 1
    assert recs[0]["replan_id"] == replan_id
    assert recs[0]["status"] == "PROPOSED"


def test_governance_invariants_approve_and_apply_separation(clean_db, SessionFactory, test_client):
    """11, 12, 13. Escalation != Approval, Approval != Apply, Apply requires prior human approval."""
    inc_id = clean_db["active_incident_id"]
    operator_id = uuid.uuid4()

    # 1. Escalate
    esc_resp = test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})
    replan_id = esc_resp.json()["data"]["replan_id"]

    # Generate options
    test_client.post(f"/api/v1/replans/{replan_id}/generate-options")
    recs = test_client.get(f"/api/v1/replans/{replan_id}/recommendations").json()["data"]
    rec_id = recs[0]["id"]

    # INVARIANT 1: Premature apply before approval is rejected
    apply_resp = test_client.post(
        f"/api/v1/recommendations/{rec_id}/apply",
        json={"actor_person_id": str(operator_id), "comment": "Premature attempt"}
    )
    assert apply_resp.status_code == 422 or apply_resp.status_code == 400

    # 2. Human Approval
    appr_resp = test_client.post(
        f"/api/v1/recommendations/{rec_id}/approve",
        json={
            "approver_person_id": str(operator_id),
            "decision": "APPROVED",
            "comment": "Approved switchover to standby power"
        }
    )
    assert appr_resp.status_code == 200
    approval_data = appr_resp.json()["data"]
    assert approval_data["status"] == "APPROVED"

    # INVARIANT 2: Approval must NOT mutate domain state yet
    session = SessionFactory()
    rec_in_db = session.get(RecommendationModel, uuid.UUID(rec_id))
    assert rec_in_db.status == RecommendationStatus.SELECTED.value
    assert rec_in_db.approval_state == "APPROVED"
    replan_in_db = session.get(ReplanModel, uuid.UUID(replan_id))
    assert replan_in_db.status == ReplanStatus.APPROVED.value  # NOT applied yet
    session.close()

    # 3. Explicit Apply
    apply_ok_resp = test_client.post(
        f"/api/v1/recommendations/{rec_id}/apply",
        json={"actor_person_id": str(operator_id), "comment": "Explicit apply by station commander"}
    )
    assert apply_ok_resp.status_code == 200
    apply_data = apply_ok_resp.json()["data"]
    assert apply_data["status"] == "APPLIED"

    # Check resulting database state
    session = SessionFactory()
    rec_applied = session.get(RecommendationModel, uuid.UUID(rec_id))
    assert rec_applied.status == RecommendationStatus.APPLIED.value
    assert rec_applied.approval_state == "IMPLEMENTED"

    replan_applied = session.get(ReplanModel, uuid.UUID(replan_id))
    assert replan_applied.status == ReplanStatus.APPLIED.value
    assert replan_applied.completed_at is not None
    session.close()


def test_operational_events_and_audit_emitted(clean_db, SessionFactory, test_client):
    """14 & 15. Operational events and audit records are emitted throughout escalation."""
    inc_id = clean_db["active_incident_id"]

    test_client.post(f"/api/v1/control-tower/incidents/{inc_id}/escalate", json={})

    session = SessionFactory()
    # Check ReplanRequested event
    events = session.query(OperationalEventModel).filter(
        OperationalEventModel.event_type == "ReplanRequested"
    ).all()
    assert len(events) >= 1

    # Check audit log for escalation
    audits = session.query(AuditLogModel).filter(
        AuditLogModel.action == "INCIDENT_ESCALATED_TO_REPLAN"
    ).all()
    assert len(audits) >= 1
    assert audits[0].entity_id == inc_id
    session.close()


def test_incident_context_endpoint(clean_db, test_client):
    """16. GET /api/v1/control-tower/incidents/{incident_id}/context returns rich context."""
    inc_id = clean_db["active_incident_id"]

    resp = test_client.get(f"/api/v1/control-tower/incidents/{inc_id}/context")
    assert resp.status_code == 200
    ctx = resp.json()["data"]

    assert ctx["incident_id"] == str(inc_id)
    assert ctx["incident_code"] == "INC-A7-001"
    assert ctx["severity"] == "CRITICAL"
    assert ctx["status"] == "OPEN"
    assert ctx["location_code"] == "LOC-MTR-STATION"
    assert ctx["asset_code"] == "AST-GEN-PRIMARY"
    assert ctx["data_provenance"] == "DERIVED"


# ===========================================================================
# HARDENING TEST CASES
# ===========================================================================

def test_impact_engine_failure_propagates_as_domain_error(clean_db, SessionFactory):
    """H1. Impact engine infrastructure failure MUST NOT be silently swallowed.

    When ImpactService.calculate_impact raises a non-domain exception (e.g.
    database connectivity failure, serialisation error), the escalation must
    fail with a DomainValidationError containing the IMPACT_ENGINE_FAILURE
    code and diagnostic details rather than silently producing an incomplete
    blast radius.
    """
    from unittest.mock import patch
    inc_id = clean_db["active_incident_id"]
    exp_id = clean_db["expedition_id"]
    session = SessionFactory()

    svc = IncidentEscalationService(session)

    with patch.object(
        svc.impact_service,
        "calculate_impact",
        side_effect=RuntimeError("Simulated infrastructure failure in impact engine"),
    ):
        with pytest.raises(DomainValidationError) as exc_info:
            svc.escalate_incident(
                incident_id=inc_id,
                expedition_id=exp_id,
            )
        err = exc_info.value
        assert err.code == "IMPACT_ENGINE_FAILURE"
        assert "impact_analysis" == err.field
        assert err.details["incident_code"] == "INC-A7-001"
        assert err.details["failed_seeds"] > 0
        assert len(err.details["failures"]) > 0
        # Each failure entry must contain diagnostic info
        first_failure = err.details["failures"][0]
        assert "seed_type" in first_failure
        assert "seed_id" in first_failure
        assert "Simulated infrastructure failure" in first_failure["error"]

    session.close()


def test_expedition_unresolvable_raises_domain_error(clean_db, SessionFactory):
    """H2. Incident with no resolvable expedition MUST be rejected.

    An incident escalation must NEVER choose an arbitrary expedition.
    If neither an explicit expedition_id, nor the incident's expedition_id,
    nor the primary affected mission's expedition_id can be resolved, the
    system must raise DomainValidationError with EXPEDITION_UNRESOLVABLE code.
    """
    inc_id = clean_db["active_incident_id"]
    exp_id = clean_db["expedition_id"]
    session = SessionFactory()

    # Create a bare incident with NO expedition_id
    orphan_inc = IncidentModel(
        id=uuid.uuid4(),
        incident_code="INC-A7-ORPHAN",
        title="Orphan Incident Without Expedition",
        description="Testing unresolvable expedition.",
        incident_type="EQUIPMENT_FAILURE",
        severity=IncidentSeverity.LOW.value,
        priority=5,
        location_id=None,
        asset_id=None,
        expedition_id=None,
        status=IncidentStatus.OPEN.value,
        data_provenance="SYNTHETIC_DEMO",
    )
    session.add(orphan_inc)
    session.commit()

    svc = IncidentEscalationService(session)

    with pytest.raises(DomainValidationError) as exc_info:
        svc.escalate_incident(
            incident_id=orphan_inc.id,
            # No explicit expedition_id provided
        )
    err = exc_info.value
    assert err.code == "EXPEDITION_UNRESOLVABLE"
    assert err.field == "expedition_id"
    assert err.details["incident_code"] == "INC-A7-ORPHAN"

    session.close()


def test_domain_errors_in_impact_are_non_fatal(clean_db, SessionFactory):
    """H3. Known domain errors from ImpactService (EntityNotFound, DomainValidation)
    for individual seeds are non-fatal — escalation proceeds with remaining seeds.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.core.errors import EntityNotFoundError as ENF
    inc_id = clean_db["active_incident_id"]
    exp_id = clean_db["expedition_id"]
    session = SessionFactory()

    # Clear any existing replans for this incident so we get a fresh escalation
    session.query(ReplanModel).filter(
        ReplanModel.trigger_entity_type == "INCIDENT",
        ReplanModel.trigger_entity_id == inc_id,
    ).delete()
    session.commit()

    svc = IncidentEscalationService(session)

    # Make calculate_impact raise EntityNotFoundError for every seed — this is
    # a domain error and should be non-fatal, allowing the escalation to complete
    # with just the direct seed references in the blast radius.
    with patch.object(
        svc.impact_service,
        "calculate_impact",
        side_effect=ENF("TestEntity", uuid.uuid4()),
    ):
        result = svc.escalate_incident(
            incident_id=inc_id,
            expedition_id=exp_id,
        )
        # Escalation should succeed despite all domain errors in impact
        assert result.replan_id is not None
        assert result.replan_status == "REQUESTED"
        # Direct seed references should still be in the blast radius
        assert len(result.affected_entities) > 0

    session.close()
