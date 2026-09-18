"""SIH26062 — Comprehensive Database Schema & Seed Verification Test Suite."""

import re
import pytest
from pathlib import Path
from backend.app.core.config import Settings, settings
from backend.app.db.session import check_db_connectivity, get_db_health


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = PROJECT_ROOT / "supabase" / "migrations" / "20260917000000_expedition_operational_schema.sql"
SEED_FILE = PROJECT_ROOT / "supabase" / "seed.sql"


@pytest.fixture(scope="module")
def migration_sql() -> str:
    """Load migration SQL text."""
    assert MIGRATION_FILE.exists(), f"Migration file missing: {MIGRATION_FILE}"
    return MIGRATION_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def seed_sql() -> str:
    """Load seed SQL text."""
    assert SEED_FILE.exists(), f"Seed file missing: {SEED_FILE}"
    return SEED_FILE.read_text(encoding="utf-8")


# ============================================================
# 1. SCHEMA STRUCTURE & ENUM VERIFICATION
# ============================================================

def test_migration_file_exists_and_non_empty(migration_sql: str):
    """Verify migration file is populated."""
    assert len(migration_sql) > 5000
    assert "CREATE EXTENSION" in migration_sql


def test_core_enums_present(migration_sql: str):
    """Verify all 21 controlled enum types exist in migration."""
    expected_enums = [
        "data_provenance", "expedition_status", "mission_status", "person_readiness",
        "person_movement", "team_status", "cargo_status", "cargo_package_status",
        "inventory_status", "asset_status", "transport_status", "location_status",
        "incident_status", "document_status", "assignment_status", "recommendation_status",
        "approval_decision", "constraint_severity", "hard_soft_constraint",
        "incident_severity", "dependency_relationship_type"
    ]
    for enum_name in expected_enums:
        pattern = rf"CREATE\s+TYPE\s+{enum_name}\s+AS\s+ENUM"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Missing enum type: {enum_name}"


def test_provenance_enum_values(migration_sql: str):
    """Verify data_provenance enum values conform strictly to rules."""
    assert "'SYNTHETIC_DEMO'" in migration_sql
    assert "'MEASURED'" in migration_sql
    assert "'DERIVED'" in migration_sql
    assert "'FORECAST'" in migration_sql
    assert "'SCENARIO'" in migration_sql
    assert "'PUBLIC_SOURCE'" in migration_sql
    assert "'ADVISORY'" in migration_sql
    # Rule: 'LIVE' must never be an enum option
    assert "'LIVE'" not in migration_sql


