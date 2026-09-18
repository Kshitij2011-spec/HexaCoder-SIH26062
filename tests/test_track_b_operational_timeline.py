"""
Comprehensive Test Suite for Person B / Track B - Milestone B9:
Logistics Operational Timeline & Cross-Domain History

Covers:
1. Every supported entity type
2. Sensible aliases
3. Ascending and descending chronological ordering
4. Deterministic tie-breaking for identical timestamps
5. Event + Audit aggregation
6. Strong correlation deduplication (correlation_id + entity_id)
7. False-positive timestamp deduplication protection (independent events within 1.5s not merged)
8. Empty timeline handling
9. Invalid entity type validation error (422)
10. Invalid UUID error handling (422)
11. Nonexistent entity error handling (404)
12. Pagination and page_size slicing
13. Page_size bounds checking
14. Date range filters (occurred_from, occurred_to)
15. Entry type filtering (OPERATIONAL_EVENT, AUDIT_RECORD, etc.)
16. Cross-domain related entity inclusion (include_related=True)
17. Incident lifecycle & B8 propagation history
18. Offline sync lifecycle history (enqueue, apply, retry)
19. Strictly read-only verification (no side-effects, no mutations)
20. API endpoint integration with ApiResponse envelope
"""

from typing import Optional
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.core.errors import EntityNotFoundError, DomainValidationError

# Import all models
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

from backend.app.domains.locations.models import LocationModel
from backend.app.domains.assets.models import AssetModel, MaintenanceRecordModel
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.transport.models import TransportLegModel, TransportCargoAssignmentModel
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.incidents.models import (
    IncidentModel,
    IncidentReferenceModel,
    IncidentPropagationModel,
)
from backend.app.domains.sync.models import OfflineOperationModel
from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.audit.models import AuditLogModel

from backend.app.domains.operations.timeline import OperationalTimelineService
from backend.app.domains.operations.schemas import (
    TimelineEntityType,
    TimelineEntryType,
    TimelineResponse,
)


@pytest.fixture(scope="module")
def client():
    """Isolated in-memory test database fixture for Timeline tests."""
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


# ============================================================
# HELPER SEED FACTORIES
# ============================================================

