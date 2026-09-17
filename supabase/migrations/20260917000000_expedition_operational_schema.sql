-- ============================================================
-- SIH26062 — HexaCoders Polar Expedition Operations Platform
-- Migration: 20260917000000_expedition_operational_schema.sql
-- Description: Core relational schema, enums, constraints, indexes & triggers
-- ============================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUMS & CONTROLLED TYPES
DO $$ BEGIN
    CREATE TYPE data_provenance AS ENUM (
        'MEASURED', 'DERIVED', 'FORECAST', 'SCENARIO', 'SYNTHETIC_DEMO', 'PUBLIC_SOURCE', 'ADVISORY'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE expedition_status AS ENUM (
        'DRAFT', 'PLANNED', 'MOBILIZATION', 'ACTIVE', 'CLOSEOUT', 'ARCHIVED', 'ON_HOLD'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE mission_status AS ENUM (
        'PROPOSED', 'APPROVED', 'READY', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED', 'DEFERRED', 'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE person_readiness AS ENUM (
        'NOMINATED', 'CLEARANCE_PENDING', 'READY', 'NOT_CLEARED', 'UNAVAILABLE'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE person_movement AS ENUM (
        'NOT_DEPLOYED', 'IN_TRANSIT', 'AT_STATION', 'FIELD', 'RETURNING', 'RETURNED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE team_status AS ENUM (
        'FORMING', 'READY', 'DEPLOYED', 'FIELD', 'RETURNED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE cargo_status AS ENUM (
        'REQUESTED', 'DECLARED', 'APPROVED', 'PACKED', 'READY', 'DISPATCHED',
        'IN_TRANSIT', 'ARRIVED', 'RECEIVED', 'HELD', 'DELAYED', 'DAMAGED', 'LOST', 'REJECTED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE cargo_package_status AS ENUM (
        'PACKED', 'LOADED', 'IN_TRANSIT', 'RECEIVED', 'ISSUED', 'RETURNED', 'HELD', 'DAMAGED', 'LOST'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE inventory_status AS ENUM (
        'ON_ORDER', 'INBOUND', 'AVAILABLE', 'RESERVED', 'ISSUED', 'CONSUMED', 'TRANSFERRED', 'QUARANTINED', 'DISPOSED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE asset_status AS ENUM (
        'AVAILABLE', 'RESERVED', 'DEPLOYED', 'IN_USE', 'MAINTENANCE', 'SERVICEABLE', 'UNSERVICEABLE', 'RETIRED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE transport_status AS ENUM (
        'PLANNED', 'BOOKED', 'READY', 'DEPARTED', 'IN_TRANSIT', 'ARRIVED', 'CLOSED', 'DELAYED', 'DIVERTED', 'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE location_status AS ENUM (
        'AVAILABLE', 'RESTRICTED', 'INACCESSIBLE', 'CLOSED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_status AS ENUM (
        'DETECTED', 'TRIAGED', 'DECLARED', 'RESPONSE_ASSIGNED', 'ACTIVE', 'STABILIZED', 'RESOLVED', 'CLOSED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE document_status AS ENUM (
        'REQUIRED', 'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'EXPIRED', 'MISSING'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE assignment_status AS ENUM (
        'PROPOSED', 'APPROVED', 'ACTIVE', 'COMPLETED', 'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE recommendation_status AS ENUM (
        'PROPOSED', 'APPROVED', 'REJECTED', 'NEEDS_REVISION', 'IMPLEMENTED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE approval_decision AS ENUM (
        'APPROVED', 'REJECTED', 'MODIFIED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE constraint_severity AS ENUM (
        'INFO', 'WARNING', 'CRITICAL'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE hard_soft_constraint AS ENUM (
        'HARD', 'SOFT'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_severity AS ENUM (
        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE dependency_relationship_type AS ENUM (
        'REQUIRES', 'SUPPORTS', 'ASSIGNED_TO', 'LOCATED_AT', 'MOVES_VIA',
        'CONTAINS', 'DELIVERED_TO', 'RESERVED_FOR', 'REPLENISHED_BY',
        'AFFECTS', 'DEPENDS_ON', 'CONSTRAINED_BY', 'OPERATED_BY', 'OCCURS_AT', 'BELONGS_TO'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 3. CORE OPERATIONAL TABLES

-- 3.1 Expeditions Table
CREATE TABLE IF NOT EXISTS expeditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    season VARCHAR(50) NOT NULL,
    objective TEXT,
    planned_start_at TIMESTAMPTZ,
    planned_end_at TIMESTAMPTZ,
    status expedition_status NOT NULL DEFAULT 'DRAFT',
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    notes TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_expedition_dates CHECK (planned_end_at IS NULL OR planned_start_at IS NULL OR planned_end_at >= planned_start_at)
);

-- 3.2 Locations Table
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    parent_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    latitude NUMERIC(9,6) CHECK (latitude IS NULL OR (latitude >= -90.0 AND latitude <= 90.0)),
    longitude NUMERIC(9,6) CHECK (longitude IS NULL OR (longitude >= -180.0 AND longitude <= 180.0)),
    status location_status NOT NULL DEFAULT 'AVAILABLE',
    description TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3.3 Missions Table
CREATE TABLE IF NOT EXISTS missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    required_by_at TIMESTAMPTZ,
    status mission_status NOT NULL DEFAULT 'PROPOSED',
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_mission_expedition_code UNIQUE (expedition_id, code)
);

-- 3.4 Teams Table (Forward reference to people.id resolved after people creation)
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    leader_person_id UUID,
    mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    status team_status NOT NULL DEFAULT 'FORMING',
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3.5 People Table
CREATE TABLE IF NOT EXISTS people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_code VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    organization VARCHAR(150),
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    readiness_state person_readiness NOT NULL DEFAULT 'NOMINATED',
    movement_state person_movement NOT NULL DEFAULT 'NOT_DEPLOYED',
    current_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    last_confirmed_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    emergency_status VARCHAR(100),
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Attach foreign key from teams to people now that people table exists
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_teams_leader'
    ) THEN
        ALTER TABLE teams ADD CONSTRAINT fk_teams_leader
        FOREIGN KEY (leader_person_id) REFERENCES people(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 3.6 Assignments Table
CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    subject_type VARCHAR(50) NOT NULL CHECK (subject_type IN ('PERSON', 'ASSET', 'INVENTORY', 'CARGO')),
    subject_id UUID NOT NULL,
    role VARCHAR(100),
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    status assignment_status NOT NULL DEFAULT 'PROPOSED',
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_assignment_dates CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at)
);

-- 4. LOGISTICS & SUPPLY CHAIN TABLES

-- 4.1 Cargo Consignments Table
CREATE TABLE IF NOT EXISTS cargo_consignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    origin_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    destination_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    required_by_at TIMESTAMPTZ NOT NULL,
    estimated_arrival_at TIMESTAMPTZ,
    transport_plan_summary TEXT,
    compliance_status document_status NOT NULL DEFAULT 'REQUIRED',
    status cargo_status NOT NULL DEFAULT 'REQUESTED',
    handling_classification VARCHAR(100),
    exception_reason TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4.2 Transport Legs Table
CREATE TABLE IF NOT EXISTS transport_legs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    mode VARCHAR(50) NOT NULL,
    origin_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    destination_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    departure_window_open TIMESTAMPTZ,
    departure_window_close TIMESTAMPTZ,
    arrival_window_open TIMESTAMPTZ,
    arrival_window_close TIMESTAMPTZ,
    planned_departure_at TIMESTAMPTZ,
    planned_arrival_at TIMESTAMPTZ,
    estimated_departure_at TIMESTAMPTZ,
    estimated_arrival_at TIMESTAMPTZ,
    capacity NUMERIC(12,2) CHECK (capacity IS NULL OR capacity >= 0),
    capacity_unit VARCHAR(50),
    status transport_status NOT NULL DEFAULT 'PLANNED',
    delay_reason TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_transport_departure_window CHECK (departure_window_close IS NULL OR departure_window_open IS NULL OR departure_window_close >= departure_window_open),
    CONSTRAINT chk_transport_arrival_window CHECK (arrival_window_close IS NULL OR arrival_window_open IS NULL OR arrival_window_close >= arrival_window_open),
    CONSTRAINT chk_transport_arrival_after_departure CHECK (arrival_window_open IS NULL OR departure_window_open IS NULL OR arrival_window_open >= departure_window_open),
    CONSTRAINT chk_transport_planned_dates CHECK (planned_arrival_at IS NULL OR planned_departure_at IS NULL OR planned_arrival_at >= planned_departure_at)
);

-- 4.3 Cargo Packages Table
CREATE TABLE IF NOT EXISTS cargo_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    consignment_id UUID NOT NULL REFERENCES cargo_consignments(id) ON DELETE CASCADE,
    contents_summary TEXT,
    quantity NUMERIC(12,2) NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    weight_kg NUMERIC(10,2) CHECK (weight_kg IS NULL OR weight_kg >= 0),
    length_cm NUMERIC(10,2) CHECK (length_cm IS NULL OR length_cm >= 0),
    width_cm NUMERIC(10,2) CHECK (width_cm IS NULL OR width_cm >= 0),
    height_cm NUMERIC(10,2) CHECK (height_cm IS NULL OR height_cm >= 0),
    handling_classification VARCHAR(100),
    current_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    current_transport_leg_id UUID REFERENCES transport_legs(id) ON DELETE SET NULL,
    condition VARCHAR(100) DEFAULT 'GOOD',
    status cargo_package_status NOT NULL DEFAULT 'PACKED',
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4.4 Transport Assignment Tables
CREATE TABLE IF NOT EXISTS transport_cargo_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transport_leg_id UUID NOT NULL REFERENCES transport_legs(id) ON DELETE CASCADE,
    cargo_consignment_id UUID NOT NULL REFERENCES cargo_consignments(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ,
    status assignment_status NOT NULL DEFAULT 'APPROVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transport_cargo UNIQUE (transport_leg_id, cargo_consignment_id)
);

CREATE TABLE IF NOT EXISTS transport_person_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transport_leg_id UUID NOT NULL REFERENCES transport_legs(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ,
    status assignment_status NOT NULL DEFAULT 'APPROVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transport_person UNIQUE (transport_leg_id, person_id)
);

-- 5. INVENTORY & FLEET ASSETS

-- 5.1 Inventory Items Catalog
CREATE TABLE IF NOT EXISTS inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_code VARCHAR(50) UNIQUE NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    criticality VARCHAR(50) NOT NULL DEFAULT 'STANDARD',
    description TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5.2 Assets Table (Forward references inventory_items for spares)
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    condition VARCHAR(100) DEFAULT 'OPERATIONAL',
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    custodian_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    assigned_mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    maintenance_state VARCHAR(50) DEFAULT 'SERVICEABLE',
    status asset_status NOT NULL DEFAULT 'AVAILABLE',
    required_spare_item_id UUID REFERENCES inventory_items(id) ON DELETE SET NULL,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5.3 Transport Asset Assignments Table
CREATE TABLE IF NOT EXISTS transport_asset_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transport_leg_id UUID NOT NULL REFERENCES transport_legs(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ,
    status assignment_status NOT NULL DEFAULT 'APPROVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_transport_asset UNIQUE (transport_leg_id, asset_id)
);

-- 5.4 Inventory Stock Lots Table
CREATE TABLE IF NOT EXISTS inventory_stock_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inventory_item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE RESTRICT,
    lot_code VARCHAR(50),
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    on_hand_quantity NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (on_hand_quantity >= 0),
    reserved_quantity NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    quarantined_quantity NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (quarantined_quantity >= 0),
    damaged_quantity NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (damaged_quantity >= 0),
    status inventory_status NOT NULL DEFAULT 'AVAILABLE',
    condition VARCHAR(100) DEFAULT 'GOOD',
    reorder_point NUMERIC(12,2) CHECK (reorder_point IS NULL OR reorder_point >= 0),
    replenishment_lead_days INTEGER CHECK (replenishment_lead_days IS NULL OR replenishment_lead_days >= 0),
    next_inbound_at TIMESTAMPTZ,
    dependent_asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    dependent_mission_id UUID REFERENCES missions(id) ON DELETE SET NULL,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_reserved_lte_on_hand CHECK (reserved_quantity <= on_hand_quantity),
    CONSTRAINT chk_total_unavailable_lte_on_hand CHECK (reserved_quantity + quarantined_quantity + damaged_quantity <= on_hand_quantity)
);

-- 5.5 Inventory Transactions Ledger
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_lot_id UUID NOT NULL REFERENCES inventory_stock_lots(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN (
        'RECEIPT', 'RESERVATION', 'RELEASE', 'ISSUE', 'TRANSFER_OUT',
        'TRANSFER_IN', 'DAMAGE', 'QUARANTINE', 'DISPOSE', 'RETURN'
    )),
    quantity NUMERIC(12,2) NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    performed_by_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5.6 Maintenance Records Table
CREATE TABLE IF NOT EXISTS maintenance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    maintenance_type VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
    required_spare_item_id UUID REFERENCES inventory_items(id) ON DELETE SET NULL,
    notes TEXT,
    performed_by VARCHAR(150),
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. COMPLIANCE, TIME WINDOWS & SEMANTIC INTELLIGENCE

-- 6.1 Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_code VARCHAR(50) UNIQUE NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    subject_type VARCHAR(50) NOT NULL,
    subject_id UUID NOT NULL,
    issued_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    status document_status NOT NULL DEFAULT 'REQUIRED',
    verifier VARCHAR(150),
    attachment_path TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6.2 Time Windows Table
CREATE TABLE IF NOT EXISTS time_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    open_at TIMESTAMPTZ NOT NULL,
    close_at TIMESTAMPTZ NOT NULL,
    hard_or_soft hard_soft_constraint NOT NULL DEFAULT 'HARD',
    subject_type VARCHAR(50) NOT NULL,
    subject_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    description TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_time_window_bounds CHECK (close_at > open_at)
);

-- 6.3 Semantic Dependencies Table
CREATE TABLE IF NOT EXISTS dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expedition_id UUID REFERENCES expeditions(id) ON DELETE CASCADE,
    relationship_type dependency_relationship_type NOT NULL,
    source_entity_type VARCHAR(50) NOT NULL,
    source_entity_id UUID NOT NULL,
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id UUID NOT NULL,
    criticality constraint_severity DEFAULT 'CRITICAL',
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6.4 Constraints Table
CREATE TABLE IF NOT EXISTS constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    severity constraint_severity NOT NULL DEFAULT 'CRITICAL',
    hard_or_soft hard_soft_constraint NOT NULL DEFAULT 'HARD',
    subject_type VARCHAR(50),
    subject_id UUID,
    rule_code VARCHAR(100) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6.5 Operational Events Table (Immutable Event Journal)
CREATE TABLE IF NOT EXISTS operational_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50),
    actor_id UUID,
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    evidence JSONB NOT NULL DEFAULT '{}',
    correlation_id UUID,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enforce Immutability on operational_events via trigger
CREATE OR REPLACE FUNCTION prevent_operational_event_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Operational events are immutable. Updates and deletions are strictly prohibited.';
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_operational_events_immutable'
    ) THEN
        CREATE TRIGGER trg_operational_events_immutable
        BEFORE UPDATE OR DELETE ON operational_events
        FOR EACH ROW EXECUTE FUNCTION prevent_operational_event_modification();
    END IF;
