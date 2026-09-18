"""Teams Application Service (Orchestrates Rules, Invariants, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.teams.repository import TeamRepository
from backend.app.domains.teams.schemas import TeamCreate, TeamUpdate
from backend.app.domains.teams.transitions import validate_team_transition
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError, DomainValidationError


class TeamService:
    """Domain service managing functional expedition teams and enforcing expedition integrity."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = TeamRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_team(
        self,
        data: TeamCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TeamModel:
        """Creates a functional expedition team and emits a TeamCreated operational event."""
        # Code uniqueness check
        existing = self.repository.get_by_code(data.code)
        if existing:
            raise ConflictError(
                f"Team with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        # Invariant 1: Team must belong to a valid expedition
        from backend.app.domains.expeditions.models import ExpeditionModel
        expedition = self.session.execute(
            select(ExpeditionModel).where(ExpeditionModel.id == data.expedition_id)
        ).scalar_one_or_none()
        if not expedition:
            raise EntityNotFoundError("Expedition", data.expedition_id)

        # Invariant 2: Team leader must belong to the same expedition
        if data.leader_person_id:
            from backend.app.domains.people.models import PersonModel
            leader = self.session.execute(
                select(PersonModel).where(PersonModel.id == data.leader_person_id)
            ).scalar_one_or_none()
            if not leader:
                raise EntityNotFoundError("Person", data.leader_person_id)
            if leader.expedition_id != data.expedition_id:
                raise DomainValidationError(
                    f"Team leader '{leader.person_code}' belongs to expedition {leader.expedition_id}, not {data.expedition_id}",
                    field="leader_person_id"
                )

        # Invariant 3: Mission assignment must belong to the same expedition
        if data.mission_id:
            from backend.app.domains.missions.models import MissionModel
            mission = self.session.execute(
                select(MissionModel).where(MissionModel.id == data.mission_id)
            ).scalar_one_or_none()
            if not mission:
                raise EntityNotFoundError("Mission", data.mission_id)
            if mission.expedition_id != data.expedition_id:
                raise DomainValidationError(
                    f"Assigned mission '{mission.code}' belongs to expedition {mission.expedition_id}, not {data.expedition_id}",
                    field="mission_id"
                )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = TeamModel(
            code=data.code,
            name=data.name,
            expedition_id=data.expedition_id,
            leader_person_id=data.leader_person_id,
            mission_id=data.mission_id,
            location_id=data.location_id,
            status=data.status.value,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            # Transactional event emission
            self.event_service.append_event(
                event_type="TeamCreated",
                entity_type="TEAM",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={
                    "code": created.code,
                    "name": created.name,
                    "expedition_id": str(created.expedition_id),
                },
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            # Transactional audit record
            self.audit_service.record_audit(
                action="CREATE_TEAM",
                entity_type="TEAM",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "name": created.name,
                    "status": created.status,
                    "expedition_id": str(created.expedition_id),
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_team(self, team_id: uuid.UUID) -> TeamModel:
        team = self.repository.get_by_id(team_id)
        if not team:
            raise EntityNotFoundError("Team", team_id)
        return team

    def list_teams(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TeamModel], int]:
        return self.repository.list_teams(
            expedition_id=expedition_id,
            status=status,
            page=page,
            page_size=page_size
        )

    def update_team(
        self,
        team_id: uuid.UUID,
        data: TeamUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> TeamModel:
        """Updates team attributes and validates lifecycle state changes."""
        team = self.get_team(team_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "name": team.name,
            "status": team.status,
            "leader_person_id": str(team.leader_person_id) if team.leader_person_id else None,
            "mission_id": str(team.mission_id) if team.mission_id else None,
        }

        # Check leader change
        if data.leader_person_id is not None and data.leader_person_id != team.leader_person_id:
            from backend.app.domains.people.models import PersonModel
            leader = self.session.execute(
                select(PersonModel).where(PersonModel.id == data.leader_person_id)
            ).scalar_one_or_none()
            if not leader:
                raise EntityNotFoundError("Person", data.leader_person_id)
            if leader.expedition_id != team.expedition_id:
                raise DomainValidationError(
                    f"Team leader '{leader.person_code}' belongs to expedition {leader.expedition_id}, not {team.expedition_id}",
                    field="leader_person_id"
                )
            team.leader_person_id = data.leader_person_id

        # Check mission change
        if data.mission_id is not None and data.mission_id != team.mission_id:
            from backend.app.domains.missions.models import MissionModel
            mission = self.session.execute(
                select(MissionModel).where(MissionModel.id == data.mission_id)
            ).scalar_one_or_none()
            if not mission:
                raise EntityNotFoundError("Mission", data.mission_id)
            if mission.expedition_id != team.expedition_id:
                raise DomainValidationError(
                    f"Assigned mission '{mission.code}' belongs to expedition {mission.expedition_id}, not {team.expedition_id}",
                    field="mission_id"
                )
            team.mission_id = data.mission_id

        # Check status transition
        event_type_to_emit = None
        prev_status = team.status
        if data.status and data.status.value != team.status:
            event_type_to_emit = validate_team_transition(team.status, data.status.value)
            team.status = data.status.value

        if data.name is not None:
            team.name = data.name
        if data.location_id is not None:
            team.location_id = data.location_id

        team.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(team)

            if event_type_to_emit:
                self.event_service.append_event(
                    event_type=event_type_to_emit,
                    entity_type="TEAM",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=prev_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"code": updated.code, "name": updated.name},
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_TEAM",
                entity_type="TEAM",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "name": updated.name,
                    "status": updated.status,
                    "leader_person_id": str(updated.leader_person_id) if updated.leader_person_id else None,
                    "mission_id": str(updated.mission_id) if updated.mission_id else None,
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def get_team_members(self, team_id: uuid.UUID):
        """Returns the personnel assigned to this team."""
        # Ensure team exists
        self.get_team(team_id)
        return self.repository.get_members(team_id)
