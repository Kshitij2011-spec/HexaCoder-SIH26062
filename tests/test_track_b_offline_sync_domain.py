"""
Comprehensive Test Suite for Person B / Track B — Milestone B5: Offline Queue / Sync Domain

Tests:
- Offline operation enqueue (single, idempotent)
- Batch enqueue with mixed outcomes (ENQUEUED, DUPLICATE)
- Queue listing and filtering
- Get operation by ID and by client operation_id
- Status transitions: PENDING → APPLIED, PENDING → FAILED, PENDING → REJECTED
- FAILED → PENDING (retry), FAILED → REJECTED
- Terminal state protection (APPLIED/REJECTED cannot be transitioned)
- Invalid transition rejection
- Queue summary counts
- Operational event journaling (every state change emits an event)
- Attributable audit logging
- Backward compatibility with all B1–B4 domains
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import (
    EntityNotFoundError,
    InvalidStateTransitionError,
)

# Register ALL models for SQLite in-memory schema creation
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

from backend.app.domains.sync.states import (
    OfflineOperationStatus,
    TERMINAL_STATUSES,
    OFFLINE_OP_TRANSITIONS,
)
from backend.app.domains.sync.schemas import (
    OfflineOperationEnqueue,
    SyncBatchRequest,
    OperationApplyRequest,
)
from backend.app.domains.sync.service import SyncService
from backend.app.platform.events.models import OperationalEventModel


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def client():
    """Isolated in-memory SQLite test database fixture for B5 Sync tests."""
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
    """Yields an active database session for direct service-level tests."""
    override = app.dependency_overrides[get_db]
    session_gen = override()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()


def _make_enqueue_payload(
    operation_id: uuid.UUID = None,
    entity_type: str = "INVENTORY_ITEM",
    operation_type: str = "UPDATE",
) -> dict:
    return {
        "operation_id": str(operation_id or uuid.uuid4()),
        "entity_type": entity_type,
        "operation_type": operation_type,
        "payload": {"field": "quantity", "value": 42},
    }


# ============================================================
# 1. STATE MACHINE UNIT TESTS
# ============================================================

class TestOfflineSyncStateMachine:
    """Deterministic state machine contract tests — no DB required."""

    def test_pending_can_transition_to_applied(self):
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.PENDING]]
        assert OfflineOperationStatus.APPLIED in allowed

    def test_pending_can_transition_to_failed(self):
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.PENDING]]
        assert OfflineOperationStatus.FAILED in allowed

    def test_pending_can_transition_to_rejected(self):
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.PENDING]]
        assert OfflineOperationStatus.REJECTED in allowed

    def test_failed_can_retry_to_pending(self):
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.FAILED]]
        assert OfflineOperationStatus.PENDING in allowed

    def test_failed_can_be_rejected(self):
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.FAILED]]
        assert OfflineOperationStatus.REJECTED in allowed

    def test_applied_is_terminal(self):
        assert OfflineOperationStatus.APPLIED in TERMINAL_STATUSES
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.APPLIED]]
        assert allowed == []

    def test_rejected_is_terminal(self):
        assert OfflineOperationStatus.REJECTED in TERMINAL_STATUSES
        allowed = [s.value for s in OFFLINE_OP_TRANSITIONS[OfflineOperationStatus.REJECTED]]
        assert allowed == []


# ============================================================
# 2. ENQUEUE — SINGLE (idempotency)
# ============================================================

class TestEnqueueSingle:
    def test_enqueue_creates_operation_with_pending_status(self, client):
        """Enqueue creates a new PENDING operation."""
        payload = _make_enqueue_payload()
        r = client.post("/api/v1/sync", json=payload)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["status"] == "PENDING"
        assert data["entity_type"] == "INVENTORY_ITEM"
        assert data["operation_type"] == "UPDATE"
        assert data["created"] is True

    def test_enqueue_idempotent_same_operation_id(self, client):
        """Re-submitting the same operation_id returns the existing record."""
        op_id = str(uuid.uuid4())
        payload = _make_enqueue_payload(operation_id=uuid.UUID(op_id))
        r1 = client.post("/api/v1/sync", json=payload)
        assert r1.status_code == 201
        assert r1.json()["data"]["created"] is True

        r2 = client.post("/api/v1/sync", json=payload)
        assert r2.status_code == 201  # still 201 (envelope does not distinguish)
        d2 = r2.json()["data"]
        assert d2["created"] is False
        assert d2["operation_id"] == op_id

    def test_enqueue_stores_payload(self, client):
        """Custom payload is persisted intact."""
        op_id = str(uuid.uuid4())
        payload = {
            "operation_id": op_id,
            "entity_type": "ASSET",
            "operation_type": "STATE_TRANSITION",
            "payload": {"from": "AVAILABLE", "to": "IN_USE", "asset_id": str(uuid.uuid4())},
        }
        r = client.post("/api/v1/sync", json=payload)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["payload"]["from"] == "AVAILABLE"
        assert data["entity_type"] == "ASSET"


# ============================================================
# 3. BATCH ENQUEUE
# ============================================================

class TestBatchEnqueue:
    def test_batch_enqueue_multiple_operations(self, client):
        """Batch enqueue returns per-operation ENQUEUED outcomes."""
        ops = [_make_enqueue_payload() for _ in range(3)]
        r = client.post("/api/v1/sync/batch", json={"operations": ops})
        assert r.status_code == 202
        data = r.json()["data"]
        assert data["enqueued"] == 3
        assert data["skipped_duplicate"] == 0
        assert data["failed"] == 0
        assert len(data["results"]) == 3
        for result in data["results"]:
            assert result["outcome"] == "ENQUEUED"

    def test_batch_enqueue_detects_duplicates(self, client):
        """Batch enqueue handles mixed new + duplicate operations."""
        op_id = str(uuid.uuid4())
        # Enqueue once first
        client.post("/api/v1/sync", json=_make_enqueue_payload(operation_id=uuid.UUID(op_id)))

        # Batch with one duplicate and one new
        ops = [
            _make_enqueue_payload(operation_id=uuid.UUID(op_id)),  # duplicate
            _make_enqueue_payload(),  # new
        ]
        r = client.post("/api/v1/sync/batch", json={"operations": ops})
        assert r.status_code == 202
        data = r.json()["data"]
        assert data["enqueued"] == 1
        assert data["skipped_duplicate"] == 1
        outcomes = {res["outcome"] for res in data["results"]}
        assert "DUPLICATE" in outcomes
        assert "ENQUEUED" in outcomes


# ============================================================
# 4. LIST AND INTROSPECTION
# ============================================================

class TestListAndIntrospection:
    def test_list_operations_returns_200(self, client):
        r = client.get("/api/v1/sync")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_list_filter_by_status_pending(self, client):
        r = client.get("/api/v1/sync?status=PENDING")
        assert r.status_code == 200
        for op in r.json()["data"]:
            assert op["status"] == "PENDING"

    def test_list_filter_by_entity_type(self, client):
        # Enqueue one INCIDENT type
        payload = _make_enqueue_payload(entity_type="INCIDENT")
        client.post("/api/v1/sync", json=payload)

        r = client.get("/api/v1/sync?entity_type=INCIDENT")
        assert r.status_code == 200
        for op in r.json()["data"]:
            assert op["entity_type"] == "INCIDENT"

    def test_get_by_id(self, client):
        """GET /sync/{id} returns the correct operation."""
        payload = _make_enqueue_payload()
        created = client.post("/api/v1/sync", json=payload).json()["data"]
        r = client.get(f"/api/v1/sync/{created['id']}")
        assert r.status_code == 200
        assert r.json()["data"]["id"] == created["id"]

    def test_get_by_id_not_found(self, client):
        r = client.get(f"/api/v1/sync/{uuid.uuid4()}")
        assert r.status_code == 200  # envelope always 200
        assert r.json()["errors"] is not None
        assert "NOT_FOUND" in r.json()["errors"][0]["code"]

    def test_get_by_operation_id(self, client):
        """GET /sync/by-operation-id/{operation_id} finds by client key."""
        op_id = uuid.uuid4()
        payload = _make_enqueue_payload(operation_id=op_id)
        client.post("/api/v1/sync", json=payload)
        r = client.get(f"/api/v1/sync/by-operation-id/{op_id}")
        assert r.status_code == 200
        assert r.json()["data"]["operation_id"] == str(op_id)

    def test_queue_summary(self, client):
        """GET /sync/summary returns structured counts."""
        r = client.get("/api/v1/sync/summary")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "pending" in data
        assert "applied" in data
        assert "failed" in data
        assert "rejected" in data
        assert "total" in data
        assert data["total"] >= 0


# ============================================================
# 5. STATUS TRANSITIONS — APPLY / FAIL / REJECT
# ============================================================

class TestStatusTransitions:
    def _enqueue_one(self, client) -> dict:
        payload = _make_enqueue_payload()
        r = client.post("/api/v1/sync", json=payload)
        assert r.status_code == 201
        return r.json()["data"]

    def test_pending_to_applied(self, client):
        op = self._enqueue_one(client)
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "APPLIED"},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "APPLIED"
        assert data["applied_at"] is not None

    def test_pending_to_failed(self, client):
        op = self._enqueue_one(client)
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "FAILED", "failure_reason": "Network timeout during replay."},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "FAILED"
        assert data["retry_count"] == 1
        assert data["failure_reason"] == "Network timeout during replay."

    def test_pending_to_rejected(self, client):
        op = self._enqueue_one(client)
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "REJECTED", "failure_reason": "Payload schema invalid for entity type."},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "REJECTED"

    def test_applied_is_terminal_cannot_transition(self, client):
        """APPLIED → anything must be rejected."""
        op = self._enqueue_one(client)
        # Apply it first
        client.patch(f"/api/v1/sync/{op['id']}/apply", json={"status": "APPLIED"})
        # Attempt further transition
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "PENDING", "failure_reason": "retry"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["errors"] is not None
        assert "STATE_TRANSITION_INVALID" in body["errors"][0]["code"]

    def test_rejected_is_terminal_cannot_transition(self, client):
        """REJECTED → anything must be rejected."""
        op = self._enqueue_one(client)
        client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "REJECTED", "failure_reason": "invalid"},
        )
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "APPLIED"},
        )
        assert r.status_code == 200
        assert r.json()["errors"] is not None

    def test_failure_reason_required_for_failed(self, client):
        """Schema validator must reject FAILED without failure_reason."""
        op = self._enqueue_one(client)
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "FAILED"},  # missing failure_reason
        )
        # FastAPI returns 422 for Pydantic validation errors
        assert r.status_code == 422

    def test_failure_reason_required_for_rejected(self, client):
        """Schema validator must reject REJECTED without failure_reason."""
        op = self._enqueue_one(client)
        r = client.patch(
            f"/api/v1/sync/{op['id']}/apply",
            json={"status": "REJECTED"},  # missing failure_reason
        )
        assert r.status_code == 422


# ============================================================
# 6. OPERATIONAL EVENTS AND AUDIT — SERVICE LEVEL
# ============================================================

class TestOperationalEventsAndAudit:
    def test_enqueue_emits_operational_event(self, db_session):
        """Enqueueing an operation must emit a OFFLINE_OP_QUEUED event."""
        svc = SyncService(db_session)
        data = OfflineOperationEnqueue(
            operation_id=uuid.uuid4(),
            entity_type="ASSET",
            operation_type="CREATE",
            payload={"asset_code": "AS-TEST-001"},
        )
        op, created = svc.enqueue(data)
        assert created is True

        events = db_session.execute(
            select(OperationalEventModel).where(
                OperationalEventModel.entity_id == op.id,
                OperationalEventModel.event_type == "OFFLINE_OP_QUEUED",
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].new_state == "PENDING"

    def test_apply_emits_operational_event(self, db_session):
        """Applying an operation must emit an OFFLINE_OP_APPLIED event."""
        svc = SyncService(db_session)
        data = OfflineOperationEnqueue(
            operation_id=uuid.uuid4(),
            entity_type="INVENTORY_ITEM",
            operation_type="UPDATE",
            payload={"quantity": 10},
        )
        op, _ = svc.enqueue(data)
        apply_req = OperationApplyRequest(status="APPLIED")
        applied = svc.apply_operation(op.id, apply_req)
        assert applied.status == "APPLIED"

        events = db_session.execute(
            select(OperationalEventModel).where(
                OperationalEventModel.entity_id == op.id,
                OperationalEventModel.event_type == "OFFLINE_OP_APPLIED",
            )
        ).scalars().all()
        assert len(events) >= 1
        assert events[0].previous_state == "PENDING"
        assert events[0].new_state == "APPLIED"

    def test_invalid_transition_raises_error(self, db_session):
        """Transitioning APPLIED operation must raise InvalidStateTransitionError."""
        svc = SyncService(db_session)
        data = OfflineOperationEnqueue(
            operation_id=uuid.uuid4(),
            entity_type="INCIDENT",
            operation_type="STATE_TRANSITION",
            payload={},
        )
        op, _ = svc.enqueue(data)
        svc.apply_operation(op.id, OperationApplyRequest(status="APPLIED"))

        with pytest.raises(InvalidStateTransitionError):
            svc.apply_operation(op.id, OperationApplyRequest(status="APPLIED"))

    def test_get_operation_not_found_raises(self, db_session):
        """Getting a non-existent operation raises EntityNotFoundError."""
        svc = SyncService(db_session)
        with pytest.raises(EntityNotFoundError):
            svc.get_operation(uuid.uuid4())

    def test_queue_summary_counts_are_accurate(self, db_session):
        """Summary counts must accurately reflect enqueued/applied operations."""
        svc = SyncService(db_session)
        # Enqueue 2 and apply 1
        op1_data = OfflineOperationEnqueue(
            operation_id=uuid.uuid4(),
            entity_type="CARGO",
            operation_type="UPDATE",
            payload={},
        )
        op2_data = OfflineOperationEnqueue(
            operation_id=uuid.uuid4(),
            entity_type="CARGO",
            operation_type="UPDATE",
            payload={},
        )
        op1, _ = svc.enqueue(op1_data)
        svc.enqueue(op2_data)
        svc.apply_operation(op1.id, OperationApplyRequest(status="APPLIED"))

        summary = svc.get_queue_summary()
        # At least the ones we created are accounted for
        assert summary.applied >= 1
        assert summary.total >= 2


# ============================================================
# 7. BACKWARD COMPATIBILITY — B1–B4 DOMAINS
# ============================================================

class TestBackwardCompatibility:
    def test_locations_endpoint_still_works(self, client):
        r = client.get("/api/v1/locations")
        assert r.status_code == 200

    def test_cargo_endpoint_still_works(self, client):
        r = client.get("/api/v1/cargo/consignments")
        assert r.status_code == 200

    def test_inventory_endpoint_still_works(self, client):
        r = client.get("/api/v1/inventory/items")
        assert r.status_code == 200

    def test_assets_endpoint_still_works(self, client):
        r = client.get("/api/v1/assets")
        assert r.status_code == 200

    def test_incidents_endpoint_still_works(self, client):
        r = client.get("/api/v1/incidents")
        assert r.status_code == 200

    def test_sync_endpoint_present(self, client):
        r = client.get("/api/v1/sync")
        assert r.status_code == 200