END $$;

-- 7. EMERGENCY INCIDENTS & RESPONSE ACTIONS

-- 7.1 Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_code VARCHAR(50) UNIQUE NOT NULL,
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    type VARCHAR(100) NOT NULL,
    severity incident_severity NOT NULL DEFAULT 'MEDIUM',
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    declared_at TIMESTAMPTZ,
    commander_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    status incident_status NOT NULL DEFAULT 'DETECTED',
    description TEXT,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.2 Incident Join Tables
CREATE TABLE IF NOT EXISTS incident_people (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role VARCHAR(100) DEFAULT 'RESPONDER',
    PRIMARY KEY (incident_id, person_id)
);

CREATE TABLE IF NOT EXISTS incident_assets (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    damage_state VARCHAR(100),
    PRIMARY KEY (incident_id, asset_id)
);

CREATE TABLE IF NOT EXISTS incident_missions (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    impact_status VARCHAR(100) DEFAULT 'BLOCKED',
    PRIMARY KEY (incident_id, mission_id)
);

CREATE TABLE IF NOT EXISTS incident_cargo (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    consignment_id UUID NOT NULL REFERENCES cargo_consignments(id) ON DELETE CASCADE,
    damage_state VARCHAR(100),
    PRIMARY KEY (incident_id, consignment_id)
);