def _create_location(db: Session, code: str = "LOC-MTR") -> LocationModel:
    loc = LocationModel(
        id=uuid.uuid4(),
        code=code,
        name="Maitri Research Station",
        type="STATION",
        latitude=Decimal("-70.7667"),
        longitude=Decimal("11.7333"),
        status="ACTIVE",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _create_asset(db: Session, code: str = "AST-SNOWCAT-01", location_id: Optional[uuid.UUID] = None) -> AssetModel:
    asset = AssetModel(
        id=uuid.uuid4(),
        asset_code=code,
        name="PistenBully Polar Snowcat",
        type="VEHICLE",
        condition="OPERATIONAL",
        status="AVAILABLE",
        location_id=location_id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _create_cargo(db: Session, code: str = "CRG-B9-001", origin_id: Optional[uuid.UUID] = None, dest_id: Optional[uuid.UUID] = None) -> CargoConsignmentModel:
    now = datetime.now(timezone.utc)
    c = CargoConsignmentModel(
        id=uuid.uuid4(),
        code=code,
        expedition_id=uuid.uuid4(),
        origin_location_id=origin_id or uuid.uuid4(),
        destination_location_id=dest_id or uuid.uuid4(),
        required_by_at=now + timedelta(days=10),
        status="READY",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _create_transport_leg(db: Session, code: str = "LEG-B9-AIR", origin_id: Optional[uuid.UUID] = None, dest_id: Optional[uuid.UUID] = None) -> TransportLegModel:
    now = datetime.now(timezone.utc)
    leg = TransportLegModel(
        id=uuid.uuid4(),
        code=code,
        expedition_id=uuid.uuid4(),
        mode="AIR",
        origin_location_id=origin_id or uuid.uuid4(),
        destination_location_id=dest_id or uuid.uuid4(),
        planned_departure_at=now,
        planned_arrival_at=now + timedelta(hours=6),
        status="SCHEDULED",
    )
    db.add(leg)
    db.commit()
    db.refresh(leg)
    return leg


def _create_inventory_item(db: Session, code: str = "ITEM-FUEL-01") -> InventoryItemModel:
    item = InventoryItemModel(
        id=uuid.uuid4(),
        item_code=code,
        item_name="Polar Aviation Kerosene",
        category="FUEL",
        unit="LITERS",
        criticality="LIFE_SUPPORT",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _create_incident(db: Session, code: str = "INC-B9-001") -> IncidentModel:
    inc = IncidentModel(
        id=uuid.uuid4(),
        incident_code=code,
        title="Blizzard Alert",
        type="WEATHER",
        severity="HIGH",
        status="OPEN",
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


# ============================================================
# 1. SUPPORTED ENTITY TYPES & ALIASES
# ============================================================

def test_timeline_supported_entity_types_and_aliases(db_session: Session):
    svc = OperationalTimelineService(db_session)
    loc = _create_location(db_session, "LOC-SUPPORT-TEST")
    asset = _create_asset(db_session, "AST-SUPPORT-TEST")
    cargo = _create_cargo(db_session, "CRG-SUPPORT-TEST")

    # Canonical type
    res_loc = svc.get_timeline(entity_type="LOCATION", entity_id=loc.id)
    assert res_loc.entity_type == "LOCATION"
    assert res_loc.entity_id == loc.id

    # Alias: CARGO -> CARGO_CONSIGNMENT
    res_cargo = svc.get_timeline(entity_type="cargo", entity_id=cargo.id)
    assert res_cargo.entity_type == "CARGO_CONSIGNMENT"

    # Alias: ASSET
    res_asset = svc.get_timeline(entity_type="ASSET", entity_id=asset.id)
    assert res_asset.entity_type == "ASSET"


def test_timeline_rejects_invalid_entity_type(db_session: Session):
    svc = OperationalTimelineService(db_session)
    with pytest.raises(DomainValidationError) as exc:
        svc.get_timeline(entity_type="INVALID_NONEXISTENT_TYPE", entity_id=uuid.uuid4())
    assert "Invalid or unsupported entity_type" in str(exc.value)


def test_timeline_rejects_nonexistent_entity(db_session: Session):
    svc = OperationalTimelineService(db_session)
    missing_id = uuid.uuid4()
    with pytest.raises(EntityNotFoundError) as exc:
        svc.get_timeline(entity_type="ASSET", entity_id=missing_id)
    assert str(missing_id) in str(exc.value)


# ============================================================
# 2. CHRONOLOGICAL ORDERING & DETERMINISTIC TIE-BREAKING
# ============================================================

def test_timeline_ordering_and_deterministic_tie_breaking(db_session: Session):
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-ORDER-TEST")
    fixed_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # Insert 3 events: 2 with EXACT same timestamp, 1 earlier
    ev_earlier = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="AssetCreated",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=fixed_time - timedelta(hours=1),
        new_state="AVAILABLE",
    )
    ev_tie_b = OperationalEventModel(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        event_id=uuid.uuid4(),
        event_type="B_Action",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=fixed_time,
        new_state="AVAILABLE",
    )
    ev_tie_a = OperationalEventModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        event_id=uuid.uuid4(),
        event_type="A_Action",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=fixed_time,
        new_state="AVAILABLE",
    )
    db_session.add_all([ev_earlier, ev_tie_b, ev_tie_a])
    db_session.commit()

    # Default DESC order (newest first)
    desc_timeline = svc.get_timeline(entity_type="ASSET", entity_id=asset.id, order="desc")
    assert len(desc_timeline.entries) == 3
    # At fixed_time: "B_Action" vs "A_Action" -> in desc sort, "B_Action" comes before "A_Action"
    assert desc_timeline.entries[0].event_or_action == "B_Action"
    assert desc_timeline.entries[1].event_or_action == "A_Action"
    assert desc_timeline.entries[2].event_or_action == "AssetCreated"

    # ASC order (oldest first)
    asc_timeline = svc.get_timeline(entity_type="ASSET", entity_id=asset.id, order="asc")
    assert asc_timeline.entries[0].event_or_action == "AssetCreated"
    assert asc_timeline.entries[1].event_or_action == "A_Action"
    assert asc_timeline.entries[2].event_or_action == "B_Action"


# ============================================================
# 3. DEDUPLICATION: STRONG CORRELATION & SAFE FALLBACK
# ============================================================

def test_strong_correlation_deduplication(db_session: Session):
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-DEDUP-STRONG")
    shared_cid = uuid.uuid4()
    t = datetime.now(timezone.utc)

    # Insert correlated event and audit log sharing correlation_id + entity_id
    ev = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="AssetStatusTransitioned",
        entity_type="ASSET",
        entity_id=asset.id,
        previous_state="AVAILABLE",
        new_state="MAINTENANCE",
        occurred_at=t,
        correlation_id=shared_cid,
        evidence={"reason": "Hydraulic seal leak"},
    )
    audit = AuditLogModel(
        id=uuid.uuid4(),
        action="TRANSITION_ASSET",
        entity_type="ASSET",
        entity_id=asset.id,
        before_snapshot={"status": "AVAILABLE"},
        after_snapshot={"status": "MAINTENANCE"},
        occurred_at=t,
        correlation_id=shared_cid,
        actor_person_id=uuid.uuid4(),
        metadata_={"ip": "10.0.0.1"},
    )
    db_session.add_all([ev, audit])
    db_session.commit()

    timeline = svc.get_timeline(entity_type="ASSET", entity_id=asset.id)
    # Must be merged into ONE entry, NOT two!
    assert timeline.total_entries == 1
    entry = timeline.entries[0]
    assert entry.entry_type == TimelineEntryType.OPERATIONAL_EVENT
    assert entry.event_or_action == "AssetStatusTransitioned"
    assert entry.audit_action == "TRANSITION_ASSET"
    assert entry.event_id == ev.event_id
    assert entry.audit_id == audit.id
    assert entry.correlation_id == shared_cid
    assert entry.actor_id == audit.actor_person_id
    # Details contains merged evidence and snapshots
    assert entry.details["reason"] == "Hydraulic seal leak"
    assert entry.details["before_snapshot"]["status"] == "AVAILABLE"
    assert entry.details["after_snapshot"]["status"] == "MAINTENANCE"


def test_protection_against_false_positive_deduplication(db_session: Session):
    """Verifies that two independent operations happening within 1.5s are NOT falsely merged."""
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-DEDUP-INDEPENDENT")
    t0 = datetime.now(timezone.utc)

    # Event 1: Sensor reading update (no status transition)
    ev = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="TelemetryLogged",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=t0,
        correlation_id=None,
        new_state="AVAILABLE",
    )
    # Audit 2: Independent administrative tag update 0.5s later with DIFFERENT state change
    audit = AuditLogModel(
        id=uuid.uuid4(),
        action="UPDATE_ASSET_METADATA",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=t0 + timedelta(milliseconds=500),
        correlation_id=None,
        before_snapshot={"tags": []},
        after_snapshot={"tags": ["priority_1"]},
    )
    db_session.add_all([ev, audit])
    db_session.commit()

    timeline = svc.get_timeline(entity_type="ASSET", entity_id=asset.id)
    # MUST retain both separate entries because they are independent operations!
    assert timeline.total_entries == 2
    actions = {e.event_or_action for e in timeline.entries}
    assert "TelemetryLogged" in actions
    assert "UPDATE_ASSET_METADATA" in actions


# ============================================================
# 4. PAGINATION & FILTERING
# ============================================================

def test_timeline_pagination(db_session: Session):
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-PAGE-TEST")
    base_t = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)

    # Insert 15 events
    events = [
        OperationalEventModel(
            id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            event_type=f"Event_{i:02d}",
            entity_type="ASSET",
            entity_id=asset.id,
            occurred_at=base_t + timedelta(minutes=i),
            new_state="AVAILABLE",
        )
        for i in range(15)
    ]
    db_session.add_all(events)
    db_session.commit()

    # Page 1 with page_size=5
    p1 = svc.get_timeline(entity_type="ASSET", entity_id=asset.id, page=1, page_size=5, order="asc")
    assert p1.total_entries == 15
    assert p1.total_pages == 3
    assert len(p1.entries) == 5
    assert p1.entries[0].event_or_action == "Event_00"
    assert p1.entries[4].event_or_action == "Event_04"

    # Page 2
    p2 = svc.get_timeline(entity_type="ASSET", entity_id=asset.id, page=2, page_size=5, order="asc")
    assert len(p2.entries) == 5
    assert p2.entries[0].event_or_action == "Event_05"

    # Page 3
    p3 = svc.get_timeline(entity_type="ASSET", entity_id=asset.id, page=3, page_size=5, order="asc")
    assert len(p3.entries) == 5
    assert p3.entries[4].event_or_action == "Event_14"


