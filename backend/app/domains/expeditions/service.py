"""Expedition Application Service (Orchestrates Rules, Transactions, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.expeditions.repository import ExpeditionRepository
from backend.app.domains.expeditions.schemas import (
    ExpeditionCreate,
    ExpeditionUpdate,
    ExpeditionSummary,
    ExpeditionRead,
)
from backend.app.domains.expeditions.transitions import validate_expedition_transition
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError


class ExpeditionService:
    """Domain service managing the lifecycle of Antarctic and polar expeditions."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = ExpeditionRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_expedition(
        self,
        data: ExpeditionCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> ExpeditionModel:
        """Creates an expedition and emits an ExpeditionCreated operational event."""
        # Check code uniqueness
        existing = self.repository.get_by_code(data.code)
        if existing:
            raise ConflictError(
                f"An expedition with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = ExpeditionModel(
            code=data.code,
            name=data.name,
            season=data.season,
            objective=data.objective,
            planned_start_at=data.planned_start_at,
            planned_end_at=data.planned_end_at,
            status=data.status.value,
            priority=data.priority,
            notes=data.notes,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            # Transactional event emission
            self.event_service.append_event(
                event_type="ExpeditionCreated",
                entity_type="EXPEDITION",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={"code": created.code, "name": created.name, "season": created.season},
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            # Transactional audit record
            self.audit_service.record_audit(
                action="CREATE_EXPEDITION",
                entity_type="EXPEDITION",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "name": created.name,
                    "status": created.status,
                    "season": created.season
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_expedition(self, expedition_id: uuid.UUID) -> ExpeditionModel:
        expedition = self.repository.get_by_id(expedition_id)
        if not expedition:
            raise EntityNotFoundError("Expedition", expedition_id)
        return expedition

    def list_expeditions(
        self,
        status: Optional[str] = None,
        season: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ExpeditionModel], int]:
        return self.repository.list_expeditions(status=status, season=season, page=page, page_size=page_size)

    def update_expedition(
        self,
        expedition_id: uuid.UUID,
        data: ExpeditionUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> ExpeditionModel:
        """Updates expedition attributes or transitions lifecycle status."""
        expedition = self.get_expedition(expedition_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "name": expedition.name,
            "status": expedition.status,
            "priority": expedition.priority,
            "planned_start_at": expedition.planned_start_at.isoformat() if expedition.planned_start_at else None,
            "planned_end_at": expedition.planned_end_at.isoformat() if expedition.planned_end_at else None,
        }

        event_type_to_emit = None
        previous_status = expedition.status

        # Validate lifecycle transition if requested
        if data.status and data.status.value != expedition.status:
            event_type_to_emit = validate_expedition_transition(expedition.status, data.status.value)
            expedition.status = data.status.value

        # Apply attribute modifications
        if data.name is not None:
            expedition.name = data.name
        if data.objective is not None:
            expedition.objective = data.objective
        if data.planned_start_at is not None:
            expedition.planned_start_at = data.planned_start_at
        if data.planned_end_at is not None:
            expedition.planned_end_at = data.planned_end_at
        if data.priority is not None:
            expedition.priority = data.priority
        if data.notes is not None:
            expedition.notes = data.notes

        expedition.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(expedition)

            # If status changed, emit corresponding domain lifecycle event
            if event_type_to_emit:
                self.event_service.append_event(
                    event_type=event_type_to_emit,
                    entity_type="EXPEDITION",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
                    correlation_id=cid
                )

            # Audit record
            self.audit_service.record_audit(
                action="UPDATE_EXPEDITION",
                entity_type="EXPEDITION",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "name": updated.name,
                    "status": updated.status,
                    "priority": updated.priority,
                    "planned_start_at": updated.planned_start_at.isoformat() if updated.planned_start_at else None,
                    "planned_end_at": updated.planned_end_at.isoformat() if updated.planned_end_at else None,
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def get_summary(self, expedition_id: uuid.UUID) -> ExpeditionSummary:
        """Assembles real operational metrics for an expedition without fake scores."""
        expedition = self.get_expedition(expedition_id)

        # Import domain models locally to prevent circular dependencies
        from backend.app.domains.missions.models import MissionModel
        from backend.app.domains.teams.models import TeamModel
        from backend.app.domains.people.models import PersonModel
        from backend.app.domains.time_windows.models import TimeWindowModel
        from backend.app.platform.events.models import OperationalEventModel

        # Real mission counts
        m_count = self.session.execute(
            select(func.count(MissionModel.id)).where(MissionModel.expedition_id == expedition_id)
        ).scalar() or 0

        active_m_count = self.session.execute(
            select(func.count(MissionModel.id)).where(
                MissionModel.expedition_id == expedition_id,
                MissionModel.status.in_(["IN_PROGRESS", "SCHEDULED", "READY"])
            )
        ).scalar() or 0

        # Real team counts
        t_count = self.session.execute(
            select(func.count(TeamModel.id)).where(TeamModel.expedition_id == expedition_id)
        ).scalar() or 0

        # Real personnel counts
        p_count = self.session.execute(
            select(func.count(PersonModel.id)).where(PersonModel.expedition_id == expedition_id)
        ).scalar() or 0

        # Real time windows count
        tw_count = self.session.execute(
            select(func.count(TimeWindowModel.id)).where(
                TimeWindowModel.subject_type == "EXPEDITION",
                TimeWindowModel.subject_id == expedition_id
            )
        ).scalar() or 0

        # Active events count
        evt_count = self.session.execute(
            select(func.count(OperationalEventModel.id)).where(
                OperationalEventModel.entity_type == "EXPEDITION",
                OperationalEventModel.entity_id == expedition_id
            )
        ).scalar() or 0

        return ExpeditionSummary(
            expedition=ExpeditionRead.model_validate(expedition),
            mission_count=m_count,
            active_mission_count=active_m_count,
            team_count=t_count,
            personnel_count=p_count,
            active_events_count=evt_count,
            time_windows_count=tw_count,
            exception_states={
                "is_on_hold": expedition.status == "ON_HOLD",
                "is_archived": expedition.status == "ARCHIVED"
            }
        )