-- 7.3 Response Actions Table
CREATE TABLE IF NOT EXISTS response_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    action_code VARCHAR(50),
    action_description TEXT NOT NULL,
    owner_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    due_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    completed_at TIMESTAMPTZ,
    result TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. REPLANNING, RECOMMENDATIONS & APPROVALS

-- 8.1 Replans Table
CREATE TABLE IF NOT EXISTS replans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    replan_code VARCHAR(50) UNIQUE NOT NULL,
    expedition_id UUID NOT NULL REFERENCES expeditions(id) ON DELETE RESTRICT,
    trigger_event_id UUID REFERENCES operational_events(id) ON DELETE SET NULL,
    trigger_reason TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'PROPOSED',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    data_provenance data_provenance NOT NULL DEFAULT 'SYNTHETIC_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8.2 Recommendations Table
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    replan_id UUID NOT NULL REFERENCES replans(id) ON DELETE CASCADE,
    trigger_event_id UUID REFERENCES operational_events(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    affected_entities JSONB NOT NULL DEFAULT '[]',
    violated_constraints JSONB NOT NULL DEFAULT '[]',
    proposed_changes JSONB NOT NULL DEFAULT '[]',
    expected_impact JSONB NOT NULL DEFAULT '{}',
    assumptions JSONB NOT NULL DEFAULT '[]',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approval_state recommendation_status NOT NULL DEFAULT 'PROPOSED',
    data_provenance data_provenance NOT NULL DEFAULT 'ADVISORY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8.3 Recommendation Alternatives Table
CREATE TABLE IF NOT EXISTS recommendation_alternatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    option_code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    proposed_changes JSONB NOT NULL DEFAULT '[]',
    impact JSONB NOT NULL DEFAULT '{}',
    tradeoffs JSONB NOT NULL DEFAULT '{}',
    assumptions JSONB NOT NULL DEFAULT '[]',
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8.4 Approvals Table
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE RESTRICT,
    approver_user_id UUID,
    approver_person_id UUID NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
    approver_role VARCHAR(100),
    decision approval_decision NOT NULL,
    comment TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resulting_event_id UUID REFERENCES operational_events(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. AUDIT & OFFLINE RESILIENCE

-- 9.1 Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID,
    actor_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    before_snapshot JSONB,
    after_snapshot JSONB,
    correlation_id UUID,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9.2 Sync Queue Table
CREATE TABLE IF NOT EXISTS sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES operational_events(id) ON DELETE SET NULL,
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('P0', 'P1', 'P2', 'P3')) DEFAULT 'P1',
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    last_attempt_at TIMESTAMPTZ,
    ack_at TIMESTAMPTZ,
    error_message TEXT
);