def test_timeline_date_and_entry_type_filters(db_session: Session):
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-FILTER-TEST")
    t0 = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)

    # Event 1 at 10:00
    ev = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="MorningEvent",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=t0,
        new_state="AVAILABLE",
    )
    # Audit 2 at 12:00
    audit = AuditLogModel(
        id=uuid.uuid4(),
        action="NoonAudit",
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_at=t0 + timedelta(hours=2),
    )
    db_session.add_all([ev, audit])
    db_session.commit()

    # Filter occurred_from >= 11:00
    res_date = svc.get_timeline(
        entity_type="ASSET",
        entity_id=asset.id,
        occurred_from=t0 + timedelta(hours=1),
    )
    assert res_date.total_entries == 1
    assert res_date.entries[0].event_or_action == "NoonAudit"

    # Filter entry_type=OPERATIONAL_EVENT
    res_type = svc.get_timeline(
        entity_type="ASSET",
        entity_id=asset.id,
        entry_type="OPERATIONAL_EVENT",
    )
    assert res_type.total_entries == 1
    assert res_type.entries[0].event_or_action == "MorningEvent"


# ============================================================
# 5. CROSS-DOMAIN RELATED ENTITY INCLUSION
# ============================================================

def test_cross_domain_related_entity_inclusion(db_session: Session):
    svc = OperationalTimelineService(db_session)
    loc_a = _create_location(db_session, "LOC-REL-A")
    loc_b = _create_location(db_session, "LOC-REL-B")
    leg = _create_transport_leg(db_session, "LEG-REL-TEST", loc_a.id, loc_b.id)
    cargo = _create_cargo(db_session, "CRG-REL-TEST", loc_a.id, loc_b.id)

    # Assign cargo to leg
    assign = TransportCargoAssignmentModel(
        id=uuid.uuid4(),
        transport_leg_id=leg.id,
        cargo_consignment_id=cargo.id,
    )
    db_session.add(assign)

    # Event on transport leg
    ev_leg = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="TransportLegDispatched",
        entity_type="TRANSPORT_LEG",
        entity_id=leg.id,
        occurred_at=datetime.now(timezone.utc),
        new_state="IN_TRANSIT",
    )
    # Event on cargo consignment
    ev_cargo = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="CargoLoaded",
        entity_type="CARGO_CONSIGNMENT",
        entity_id=cargo.id,
        occurred_at=datetime.now(timezone.utc),
        new_state="IN_TRANSIT",
    )
    db_session.add_all([ev_leg, ev_cargo])
    db_session.commit()

    # Query without related entities: should only show leg events
    direct_timeline = svc.get_timeline(entity_type="TRANSPORT_LEG", entity_id=leg.id, include_related=False)
    assert direct_timeline.total_entries == 1
    assert direct_timeline.entries[0].entity_type == "TRANSPORT_LEG"

    # Query WITH related entities: should include cargo consignment events!
    related_timeline = svc.get_timeline(entity_type="TRANSPORT_LEG", entity_id=leg.id, include_related=True)
    assert related_timeline.total_entries == 2
    entity_types = {e.entity_type for e in related_timeline.entries}
    assert "TRANSPORT_LEG" in entity_types
    assert "CARGO_CONSIGNMENT" in entity_types
    assert related_timeline.related_entities_included is True