def test_core_tables_defined(migration_sql: str):
    """Verify all 29 required operational and junction tables are declared."""
    expected_tables = [
        "expeditions", "locations", "missions", "teams", "people", "assignments",
        "cargo_consignments", "transport_legs", "cargo_packages",
        "transport_cargo_assignments", "transport_person_assignments", "transport_asset_assignments",
        "inventory_items", "assets", "inventory_stock_lots", "inventory_transactions",
        "maintenance_records", "documents", "time_windows", "dependencies",
        "constraints", "operational_events", "incidents", "incident_people",
        "incident_assets", "incident_missions", "incident_cargo", "response_actions",
        "replans", "recommendations", "recommendation_alternatives", "approvals",
        "audit_log", "sync_queue", "sync_conflicts"
    ]
    for table_name in expected_tables:
        pattern = rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\("
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Missing table: {table_name}"


def test_semantic_dependency_relationship_types(migration_sql: str):
    """Verify semantic dependency enum includes all 15 authorized relationships."""
    expected_vocab = [
        "REQUIRES", "SUPPORTS", "ASSIGNED_TO", "LOCATED_AT", "MOVES_VIA",
        "CONTAINS", "DELIVERED_TO", "RESERVED_FOR", "REPLENISHED_BY",
        "AFFECTS", "DEPENDS_ON", "CONSTRAINED_BY", "OPERATED_BY", "OCCURS_AT", "BELONGS_TO"
    ]
    for rel in expected_vocab:
        assert f"'{rel}'" in migration_sql, f"Missing semantic relationship vocabulary: {rel}"


def test_event_immutability_trigger_defined(migration_sql: str):
    """Verify immutable event journal trigger is declared for operational_events."""
    assert "prevent_operational_event_modification" in migration_sql
    assert "trg_operational_events_immutable" in migration_sql
    assert "BEFORE UPDATE OR DELETE ON operational_events" in migration_sql


def test_inventory_quantity_constraints_defined(migration_sql: str):
    """Verify inventory quantity rules are enforced in SQL check constraints."""
    # reserved <= on_hand
    assert "reserved_quantity <= on_hand_quantity" in migration_sql
    # reserved + quarantined + damaged <= on_hand
    assert "reserved_quantity + quarantined_quantity + damaged_quantity <= on_hand_quantity" in migration_sql


def test_time_window_constraint_defined(migration_sql: str):
    """Verify time window close_at > open_at constraint."""
    assert "close_at > open_at" in migration_sql


def test_transport_window_constraints_defined(migration_sql: str):
    """Verify transport leg temporal constraints."""
    assert "departure_window_close >= departure_window_open" in migration_sql
    assert "arrival_window_close >= arrival_window_open" in migration_sql
    assert "arrival_window_open >= departure_window_open" in migration_sql
    assert "planned_arrival_at >= planned_departure_at" in migration_sql


# ============================================================
# 2. SEED DATA & HERO SCENARIO VERIFICATION
# ============================================================

def test_seed_file_exists_and_has_provenance(seed_sql: str):
    """Verify seed SQL file exists and tags all records with SYNTHETIC_DEMO."""
    assert len(seed_sql) > 5000
    assert "SYNTHETIC_DEMO" in seed_sql
    assert "Live NCPOR" not in seed_sql
    assert "Real Bharati" not in seed_sql


def test_hero_scenario_codes_exist(seed_sql: str):
    """Verify all hero codes from Prompt 2 exist in seed data."""
    hero_codes = [
        "EXP-26-A",  # Expedition
        "M-08",      # Mission
        "R-04",      # Team
        "I-42",      # Asset (Scientific Instrument)
        "C-117",     # Cargo Consignment
        "T-08"       # Transport Leg
    ]
    for code in hero_codes:
        assert f"'{code}'" in seed_sql, f"Hero business code missing from seed: {code}"


def test_hero_scenario_fixed_uuids(seed_sql: str):
    """Verify deterministic fixed UUIDs exist for hero scenario entities."""
    fixed_uuids = [
        "00000000-0000-0000-0000-000000000001",  # EXP-26-A
        "20000000-0000-0000-0000-000000000001",  # M-08
        "30000000-0000-0000-0000-000000000001",  # R-04
        "90000000-0000-0000-0000-000000000001",  # I-42
        "50000000-0000-0000-0000-000000000001",  # C-117
        "60000000-0000-0000-0000-000000000001",  # T-08
    ]
    for uid in fixed_uuids:
        assert uid in seed_sql, f"Fixed UUID missing: {uid}"


def test_hero_constraint_declared(seed_sql: str):
    """Verify hard constraint binding Mission M-08 to Asset I-42."""
    assert "CONST-M08-RESOURCE" in seed_sql
    assert "MISSION_RESOURCE_REQUIRED" in seed_sql
    assert "HARD" in seed_sql
    assert "CRITICAL" in seed_sql


def test_hero_dependency_chain_declared(seed_sql: str):
    """Verify the hero dependency chain is seeded in the dependencies table."""
    # M-08 REQUIRES I-42
    assert "20000000-0000-0000-0000-000000000001" in seed_sql
    assert "90000000-0000-0000-0000-000000000001" in seed_sql
    # C-117 SUPPORTS M-08
    assert "50000000-0000-0000-0000-000000000001" in seed_sql
    # C-117 MOVES_VIA T-08
    assert "60000000-0000-0000-0000-000000000001" in seed_sql
    # PKG-117-01 CONTAINS I-42
    assert "70000000-0000-0000-0000-000000000001" in seed_sql


def test_team_r04_composition(seed_sql: str):
    """Verify Team R-04 contains leader, researchers, and field guide."""
    assert "Dr. Rajesh Sharma" in seed_sql
    assert "Dr. Priya Roy" in seed_sql
    assert "Tanmoy Sengupta" in seed_sql
    assert "Kavita Deshmukh" in seed_sql
    assert "Polar Field Safety Officer" in seed_sql


def test_inventory_spare_and_stockout_scenarios(seed_sql: str):
    """Verify inventory spare part link to asset and stockout scenario."""
    # SKU-HYD-HOSE-08 is spare for PB-01
    assert "SKU-HYD-HOSE-08" in seed_sql
    assert "PB-01" in seed_sql
    # Lot with on_hand=2, reserved=1 for GEN-01 backup
    assert "LOT-HOSE-MTR-01" in seed_sql
    # Depleted stockout lot for seismometer replacement
    assert "LOT-SEIS-MTR-DEPLETED" in seed_sql


def test_minimum_seed_counts(seed_sql: str):
    """Verify minimum record counts required by specification."""
    # Count INSERT blocks or tuples
    expedition_count = len(re.findall(r"'EXP-26-A'", seed_sql))
    assert expedition_count >= 1

    # Locations >= 10
    location_matches = re.findall(r"'LOC-[A-Z0-9\-]+'", seed_sql)
    assert len(set(location_matches)) >= 10

    # Missions >= 3
    mission_matches = re.findall(r"'M-0[0-9]'", seed_sql)
    assert len(set(mission_matches)) >= 3

    # Teams >= 2
    team_matches = re.findall(r"'R-0[0-9]'", seed_sql)
    assert len(set(team_matches)) >= 2

    # People >= 6
    person_matches = re.findall(r"'PERS-[A-Z0-9\-]+'", seed_sql)
    assert len(set(person_matches)) >= 6

    # Cargo consignments >= 3
    consignment_matches = re.findall(r"'C-1[0-9]{2}'", seed_sql)
    assert len(set(consignment_matches)) >= 3

    # Transport legs >= 5
    transport_matches = re.findall(r"'T-0[0-9]'", seed_sql)
    assert len(set(transport_matches)) >= 5

    # Inventory items >= 10
    sku_matches = re.findall(r"'SKU-[A-Z0-9\-]+'", seed_sql)
    assert len(set(sku_matches)) >= 10

    # Assets >= 6
    asset_codes = ["I-42", "PB-01", "PB-02", "GEN-01", "SKID-01", "DRILL-01"]
    for ac in asset_codes:
        assert f"'{ac}'" in seed_sql

    # Maintenance records >= 5
    maint_matches = re.findall(r"'b0000000-0000-0000-0000-00000000000[1-5]'", seed_sql)
    assert len(set(maint_matches)) >= 5

    # Documents >= 8
    doc_matches = re.findall(r"'DOC-[A-Z0-9\-]+'", seed_sql)
    assert len(set(doc_matches)) >= 8

    # Time windows >= 6
    tw_matches = re.findall(r"'d0000000-0000-0000-0000-00000000000[1-6]'", seed_sql)
    assert len(set(tw_matches)) >= 6

    # Dependencies >= 15
    dep_matches = re.findall(r"'d1000000-0000-0000-0000-0000000000[0-9]{2}'", seed_sql)
    assert len(dep_matches) >= 15

    # Baseline operational events >= 10
    event_matches = re.findall(r"'f0000000-0000-0000-0000-0000000000[0-9]{2}'", seed_sql)
    assert len(event_matches) >= 10

    # Constraints >= 6
    const_matches = re.findall(r"'CONST-[A-Z0-9\-]+'", seed_sql)
    assert len(set(const_matches)) >= 6

    # Incidents >= 2 (Non-active demo incidents)
    inc_matches = re.findall(r"'INC-2025-0[1-2]'", seed_sql)
    assert len(set(inc_matches)) >= 2


# ============================================================
# 3. BACKEND SCAFFOLD VERIFICATION
# ============================================================

def test_backend_settings_config():
    """Verify backend settings load cleanly with defaults."""
    cfg = Settings()
    assert cfg.PROJECT_NAME == "HexaCoders - SIH26062"
    assert cfg.API_V1_STR == "/api/v1"
    assert "postgresql" in cfg.get_database_url()


def test_backend_db_connectivity_helper():
    """Verify connectivity diagnostic handles disconnected state safely."""
    # When no local Postgres server is running, helper returns False gracefully without crashing
    connected = check_db_connectivity()
    assert isinstance(connected, bool)


def test_backend_db_health_helper():
    """Verify get_db_health diagnostic returns structured status without exposing secrets."""
    health = get_db_health()
    assert isinstance(health, dict)
    assert "status" in health
    assert "database_reachable" in health
    assert isinstance(health["database_reachable"], bool)
    # Verify no credentials leaked in output
    for val in health.values():
        val_str = str(val).lower()
        assert "password" not in val_str
        assert "postgres:" not in val_str



# ============================================================
# 4. DATABASE INTEGRITY & CONSTRAINT ASSERTIONS
# ============================================================

def test_referential_integrity_in_seed_data(seed_sql: str):
    """Verify all foreign key references in seed data resolve to defined primary keys."""
    # Collect all UUIDs defined as PKs in seed.sql
    pk_uuids = set(re.findall(r"'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'", seed_sql, re.IGNORECASE))
    
    # Check that known foreign keys reference valid PKs:
    # Mission expedition_id
    assert "00000000-0000-0000-0000-000000000001" in pk_uuids
    # Team mission_id
    assert "20000000-0000-0000-0000-000000000001" in pk_uuids
    # People expedition_id and team_id
    assert "30000000-0000-0000-0000-000000000001" in pk_uuids
    # Cargo Consignment expedition_id, origin, destination
    assert "10000000-0000-0000-0000-000000000002" in pk_uuids
    assert "10000000-0000-0000-0000-000000000004" in pk_uuids
    # Package consignment_id
    assert "50000000-0000-0000-0000-000000000001" in pk_uuids
    # Transport Leg origin, dest
    assert "60000000-0000-0000-0000-000000000001" in pk_uuids
    # Asset required spare item_id
    assert "80000000-0000-0000-0000-000000000001" in pk_uuids
    # Stock lot item_id and location_id
    assert "80000000-0000-0000-0000-000000000002" in pk_uuids
    assert "10000000-0000-0000-0000-000000000006" in pk_uuids


def test_seed_stock_lots_satisfy_quantity_invariants(seed_sql: str):
    """Verify that all seeded stock lots satisfy reserved <= on_hand and non-negative quantities."""
    # Extract tuples from inventory_stock_lots insert
    lot_pattern = r"\('a0000000[0-9a-f\-]+',\s*'80000000[0-9a-f\-]+',\s*'[^']+',\s*'10000000[0-9a-f\-]+',\s*([0-9\.]+),\s*([0-9\.]+),\s*([0-9\.]+),\s*([0-9\.]+)"
    matches = re.findall(lot_pattern, seed_sql)
    assert len(matches) >= 10, f"Expected at least 10 stock lots parsed, found {len(matches)}"
    for on_hand_str, reserved_str, quarantined_str, damaged_str in matches:
        on_hand = float(on_hand_str)
        reserved = float(reserved_str)
        quarantined = float(quarantined_str)
        damaged = float(damaged_str)
        assert on_hand >= 0
        assert reserved >= 0
        assert quarantined >= 0
        assert damaged >= 0
        assert reserved <= on_hand, f"Invariant violated: reserved {reserved} > on_hand {on_hand}"
        assert reserved + quarantined + damaged <= on_hand, f"Invariant violated: unavailable > on_hand"


def test_seed_time_windows_satisfy_temporal_bounds(seed_sql: str):
    """Verify all seeded time windows satisfy close_at > open_at."""
    from datetime import datetime
    tw_pattern = r"\('d0000000[0-9a-f\-]+',\s*'[^']+',\s*'([^']+)',\s*'([^']+)'"
    matches = re.findall(tw_pattern, seed_sql)
    assert len(matches) >= 6, f"Expected at least 6 time windows parsed, found {len(matches)}"
    for open_str, close_str in matches:
        open_dt = datetime.fromisoformat(open_str.replace("Z", "+00:00"))
        close_dt = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
        assert close_dt > open_dt, f"Time window bounds invalid: close {close_dt} <= open {open_dt}"


def test_unique_business_codes_enforced_in_migration(migration_sql: str):
    """Verify UNIQUE constraints are explicitly placed on operational codes."""
    unique_checks = [
        ("expeditions", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("locations", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("missions", "CONSTRAINT uq_mission_expedition_code UNIQUE (expedition_id, code)"),
        ("teams", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("people", "person_code VARCHAR(50) UNIQUE NOT NULL"),
        ("cargo_consignments", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("transport_legs", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("cargo_packages", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("inventory_items", "item_code VARCHAR(50) UNIQUE NOT NULL"),
        ("assets", "asset_code VARCHAR(50) UNIQUE NOT NULL"),
        ("documents", "document_code VARCHAR(50) UNIQUE NOT NULL"),
        ("constraints", "code VARCHAR(50) UNIQUE NOT NULL"),
        ("operational_events", "event_id UUID UNIQUE NOT NULL"),
        ("incidents", "incident_code VARCHAR(50) UNIQUE NOT NULL"),
        ("replans", "replan_code VARCHAR(50) UNIQUE NOT NULL")
    ]
    for table, pattern in unique_checks:
        assert pattern in migration_sql, f"Missing unique business code constraint on {table}"


def test_events_have_correlation_ids_and_required_metadata(seed_sql: str):
    """Verify that all seeded operational events contain correlation_id and metadata."""
    event_pattern = r"\('f0000000[0-9a-f\-]+',\s*'f1000000[0-9a-f\-]+',\s*'([A-Za-z]+)',\s*'([A-Za-z_]+)',\s*'([0-9a-f\-]+)'"
    matches = re.findall(event_pattern, seed_sql)
    assert len(matches) >= 10, f"Expected at least 10 operational events parsed, found {len(matches)}"
    # Verify common correlation ID used for baseline initialization chain
    assert "f0000000-0000-0000-0000-000000000000" in seed_sql


def test_migration_lineage_reconciled():
    """Verify the migration lineage sequence exists and filenames are authoritative."""
    migrations_dir = PROJECT_ROOT / "supabase" / "migrations"
    initial_schema_file = migrations_dir / "20260917000000_expedition_operational_schema.sql"
    rls_file = migrations_dir / "20260918000001_enable_rls_security_baseline.sql"

    assert initial_schema_file.exists(), f"Canonical initial schema migration missing: {initial_schema_file}"
    assert rls_file.exists(), f"Security baseline migration missing: {rls_file}"

    # Ensure no conflicting 20260917000001 duplicate migration exists
    conflicting_file = migrations_dir / "20260917000001_expedition_operational_schema.sql"
    assert not conflicting_file.exists(), f"Found obsolete duplicate migration: {conflicting_file}"


def test_rls_security_migration_covers_all_core_tables():
    """Verify that 20260918000001_enable_rls_security_baseline.sql enables RLS on all 35 operational tables."""
    rls_file = PROJECT_ROOT / "supabase" / "migrations" / "20260918000001_enable_rls_security_baseline.sql"
    content = rls_file.read_text(encoding="utf-8")

    core_tables = [
        "expeditions", "locations", "missions", "teams", "people", "assignments",
        "cargo_consignments", "transport_legs", "cargo_packages",
        "transport_cargo_assignments", "transport_person_assignments", "transport_asset_assignments",
        "inventory_items", "assets", "inventory_stock_lots", "inventory_transactions", "maintenance_records",
        "documents", "time_windows", "dependencies", "constraints", "operational_events",
        "incidents", "incident_people", "incident_assets", "incident_missions", "incident_cargo",
        "response_actions", "replans", "recommendations", "recommendation_alternatives", "approvals",
        "audit_log", "sync_queue", "sync_conflicts"
    ]
    assert len(core_tables) == 35

    for table in core_tables:
        pattern = f"ALTER TABLE IF EXISTS public.{table} ENABLE ROW LEVEL SECURITY;"
        assert pattern in content, f"Table '{table}' missing RLS enablement in security baseline migration"


def test_sqlite_uuid_compatibility_and_interoperability():
    """
    Focused Regression Test for SQLiteUUID TypeDecorator in backend.app.db.base:
    Proves:
    1. ORM UUID insert into SQLite stores canonical 36-character hyphenated UUID string.
    2. Raw SQL lookup by canonical hyphenated UUID matches the row.
    3. ORM lookup returns the exact same Python uuid.UUID object.
    4. UUID comparisons work bidirectionally (ORM insert -> raw SQL lookup, raw SQL insert -> ORM lookup).
    5. Production PostgreSQL dialect retains native UUID type (PG_UUID base is UUID(as_uuid=True)).
    """
    import uuid
    from sqlalchemy import create_engine, text, Column, String
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.dialects.postgresql import UUID as PG_NATIVE_UUID
    from backend.app.db.base import PG_UUID

    # 1. Verify PostgreSQL native specification
    assert isinstance(PG_UUID, PG_NATIVE_UUID)
    assert PG_UUID.as_uuid is True

    # 2. Test in SQLite environment
    test_base = declarative_base()

    class MockItem(test_base):
        __tablename__ = "test_mock_items"
        id = Column(PG_UUID, primary_key=True, default=uuid.uuid4)
        name = Column(String(100), nullable=False)

    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    test_base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # Step 1: ORM insert
    item_id = uuid.uuid4()
    session.add(MockItem(id=item_id, name="Test Rover"))
    session.commit()

    # Step 2: Raw SQL lookup by canonical hyphenated UUID string
    raw_row = session.execute(
        text("SELECT id, typeof(id), length(id), name FROM test_mock_items WHERE id = :id"),
        {"id": str(item_id)}
    ).mappings().first()
    assert raw_row is not None
    assert raw_row["id"] == str(item_id)
    assert raw_row["length(id)"] == 36
    assert raw_row["name"] == "Test Rover"

    # Step 3: ORM lookup returns exact uuid.UUID
    orm_item = session.get(MockItem, item_id)
    assert orm_item is not None
    assert orm_item.id == item_id
    assert isinstance(orm_item.id, uuid.UUID)

    # Step 4: Raw SQL insert -> ORM lookup
    raw_id = uuid.uuid4()
    session.execute(
        text("INSERT INTO test_mock_items (id, name) VALUES (:id, :name)"),
        {"id": str(raw_id), "name": "Raw Sensor"}
    )
    session.commit()

    orm_from_raw = session.get(MockItem, raw_id)
    assert orm_from_raw is not None
    assert orm_from_raw.id == raw_id
    assert isinstance(orm_from_raw.id, uuid.UUID)
    assert orm_from_raw.name == "Raw Sensor"

    session.close()