-- 9.3 Sync Conflicts Table
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES operational_events(id) ON DELETE SET NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    local_payload JSONB NOT NULL,
    server_payload JSONB NOT NULL,
    conflict_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'UNRESOLVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolution JSONB
);

-- 10. INDEXES

-- Expeditions
CREATE INDEX IF NOT EXISTS idx_expeditions_status ON expeditions (status);

-- Missions
CREATE INDEX IF NOT EXISTS idx_missions_expedition_id ON missions (expedition_id);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (status);
CREATE INDEX IF NOT EXISTS idx_missions_required_by_at ON missions (required_by_at);
CREATE INDEX IF NOT EXISTS idx_missions_location_id ON missions (location_id);

-- People
CREATE INDEX IF NOT EXISTS idx_people_expedition_id ON people (expedition_id);
CREATE INDEX IF NOT EXISTS idx_people_team_id ON people (team_id);
CREATE INDEX IF NOT EXISTS idx_people_readiness_state ON people (readiness_state);
CREATE INDEX IF NOT EXISTS idx_people_movement_state ON people (movement_state);
CREATE INDEX IF NOT EXISTS idx_people_current_location ON people (current_location_id);

-- Teams
CREATE INDEX IF NOT EXISTS idx_teams_expedition_id ON teams (expedition_id);
CREATE INDEX IF NOT EXISTS idx_teams_mission_id ON teams (mission_id);
CREATE INDEX IF NOT EXISTS idx_teams_status ON teams (status);