# ============================================================
# 6. INCIDENT PROPAGATION & OFFLINE SYNC HISTORY
# ============================================================

def test_incident_propagation_history_in_timeline(db_session: Session):
    svc = OperationalTimelineService(db_session)
    inc = _create_incident(db_session, "INC-TIMELINE-PROP")
    asset = _create_asset(db_session, "AST-TIMELINE-PROP")

    # Add reference
    ref = IncidentReferenceModel(
        id=uuid.uuid4(),
        incident_id=inc.id,
        reference_type="ASSET",
        reference_id=asset.id,
    )
    # Add B8 propagation record
    prop = IncidentPropagationModel(
        id=uuid.uuid4(),
        incident_id=inc.id,
        reference_type="ASSET",
        reference_id=asset.id,
        action="MAINTENANCE_ASSET",
        status="APPLIED",
        previous_state="AVAILABLE",
        resulting_state="MAINTENANCE",
        reason="Generator coolant leak",
    )
    # Add incident lifecycle event
    ev = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="IncidentDeclared",
        entity_type="INCIDENT",
        entity_id=inc.id,
        occurred_at=datetime.now(timezone.utc),
        new_state="OPEN",
    )
    db_session.add_all([ref, prop, ev])
    db_session.commit()

    timeline = svc.get_timeline(entity_type="INCIDENT", entity_id=inc.id, include_related=True)
    assert timeline.total_entries >= 2
    entry_types = {e.entry_type for e in timeline.entries}
    assert TimelineEntryType.PROPAGATION_RECORD in entry_types
    assert TimelineEntryType.OPERATIONAL_EVENT in entry_types

    # Find propagation entry
    prop_entry = next(e for e in timeline.entries if e.entry_type == TimelineEntryType.PROPAGATION_RECORD)
    assert prop_entry.status == "APPLIED"
    assert "MAINTENANCE_ASSET" in prop_entry.event_or_action
    assert prop_entry.details["reason"] == "Generator coolant leak"


