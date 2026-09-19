"""
Deterministic Benchmark Scenario Injection Service (A6).

Provides repeatable, auditable disruption injection for the three approved A6 benchmark scenarios:
1. FLIGHT_GROUNDING: Grounding/delay of active polar air transport leg due to adverse blizzard.
2. GENERATOR_FAILURE: Critical mechanical failure of expedition primary diesel generator.
3. COLD_CHAIN_EXCURSION: Refrigerated cargo hold/quarantine due to storage temperature excursion.

Guarantees & Constitutional Invariants:
- Pure public service invocations (TransportService, AssetService, CargoService); zero Track B internal modifications.
- Dynamic entity resolution strictly scoped to expedition; zero hardcoded entity IDs.
- Deterministic documented selection rules when matching candidates exist.
- Strict DomainValidationError when zero semantic matching targets exist (zero unsafe fallbacks).
- Strict expedition isolation: expedition_id is mandatory; never falls back to global/unrelated entities.
- Safe idempotency on repeated injection.
- Strict non-autonomous rule: zero autonomous replanning or recommendation generation.
- All events and mutations tagged with data_provenance: SYNTHETIC_DEMO.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from backend.app.domains.control_tower.schemas import (
    ScenarioInjectRequest,
    ScenarioInjectResult,
)
from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.missions.models import MissionModel
from backend.app.services.dependencies.models import DependencyModel
from backend.app.domains.transport.models import TransportLegModel
from backend.app.domains.transport.service import TransportService
from backend.app.domains.transport.schemas import TransportLegDelayRequest, TransportLegUpdate
from backend.app.domains.assets.models import AssetModel
from backend.app.domains.assets.service import AssetService
from backend.app.domains.assets.schemas import AssetStatusTransitionRequest, AssetUpdate
from backend.app.domains.assets.states import AssetStatus, AssetCondition
from backend.app.domains.cargo.models import CargoConsignmentModel
from backend.app.domains.cargo.service import CargoService
from backend.app.domains.cargo.schemas import CargoConsignmentUpdate
from backend.app.shared.types.states import CargoStatus, TransportStatus
from backend.app.platform.events.models import OperationalEventModel
from backend.app.core.errors import DomainValidationError


def _resolve_expedition_id(session: Session, requested_exp_id: Optional[uuid.UUID]) -> uuid.UUID:
    """Validates target expedition: expedition_id is strictly required for tenant isolation."""
    if not requested_exp_id:
        raise DomainValidationError(
            message="expedition_id is strictly required for scenario injection. Global or fallback injection is prohibited.",
            field="expedition_id",
        )
    exp = session.get(ExpeditionModel, requested_exp_id)
    if not exp:
        raise DomainValidationError(f"Target expedition '{requested_exp_id}' not found.")
    return exp.id


def _get_latest_event_id(session: Session, entity_type: str, entity_id: uuid.UUID) -> Optional[uuid.UUID]:
    """Finds the most recent event ID emitted for a specific entity."""
    stmt = (
        select(OperationalEventModel.event_id)
        .where(
            OperationalEventModel.entity_type == entity_type.upper(),
            OperationalEventModel.entity_id == entity_id,
        )
        .order_by(OperationalEventModel.occurred_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


class ScenarioInjectionService:
    """Executes deterministic benchmark disruption scenarios against expedition operational state."""

    def __init__(self, session: Session):
        self.session = session
        self.transport_service = TransportService(session)
        self.asset_service = AssetService(session)
        self.cargo_service = CargoService(session)

    def inject(self, request: ScenarioInjectRequest) -> ScenarioInjectResult:
        """Dispatches to the appropriate scenario runner based on scenario_key."""
        key = (request.scenario_key or "").strip().upper()
        expedition_id = _resolve_expedition_id(self.session, request.expedition_id)

        if key == "FLIGHT_GROUNDING":
            return self._inject_flight_grounding(expedition_id, request.requested_by)
        elif key == "GENERATOR_FAILURE":
            return self._inject_generator_failure(expedition_id, request.requested_by)
        elif key == "COLD_CHAIN_EXCURSION":
            return self._inject_cold_chain_excursion(expedition_id, request.requested_by)
        else:
            raise DomainValidationError(
                f"Unknown scenario_key '{request.scenario_key}'. Supported: FLIGHT_GROUNDING, GENERATOR_FAILURE, COLD_CHAIN_EXCURSION."
            )

    def _inject_flight_grounding(
        self, expedition_id: uuid.UUID, requested_by: Optional[uuid.UUID]
    ) -> ScenarioInjectResult:
        """
        Scenario 1: FLIGHT_GROUNDING.
        Dynamically locates active air transport leg in expedition and delays it +5 days.
        Deterministic selection rule: mode == AIR, status in active states,
        sorted by planned_departure_at ASC, code ASC.
        Zero fallback to non-AIR transport legs.
        """
        active_statuses = ["PLANNED", "BOOKED", "READY", "DEPARTED", "IN_TRANSIT"]

        stmt_air = (
            select(TransportLegModel)
            .where(
                TransportLegModel.expedition_id == expedition_id,
                TransportLegModel.status.in_(active_statuses),
                TransportLegModel.mode == "AIR",
            )
            .order_by(TransportLegModel.planned_departure_at.asc(), TransportLegModel.code.asc())
            .limit(1)
        )
        leg = self.session.execute(stmt_air).scalar_one_or_none()

        delay_reason = "Adverse polar weather: flight grounded due to severe blizzard and zero visibility."

        if not leg:
            # Check for already-grounded AIR leg for idempotency replay
            stmt_already = (
                select(TransportLegModel)
                .where(
                    TransportLegModel.expedition_id == expedition_id,
                    TransportLegModel.mode == "AIR",
                    TransportLegModel.status == "DELAYED",
                    TransportLegModel.delay_reason == delay_reason,
                )
                .order_by(TransportLegModel.planned_departure_at.asc(), TransportLegModel.code.asc())
                .limit(1)
            )
            already_leg = self.session.execute(stmt_already).scalar_one_or_none()
            if already_leg:
                event_id = _get_latest_event_id(self.session, "TRANSPORT_LEG", already_leg.id)
                return ScenarioInjectResult(
                    scenario_key="FLIGHT_GROUNDING",
                    summary=f"Transport leg {already_leg.code} is already grounded due to polar weather (idempotent replay).",
                    trigger_event_id=event_id,
                    affected_entity_type="TRANSPORT_LEG",
                    affected_entity_id=already_leg.id,
                    affected_entity_code=already_leg.code,
                    data_provenance="SYNTHETIC_DEMO",
                )
            raise DomainValidationError(
                f"FLIGHT_GROUNDING scenario failed: No active AIR transport legs found for expedition {expedition_id}."
            )

        if leg.status == "DELAYED" and leg.delay_reason == delay_reason:
            event_id = _get_latest_event_id(self.session, "TRANSPORT_LEG", leg.id)
            return ScenarioInjectResult(
                scenario_key="FLIGHT_GROUNDING",
                summary=f"Transport leg {leg.code} is already grounded due to polar weather (idempotent replay).",
                trigger_event_id=event_id,
                affected_entity_type="TRANSPORT_LEG",
                affected_entity_id=leg.id,
                affected_entity_code=leg.code,
                data_provenance="SYNTHETIC_DEMO",
            )

        now = datetime.now(timezone.utc)
        base_date = leg.estimated_arrival_at or leg.planned_arrival_at or now
        if base_date.tzinfo is None:
            base_date = base_date.replace(tzinfo=timezone.utc)
        new_eta = base_date + timedelta(days=5)

        delay_req = TransportLegDelayRequest(
            new_estimated_arrival_at=new_eta,
            delay_reason=delay_reason,
            operational_metadata={"scenario": "FLIGHT_GROUNDING", "blizzard_alert": "CAT_4"},
        )

        actor_context = {
            "actor_type": "OPERATOR" if requested_by else "SYSTEM",
            "actor_id": requested_by,
            "source": "SCENARIO_RUNNER",
        }

        if leg.status == "PLANNED":
            self.transport_service.update_transport_leg(
                leg_id=leg.id,
                data=TransportLegUpdate(status=TransportStatus.BOOKED),
                actor_context=actor_context,
            )

        self.transport_service.record_transport_delay(
            leg_id=leg.id,
            delay_data=delay_req,
            actor_context=actor_context,
        )

        event_id = _get_latest_event_id(self.session, "TRANSPORT_LEG", leg.id)

        return ScenarioInjectResult(
            scenario_key="FLIGHT_GROUNDING",
            summary=(
                f"Flight Grounding injected: Transport leg {leg.code} delayed +5 days to "
                f"{new_eta.strftime('%Y-%m-%d')} due to severe polar blizzard."
            ),
            trigger_event_id=event_id,
            affected_entity_type="TRANSPORT_LEG",
            affected_entity_id=leg.id,
            affected_entity_code=leg.code,
            data_provenance="SYNTHETIC_DEMO",
        )

    def _inject_generator_failure(
        self, expedition_id: uuid.UUID, requested_by: Optional[uuid.UUID]
    ) -> ScenarioInjectResult:
        """
        Scenario 2: GENERATOR_FAILURE.
        Dynamically locates an active power/generator asset legitimately associated with the expedition
        and transitions it via public AssetService contracts.
        Deterministic selection rule:
          - legitimately associated with expedition_id via assigned mission, mission location, or semantic dependency.
          - type or name matches generator/power.
          - status in AVAILABLE or IN_USE.
          - sorted by criticality DESC, asset_code ASC.
        Zero fallback to unrelated global assets or non-generator assets.
        Zero direct mutations on AssetModel from Track A.
        """
        active_statuses = [AssetStatus.AVAILABLE.value, AssetStatus.IN_USE.value]

        # Resolve legitimate domain associations with the expedition
        exp_missions_subq = select(MissionModel.id).where(MissionModel.expedition_id == expedition_id)
        exp_mission_locs_subq = select(MissionModel.location_id).where(
            MissionModel.expedition_id == expedition_id,
            MissionModel.location_id.isnot(None),
        )
        exp_dep_targets_subq = select(DependencyModel.target_entity_id).where(
            DependencyModel.expedition_id == expedition_id,
            DependencyModel.target_entity_type == "ASSET",
        )
        exp_dep_sources_subq = select(DependencyModel.source_entity_id).where(
            DependencyModel.expedition_id == expedition_id,
            DependencyModel.source_entity_type == "ASSET",
        )

        expedition_asset_clause = or_(
            AssetModel.assigned_mission_id.in_(exp_missions_subq),
            AssetModel.location_id.in_(exp_mission_locs_subq),
            AssetModel.id.in_(exp_dep_targets_subq),
            AssetModel.id.in_(exp_dep_sources_subq),
        )

        generator_semantic_clause = or_(
            AssetModel.type.ilike("%generator%"),
            AssetModel.type.ilike("%power%"),
            AssetModel.name.ilike("%generator%"),
        )

        stmt = (
            select(AssetModel)
            .where(
                AssetModel.status.in_(active_statuses),
                generator_semantic_clause,
                expedition_asset_clause,
            )
            .order_by(AssetModel.criticality.desc(), AssetModel.asset_code.asc())
            .limit(1)
        )
        asset = self.session.execute(stmt).scalar_one_or_none()

        reason = "Primary station diesel generator catastrophic mechanical failure: engine block seizure and coolant loss."

        if not asset:
            # Check for already-failed generator associated with this expedition for idempotency replay
            stmt_already = (
                select(AssetModel)
                .where(
                    AssetModel.status == AssetStatus.MAINTENANCE.value,
                    or_(
                        AssetModel.condition == AssetCondition.DAMAGED.value,
                        AssetModel.condition == AssetCondition.DEGRADED.value,
                    ),
                    generator_semantic_clause,
                    expedition_asset_clause,
                )
                .order_by(AssetModel.criticality.desc(), AssetModel.asset_code.asc())
                .limit(1)
            )
            already_asset = self.session.execute(stmt_already).scalar_one_or_none()
            if already_asset:
                event_id = _get_latest_event_id(self.session, "ASSET", already_asset.id)
                return ScenarioInjectResult(
                    scenario_key="GENERATOR_FAILURE",
                    summary=f"Asset {already_asset.asset_code} ({already_asset.name}) is already failed / in maintenance (idempotent replay).",
                    trigger_event_id=event_id,
                    affected_entity_type="ASSET",
                    affected_entity_id=already_asset.id,
                    affected_entity_code=already_asset.asset_code,
                    data_provenance="SYNTHETIC_DEMO",
                )
            raise DomainValidationError(
                f"GENERATOR_FAILURE scenario failed: No active generator/power assets found associated with expedition {expedition_id}."
            )

        if asset.status == AssetStatus.MAINTENANCE.value and asset.condition == AssetCondition.DAMAGED.value:
            event_id = _get_latest_event_id(self.session, "ASSET", asset.id)
            return ScenarioInjectResult(
                scenario_key="GENERATOR_FAILURE",
                summary=f"Asset {asset.asset_code} ({asset.name}) is already failed / in maintenance (idempotent replay).",
                trigger_event_id=event_id,
                affected_entity_type="ASSET",
                affected_entity_id=asset.id,
                affected_entity_code=asset.asset_code,
                data_provenance="SYNTHETIC_DEMO",
            )

        # 1. Update condition to DAMAGED via public AssetService.update_asset contract
        self.asset_service.update_asset(
            asset_id=asset.id,
            data=AssetUpdate(
                condition=AssetCondition.DAMAGED,
                operational_metadata={
                    "disruption": "GENERATOR_FAILURE",
                    "fault": "Catastrophic engine block seizure and coolant loss",
                    "provenance": "SYNTHETIC_DEMO",
                },
            ),
            actor_person_id=requested_by,
        )

        # 2. Transition status to MAINTENANCE via public AssetService.transition_asset_status contract
        self.asset_service.transition_asset_status(
            asset_id=asset.id,
            req=AssetStatusTransitionRequest(
                target_status=AssetStatus.MAINTENANCE,
                reason=reason,
            ),
            actor_person_id=requested_by,
        )

        event_id = _get_latest_event_id(self.session, "ASSET", asset.id)

        return ScenarioInjectResult(
            scenario_key="GENERATOR_FAILURE",
            summary=(
                f"Generator Failure injected: Asset {asset.asset_code} ({asset.name}) transitioned "
                f"to MAINTENANCE (DAMAGED) due to catastrophic engine seizure."
            ),
            trigger_event_id=event_id,
            affected_entity_type="ASSET",
            affected_entity_id=asset.id,
            affected_entity_code=asset.asset_code,
            data_provenance="SYNTHETIC_DEMO",
        )

    def _inject_cold_chain_excursion(
        self, expedition_id: uuid.UUID, requested_by: Optional[uuid.UUID]
    ) -> ScenarioInjectResult:
        """
        Scenario 3: COLD_CHAIN_EXCURSION.
        Dynamically locates active temperature-sensitive cargo in expedition and transitions it to HELD (quarantine).
        Deterministic selection rule: expedition_id matches, status in active states,
        handling_classification or description indicates temperature control, sorted by code ASC.
        Zero fallback to ordinary non-cold-chain cargo.
        """
        active_statuses = [
            CargoStatus.READY.value,
            CargoStatus.IN_TRANSIT.value,
            CargoStatus.DISPATCHED.value,
            CargoStatus.PACKED.value,
        ]

        cold_chain_clause = or_(
            CargoConsignmentModel.handling_classification.ilike("%cold%"),
            CargoConsignmentModel.handling_classification.ilike("%temp%"),
            CargoConsignmentModel.code.ilike("%cold%"),
            CargoConsignmentModel.transport_plan_summary.ilike("%cold%"),
        )

        stmt = (
            select(CargoConsignmentModel)
            .where(
                CargoConsignmentModel.expedition_id == expedition_id,
                CargoConsignmentModel.status.in_(active_statuses),
                cold_chain_clause,
            )
            .order_by(CargoConsignmentModel.code.asc())
            .limit(1)
        )
        consignment = self.session.execute(stmt).scalar_one_or_none()

        hold_reason = "Cold-chain temperature excursion logged: storage temp reached +8.2°C for 14 hours."

        if not consignment:
            # Check for already-quarantined cold-chain cargo for idempotency replay
            stmt_already = (
                select(CargoConsignmentModel)
                .where(
                    CargoConsignmentModel.expedition_id == expedition_id,
                    CargoConsignmentModel.status == CargoStatus.HELD.value,
                    cold_chain_clause,
                )
                .order_by(CargoConsignmentModel.code.asc())
                .limit(1)
            )
            already_consignment = self.session.execute(stmt_already).scalar_one_or_none()
            if already_consignment:
                event_id = _get_latest_event_id(self.session, "CARGO_CONSIGNMENT", already_consignment.id)
                return ScenarioInjectResult(
                    scenario_key="COLD_CHAIN_EXCURSION",
                    summary=f"Consignment {already_consignment.code} is already in quarantine hold (idempotent replay).",
                    trigger_event_id=event_id,
                    affected_entity_type="CARGO_CONSIGNMENT",
                    affected_entity_id=already_consignment.id,
                    affected_entity_code=already_consignment.code,
                    data_provenance="SYNTHETIC_DEMO",
                )
            raise DomainValidationError(
                f"COLD_CHAIN_EXCURSION scenario failed: No active cold-chain/temperature-controlled cargo consignments found for expedition {expedition_id}."
            )

        if (
            consignment.status == CargoStatus.HELD.value
            and consignment.exception_reason
            and "cold-chain" in consignment.exception_reason.lower()
        ):
            event_id = _get_latest_event_id(self.session, "CARGO_CONSIGNMENT", consignment.id)
            return ScenarioInjectResult(
                scenario_key="COLD_CHAIN_EXCURSION",
                summary=f"Consignment {consignment.code} is already in quarantine hold (idempotent replay).",
                trigger_event_id=event_id,
                affected_entity_type="CARGO_CONSIGNMENT",
                affected_entity_id=consignment.id,
                affected_entity_code=consignment.code,
                data_provenance="SYNTHETIC_DEMO",
            )

        update_data = CargoConsignmentUpdate(
            status=CargoStatus.HELD,
            exception_reason=hold_reason,
        )

        actor_context = {
            "actor_type": "OPERATOR" if requested_by else "SYSTEM",
            "actor_id": requested_by,
            "source": "SCENARIO_RUNNER",
        }

        self.cargo_service.update_consignment(
            consignment_id=consignment.id,
            data=update_data,
            actor_context=actor_context,
        )

        event_id = _get_latest_event_id(self.session, "CARGO_CONSIGNMENT", consignment.id)

        return ScenarioInjectResult(
            scenario_key="COLD_CHAIN_EXCURSION",
            summary=(
                f"Cold-Chain Excursion injected: Consignment {consignment.code} placed on quarantine "
                f"HELD status due to temperature breach (+8.2°C)."
            ),
            trigger_event_id=event_id,
            affected_entity_type="CARGO_CONSIGNMENT",
            affected_entity_id=consignment.id,
            affected_entity_code=consignment.code,
            data_provenance="SYNTHETIC_DEMO",
        )