-- Cargo
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_expedition ON cargo_consignments (expedition_id);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_status ON cargo_consignments (status);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_required_by ON cargo_consignments (required_by_at);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_eta ON cargo_consignments (estimated_arrival_at);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_origin ON cargo_consignments (origin_location_id);
CREATE INDEX IF NOT EXISTS idx_cargo_consignments_dest ON cargo_consignments (destination_location_id);

-- Cargo Packages
CREATE INDEX IF NOT EXISTS idx_cargo_packages_consignment ON cargo_packages (consignment_id);
CREATE INDEX IF NOT EXISTS idx_cargo_packages_location ON cargo_packages (current_location_id);
CREATE INDEX IF NOT EXISTS idx_cargo_packages_transport_leg ON cargo_packages (current_transport_leg_id);
CREATE INDEX IF NOT EXISTS idx_cargo_packages_status ON cargo_packages (status);

-- Transport
CREATE INDEX IF NOT EXISTS idx_transport_legs_expedition ON transport_legs (expedition_id);
CREATE INDEX IF NOT EXISTS idx_transport_legs_status ON transport_legs (status);
CREATE INDEX IF NOT EXISTS idx_transport_legs_planned_dep ON transport_legs (planned_departure_at);
CREATE INDEX IF NOT EXISTS idx_transport_legs_planned_arr ON transport_legs (planned_arrival_at);
CREATE INDEX IF NOT EXISTS idx_transport_legs_estimated_arr ON transport_legs (estimated_arrival_at);
CREATE INDEX IF NOT EXISTS idx_transport_legs_origin ON transport_legs (origin_location_id);
CREATE INDEX IF NOT EXISTS idx_transport_legs_dest ON transport_legs (destination_location_id);