def test_offline_sync_lifecycle_history(db_session: Session):
    svc = OperationalTimelineService(db_session)
    op = OfflineOperationModel(
        id=uuid.uuid4(),
        operation_id=uuid.uuid4(),
        entity_type="INVENTORY_ITEM",
        operation_type="CREATE",
        payload={"item_code": "SYNC-TEST-01"},
        status="APPLIED",
        queued_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        applied_at=datetime.now(timezone.utc),
        retry_count=1,
    )
    db_session.add(op)
    db_session.commit()

    timeline = svc.get_timeline(entity_type="OFFLINE_OPERATION", entity_id=op.id)
    assert timeline.total_entries == 1
    entry = timeline.entries[0]
    assert entry.entry_type == TimelineEntryType.OFFLINE_SYNC
    assert entry.status == "APPLIED"
    assert entry.details["retry_count"] == 1


# ============================================================
# 7. STRICT READ-ONLY / NO SIDE-EFFECT VERIFICATION
# ============================================================

def test_timeline_is_strictly_read_only(db_session: Session):
    svc = OperationalTimelineService(db_session)
    asset = _create_asset(db_session, "AST-READONLY-TEST")

    # Record counts before
    event_count_before = db_session.execute(select(func.count(OperationalEventModel.id))).scalar()
    audit_count_before = db_session.execute(select(func.count(AuditLogModel.id))).scalar()
    asset_status_before = asset.status

    # Query timeline multiple times with various parameters
    svc.get_timeline(entity_type="ASSET", entity_id=asset.id, include_related=True)
    svc.get_timeline(entity_type="ASSET", entity_id=asset.id, include_related=False, order="asc")

    # Verify zero mutations occurred
    event_count_after = db_session.execute(select(func.count(OperationalEventModel.id))).scalar()
    audit_count_after = db_session.execute(select(func.count(AuditLogModel.id))).scalar()
    assert event_count_after == event_count_before
    assert audit_count_after == audit_count_before
    assert asset.status == asset_status_before


# ============================================================
# 8. API ENDPOINT INTEGRATION & ENVELOPE VERIFICATION
# ============================================================

