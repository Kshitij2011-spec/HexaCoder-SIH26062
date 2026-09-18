"""Personnel Application Service (Orchestrates Rules, Transactions, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.domains.people.models import PersonModel
from backend.app.domains.people.repository import PersonRepository
from backend.app.domains.people.schemas import (
    PersonCreate,
    PersonUpdate,
    PersonReadinessUpdate,
    PersonMovementUpdate,
)
from backend.app.domains.people.transitions import (
    validate_readiness_transition,
    validate_movement_transition,
)
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError, DomainValidationError


class PersonService:
    """Domain service managing expedition personnel lifecycle, qualifications, and movements."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = PersonRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_person(
        self,
        data: PersonCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> PersonModel:
        """Enrolls expedition personnel and emits an initial readiness operational event."""
        # Code uniqueness check
        existing = self.repository.get_by_code(data.person_code)
        if existing:
            raise ConflictError(
                f"Personnel with code '{data.person_code}' already exists.",
                field="person_code",
                details={"person_code": data.person_code}
            )

        # Validate expedition exists
        from backend.app.domains.expeditions.models import ExpeditionModel
        expedition = self.session.execute(
            select(ExpeditionModel).where(ExpeditionModel.id == data.expedition_id)
        ).scalar_one_or_none()
        if not expedition:
            raise EntityNotFoundError("Expedition", data.expedition_id)

        # If team_id is provided, validate team exists and belongs to same expedition
        if data.team_id:
            from backend.app.domains.teams.models import TeamModel
            team = self.session.execute(
                select(TeamModel).where(TeamModel.id == data.team_id)
            ).scalar_one_or_none()
            if not team:
                raise EntityNotFoundError("Team", data.team_id)
            if team.expedition_id != data.expedition_id:
                raise DomainValidationError(
                    f"Team '{team.team_code}' belongs to expedition {team.expedition_id}, not {data.expedition_id}",
                    field="team_id"
                )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = PersonModel(
            person_code=data.person_code,
            full_name=data.full_name,
            role=data.role,
            organization=data.organization,
            expedition_id=data.expedition_id,
            team_id=data.team_id,
            readiness_state=data.readiness_state.value,
            movement_state=data.movement_state.value,
            current_location_id=data.current_location_id,
            last_confirmed_location_id=data.last_confirmed_location_id,
            emergency_status=data.emergency_status,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            # Transactional event emission: PersonNominated
            self.event_service.append_event(
                event_type="PersonNominated",
                entity_type="PERSON",
                entity_id=created.id,
                new_state=created.readiness_state,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                evidence={
                    "person_code": created.person_code,
                    "full_name": created.full_name,
                    "role": created.role,
                    "expedition_id": str(created.expedition_id),
                },
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            # Transactional audit record
            self.audit_service.record_audit(
                action="CREATE_PERSON",
                entity_type="PERSON",
                entity_id=created.id,
                after_snapshot={
                    "person_code": created.person_code,
                    "full_name": created.full_name,
                    "role": created.role,
                    "readiness_state": created.readiness_state,
                    "movement_state": created.movement_state,
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_person(self, person_id: uuid.UUID) -> PersonModel:
        person = self.repository.get_by_id(person_id)
        if not person:
            raise EntityNotFoundError("Person", person_id)
        return person

    def list_people(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        readiness_state: Optional[str] = None,
        movement_state: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[PersonModel], int]:
        return self.repository.list_people(
            expedition_id=expedition_id,
            team_id=team_id,
            readiness_state=readiness_state,
            movement_state=movement_state,
            page=page,
            page_size=page_size
        )

    def update_person(
        self,
        person_id: uuid.UUID,
        data: PersonUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> PersonModel:
        """Updates personnel general info or triggers state transitions."""
        person = self.get_person(person_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "full_name": person.full_name,
            "role": person.role,
            "team_id": str(person.team_id) if person.team_id else None,
            "readiness_state": person.readiness_state,
            "movement_state": person.movement_state,
        }

        # If team_id is being modified, validate team compatibility
        if data.team_id is not None and data.team_id != person.team_id:
            from backend.app.domains.teams.models import TeamModel
            team = self.session.execute(
                select(TeamModel).where(TeamModel.id == data.team_id)
            ).scalar_one_or_none()
            if not team:
                raise EntityNotFoundError("Team", data.team_id)
            if team.expedition_id != person.expedition_id:
                raise DomainValidationError(
                    f"Team '{team.team_code}' belongs to expedition {team.expedition_id}, not {person.expedition_id}",
                    field="team_id"
                )
            person.team_id = data.team_id

        # Check readiness transition if provided
        readiness_event = None
        prev_readiness = person.readiness_state
        if data.readiness_state and data.readiness_state.value != person.readiness_state:
            readiness_event = validate_readiness_transition(person.readiness_state, data.readiness_state.value)
            person.readiness_state = data.readiness_state.value

        # Check movement transition if provided
        movement_event = None
        prev_movement = person.movement_state
        if data.movement_state and data.movement_state.value != person.movement_state:
            movement_event = validate_movement_transition(person.movement_state, data.movement_state.value)
            person.movement_state = data.movement_state.value

        # Update general fields
        if data.full_name is not None:
            person.full_name = data.full_name
        if data.role is not None:
            person.role = data.role
        if data.organization is not None:
            person.organization = data.organization
        if data.current_location_id is not None:
            person.current_location_id = data.current_location_id
        if data.last_confirmed_location_id is not None:
            person.last_confirmed_location_id = data.last_confirmed_location_id
        if data.emergency_status is not None:
            person.emergency_status = data.emergency_status

        person.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(person)

            # Emit readiness transition event if changed
            if readiness_event:
                self.event_service.append_event(
                    event_type=readiness_event,
                    entity_type="PERSON",
                    entity_id=updated.id,
                    new_state=updated.readiness_state,
                    previous_state=prev_readiness,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"transition_type": "READINESS"},
                    correlation_id=cid
                )

            # Emit movement transition event if changed
            if movement_event:
                self.event_service.append_event(
                    event_type=movement_event,
                    entity_type="PERSON",
                    entity_id=updated.id,
                    new_state=updated.movement_state,
                    previous_state=prev_movement,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    evidence={"transition_type": "MOVEMENT"},
                    correlation_id=cid
                )

            # Audit record
            self.audit_service.record_audit(
                action="UPDATE_PERSON",
                entity_type="PERSON",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "full_name": updated.full_name,
                    "role": updated.role,
                    "team_id": str(updated.team_id) if updated.team_id else None,
                    "readiness_state": updated.readiness_state,
                    "movement_state": updated.movement_state,
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def update_readiness(
        self,
        person_id: uuid.UUID,
        data: PersonReadinessUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> PersonModel:
        """Dedicated endpoint method for personnel qualification/readiness status change."""
        return self.update_person(
            person_id=person_id,
            data=PersonUpdate(readiness_state=data.readiness_state),
            correlation_id=correlation_id,
            actor_context=actor_context
        )

    def update_movement(
        self,
        person_id: uuid.UUID,
        data: PersonMovementUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> PersonModel:
        """Dedicated endpoint method for personnel movement / deployment status change."""
        return self.update_person(
            person_id=person_id,
            data=PersonUpdate(
                movement_state=data.movement_state,
                current_location_id=data.current_location_id
            ),
            correlation_id=correlation_id,
            actor_context=actor_context
        )