-- Inventory
CREATE INDEX IF NOT EXISTS idx_stock_lots_item ON inventory_stock_lots (inventory_item_id);
CREATE INDEX IF NOT EXISTS idx_stock_lots_location ON inventory_stock_lots (location_id);
CREATE INDEX IF NOT EXISTS idx_stock_lots_status ON inventory_stock_lots (status);
CREATE INDEX IF NOT EXISTS idx_stock_lots_dep_asset ON inventory_stock_lots (dependent_asset_id);
CREATE INDEX IF NOT EXISTS idx_stock_lots_dep_mission ON inventory_stock_lots (dependent_mission_id);
CREATE INDEX IF NOT EXISTS idx_stock_lots_inbound ON inventory_stock_lots (next_inbound_at);

-- Assets
CREATE INDEX IF NOT EXISTS idx_assets_location ON assets (location_id);
CREATE INDEX IF NOT EXISTS idx_assets_assigned_mission ON assets (assigned_mission_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets (status);
CREATE INDEX IF NOT EXISTS idx_assets_maint_state ON assets (maintenance_state);
CREATE INDEX IF NOT EXISTS idx_assets_spare_item ON assets (required_spare_item_id);

-- Events
CREATE INDEX IF NOT EXISTS idx_events_entity ON operational_events (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON operational_events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON operational_events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON operational_events (correlation_id);

-- Dependencies
CREATE INDEX IF NOT EXISTS idx_dep_source ON dependencies (source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_dep_target ON dependencies (target_entity_type, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_dep_relationship_type ON dependencies (relationship_type);
CREATE INDEX IF NOT EXISTS idx_dep_expedition_id ON dependencies (expedition_id);

-- Constraints
CREATE INDEX IF NOT EXISTS idx_constraints_subject ON constraints (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_constraints_active ON constraints (active);
CREATE INDEX IF NOT EXISTS idx_constraints_rule_code ON constraints (rule_code);

-- Recommendations & Replans
CREATE INDEX IF NOT EXISTS idx_recommendations_replan ON recommendations (replan_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_approval ON recommendations (approval_state);

-- Incidents
CREATE INDEX IF NOT EXISTS idx_incidents_expedition ON incidents (expedition_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_location ON incidents (location_id);

-- Time Windows
CREATE INDEX IF NOT EXISTS idx_time_windows_subject ON time_windows (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_time_windows_dates ON time_windows (open_at, close_at);