def test_api_endpoint_timeline(client: TestClient, db_session: Session):
    loc = _create_location(db_session, "LOC-API-TEST")
    ev = OperationalEventModel(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        event_type="LocationStatusChanged",
        entity_type="LOCATION",
        entity_id=loc.id,
        previous_state="ACTIVE",
        new_state="RESTRICTED",
        occurred_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    db_session.commit()

    # Success call
    resp = client.get(f"/api/v1/operations/timeline/LOCATION/{loc.id}?order=desc&page=1&page_size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None
    assert body["data"]["entity_type"] == "LOCATION"
    assert body["data"]["entity_id"] == str(loc.id)
    assert len(body["data"]["entries"]) == 1
    assert body["data"]["entries"][0]["event_or_action"] == "LocationStatusChanged"

    # Alias call (cargo)
    cargo = _create_cargo(db_session, "CRG-API-TEST")
    resp_alias = client.get(f"/api/v1/operations/timeline/cargo/{cargo.id}")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["data"]["entity_type"] == "CARGO_CONSIGNMENT"

    # 404 for missing entity
    missing_id = uuid.uuid4()
    resp_404 = client.get(f"/api/v1/operations/timeline/ASSET/{missing_id}")
    assert resp_404.status_code == 404
    assert resp_404.json()["errors"] is not None

    # 422 for invalid entity type
    resp_invalid = client.get(f"/api/v1/operations/timeline/NONEXISTENT_TYPE/{loc.id}")
    assert resp_invalid.status_code == 422

    # 422 for invalid UUID format
    resp_bad_uuid = client.get("/api/v1/operations/timeline/LOCATION/not-a-valid-uuid")
    assert resp_bad_uuid.status_code == 422

    # 422 for page_size > 200
    resp_bad_page_size = client.get(f"/api/v1/operations/timeline/LOCATION/{loc.id}?page_size=300")
    assert resp_bad_page_size.status_code == 422


def test_timeline_empty_history(db_session: Session):
    svc = OperationalTimelineService(db_session)
    loc = _create_location(db_session, "LOC-EMPTY-TEST")
    timeline = svc.get_timeline(entity_type="LOCATION", entity_id=loc.id)
    assert timeline.total_entries == 0
    assert timeline.total_pages == 1
    assert timeline.entries == []


def test_all_other_person_b_entity_types(db_session: Session):
    svc = OperationalTimelineService(db_session)
    # Inventory Item
    item = _create_inventory_item(db_session, "ITEM-ALL-TYPES")
    tl_item = svc.get_timeline(entity_type="INVENTORY_ITEM", entity_id=item.id)
    assert tl_item.entity_type == "INVENTORY_ITEM"

    # Inventory Stock Lot
    lot = InventoryStockLotModel(
        id=uuid.uuid4(),
        inventory_item_id=item.id,
        lot_code="LOT-ALL-TYPES-01",
        location_id=uuid.uuid4(),
        on_hand_quantity=Decimal("100"),
        status="AVAILABLE",
    )
    db_session.add(lot)
    db_session.commit()
    tl_lot = svc.get_timeline(entity_type="INVENTORY_STOCK_LOT", entity_id=lot.id)
    assert tl_lot.entity_type == "INVENTORY_STOCK_LOT"

    # Cargo Package
    cargo = _create_cargo(db_session, "CRG-PKG-PARENT")
    pkg = CargoPackageModel(
        id=uuid.uuid4(),
        code="PKG-ALL-TYPES-01",
        consignment_id=cargo.id,
        quantity=Decimal("1"),
        status="PACKED",
    )
    db_session.add(pkg)
    db_session.commit()
    tl_pkg = svc.get_timeline(entity_type="CARGO_PACKAGE", entity_id=pkg.id)
    assert tl_pkg.entity_type == "CARGO_PACKAGE"

    # Maintenance Record
    asset = _create_asset(db_session, "AST-MAINT-PARENT")
    maint = MaintenanceRecordModel(
        id=uuid.uuid4(),
        asset_id=asset.id,
        maintenance_type="PREVENTATIVE",
        status="SCHEDULED",
    )
    db_session.add(maint)
    db_session.commit()
    tl_maint = svc.get_timeline(entity_type="MAINTENANCE_RECORD", entity_id=maint.id)
    assert tl_maint.entity_type == "MAINTENANCE_RECORD"

    # Incident Reference
    inc = _create_incident(db_session, "INC-REF-PARENT")
    ref = IncidentReferenceModel(
        id=uuid.uuid4(),
        incident_id=inc.id,
        reference_type="LOCATION",
        reference_id=uuid.uuid4(),
    )
    db_session.add(ref)
    db_session.commit()
    tl_ref = svc.get_timeline(entity_type="INCIDENT_REFERENCE", entity_id=ref.id)
    assert tl_ref.entity_type == "INCIDENT_REFERENCE"
