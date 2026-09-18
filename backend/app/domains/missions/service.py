"""Mission Application Service."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.missions.repository import MissionRepository
from backend.app.domains.missions.schemas import (
    MissionCreate,
    MissionUpdate,
    MissionRelationshipRead,
)
from backend.app.domains.missions.transitions import validate_mission_transition
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError


class MissionService:
    """Domain service managing the lifecycle, dependencies, and execution state of polar missions."""
    def __init__(self, session: Session):
        self.session = session
        self.repository = MissionRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_mission(
        self,
        data: MissionCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> MissionModel:
        """Creates a mission within an expedition and emits MissionProposed event."""
        existing = self.repository.get_by_code(data.expedition_id, data.code)
        if existing:
            raise ConflictError(
                f"A mission with code '{data.code}' already exists in expedition '{data.expedition_id}'.",
                field="code",
                details={"expedition_id": str(data.expedition_id), "code": data.code}
            )

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = MissionModel(
            expedition_id=data.expedition_id,
            code=data.code,
            title=data.title,
            description=data.description,
            type=data.type,
            priority=data.priority,
            location_id=data.location_id,
            required_by_at=data.required_by_at,
            status=data.status.value,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            self.event_service.append_event(
                event_type="MissionCreated",
                entity_type="MISSION",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=created.location_id,
                evidence={"code": created.code, "title": created.title, "priority": created.priority},
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            self.audit_service.record_audit(
                action="CREATE_MISSION",
                entity_type="MISSION",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "title": created.title,
                    "status": created.status,
                    "priority": created.priority,
                    "expedition_id": str(created.expedition_id)
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_mission(self, mission_id: uuid.UUID) -> MissionModel:
        mission = self.repository.get_by_id(mission_id)
        if not mission:
            raise EntityNotFoundError("Mission", mission_id)
        return mission

    def list_missions(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[MissionModel], int]:
        return self.repository.list_missions(
            expedition_id=expedition_id,
            status=status,
            priority=priority,
            page=page,
            page_size=page_size
        )

    def update_mission(
        self,
        mission_id: uuid.UUID,
        data: MissionUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> MissionModel:
        """Updates mission details or validates and applies a lifecycle state transition."""
        mission = self.get_mission(mission_id)
        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "title": mission.title,
            "status": mission.status,
            "priority": mission.priority,
            "type": mission.type,
            "required_by_at": mission.required_by_at.isoformat() if mission.required_by_at else None,
        }

        event_type_to_emit = None
        previous_status = mission.status

        if data.status and data.status.value != mission.status:
            event_type_to_emit = validate_mission_transition(mission.status, data.status.value)
            mission.status = data.status.value

        if data.title is not None:
            mission.title = data.title
        if data.description is not None:
            mission.description = data.description
        if data.type is not None:
            mission.type = data.type
        if data.priority is not None:
            mission.priority = data.priority
        if data.location_id is not None:
            mission.location_id = data.location_id
        if data.required_by_at is not None:
            mission.required_by_at = data.required_by_at

        mission.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(mission)

            if event_type_to_emit:
                self.event_service.append_event(
                    event_type=event_type_to_emit,
                    entity_type="MISSION",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_status,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    location_id=updated.location_id,
                    evidence={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_MISSION",
                entity_type="MISSION",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "title": updated.title,
                    "status": updated.status,
                    "priority": updated.priority,
                    "type": updated.type,
                    "required_by_at": updated.required_by_at.isoformat() if updated.required_by_at else None,
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def get_relationships(self, mission_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves semantic relationships from graph for this mission."""
        self.get_mission(mission_id)
        return self.repository.get_relationships(mission_id)

    def get_time_windows(self, mission_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retrieves time windows associated with this mission."""
        self.get_mission(mission_id)
        return self.repository.get_time_windows(mission_id)
