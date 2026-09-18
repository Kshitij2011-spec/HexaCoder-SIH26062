"""Location Application Service (Orchestrates Rules, Transactions, Events, Audit)."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.locations.repository import LocationRepository
from backend.app.domains.locations.schemas import (
    LocationCreate,
    LocationUpdate,
    LocationRead,
    LocationHierarchyRead,
)
from backend.app.domains.locations.transitions import validate_location_transition
from backend.app.platform.events.service import EventService
from backend.app.platform.audit.service import AuditService
from backend.app.core.errors import EntityNotFoundError, ConflictError, DomainValidationError


class LocationService:
    """Domain service managing polar expedition and logistics locations."""

    def __init__(self, session: Session):
        self.session = session
        self.repository = LocationRepository(session)
        self.event_service = EventService(session)
        self.audit_service = AuditService(session)

    def create_location(
        self,
        data: LocationCreate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> LocationModel:
        """Creates a location and transactionally emits an immutable LocationCreated event and audit log."""
        existing = self.repository.get_by_code(data.code)
        if existing:
            raise ConflictError(
                f"A location with code '{data.code}' already exists.",
                field="code",
                details={"code": data.code}
            )

        if data.parent_location_id:
            parent = self.repository.get_by_id(data.parent_location_id)
            if not parent:
                raise EntityNotFoundError("Location", data.parent_location_id, details={"field": "parent_location_id"})

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        model = LocationModel(
            code=data.code,
            name=data.name,
            type=data.type,
            parent_location_id=data.parent_location_id,
            latitude=data.latitude,
            longitude=data.longitude,
            status=data.status.value,
            description=data.description,
            data_provenance=data.data_provenance.value,
        )

        with self.session.begin_nested():
            created = self.repository.create(model)

            self.event_service.append_event(
                event_type="LocationCreated",
                entity_type="LOCATION",
                entity_id=created.id,
                new_state=created.status,
                previous_state=None,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=created.id,
                evidence={"code": created.code, "name": created.name, "type": created.type},
                correlation_id=cid,
                data_provenance=data.data_provenance
            )

            self.audit_service.record_audit(
                action="CREATE_LOCATION",
                entity_type="LOCATION",
                entity_id=created.id,
                after_snapshot={
                    "code": created.code,
                    "name": created.name,
                    "type": created.type,
                    "status": created.status,
                    "parent_location_id": str(created.parent_location_id) if created.parent_location_id else None
                },
                correlation_id=cid
            )

        self.session.commit()
        return created

    def get_location(self, location_id: uuid.UUID) -> LocationModel:
        loc = self.repository.get_by_id(location_id)
        if not loc:
            raise EntityNotFoundError("Location", location_id)
        return loc

    def list_locations(
        self,
        type_: Optional[str] = None,
        status: Optional[str] = None,
        parent_location_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LocationModel], int]:
        return self.repository.list_locations(
            type_=type_,
            status=status,
            parent_location_id=parent_location_id,
            page=page,
            page_size=page_size
        )

    def update_location_state(
        self,
        location_id: uuid.UUID,
        new_status: str,
        reason: Optional[str] = None,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> LocationModel:
        """Executes a validated operational state transition for a location."""
        loc = self.get_location(location_id)
        current_state = loc.status

        validate_location_transition(current_state, new_status)

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snap = {"status": current_state}
        loc.status = new_status
        loc.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(loc)

            self.event_service.append_event(
                event_type="LocationStateChanged",
                entity_type="LOCATION",
                entity_id=updated.id,
                new_state=new_status,
                previous_state=current_state,
                source=actor.get("source", "API"),
                actor_type=actor.get("actor_type", "SYSTEM"),
                actor_id=actor.get("actor_id"),
                location_id=updated.id,
                evidence={"reason": reason} if reason else {},
                correlation_id=cid
            )

            self.audit_service.record_audit(
                action="UPDATE_LOCATION_STATE",
                entity_type="LOCATION",
                entity_id=updated.id,
                before_snapshot=before_snap,
                after_snapshot={"status": new_status, "reason": reason},
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def update_location(
        self,
        location_id: uuid.UUID,
        data: LocationUpdate,
        correlation_id: Optional[uuid.UUID] = None,
        actor_context: Optional[Dict[str, Any]] = None
    ) -> LocationModel:
        """Updates attributes and optionally executes state transition."""
        loc = self.get_location(location_id)

        # Check self-parent cycle or ancestor cycle
        if data.parent_location_id:
            if data.parent_location_id == location_id:
                raise DomainValidationError("A location cannot be its own parent.", field="parent_location_id")
            # Verify parent exists
            parent = self.repository.get_by_id(data.parent_location_id)
            if not parent:
                raise EntityNotFoundError("Location", data.parent_location_id, details={"field": "parent_location_id"})
            # Check cycle upwards
            curr_ancestor_id = parent.parent_location_id
            visited = {location_id, data.parent_location_id}
            while curr_ancestor_id:
                if curr_ancestor_id == location_id:
                    raise DomainValidationError("Cyclic parent-child hierarchy detected.", field="parent_location_id")
                visited.add(curr_ancestor_id)
                ancestor = self.repository.get_by_id(curr_ancestor_id)
                curr_ancestor_id = ancestor.parent_location_id if ancestor else None

        actor = actor_context or {"actor_type": "SYSTEM", "actor_id": None, "source": "API"}
        cid = correlation_id or uuid.uuid4()

        before_snapshot = {
            "name": loc.name,
            "type": loc.type,
            "status": loc.status,
            "parent_location_id": str(loc.parent_location_id) if loc.parent_location_id else None
        }

        previous_state = loc.status
        status_changed = False
        if data.status and data.status.value != loc.status:
            validate_location_transition(loc.status, data.status.value)
            loc.status = data.status.value
            status_changed = True

        if data.name is not None:
            loc.name = data.name
        if data.type is not None:
            loc.type = data.type
        if data.parent_location_id is not None:
            loc.parent_location_id = data.parent_location_id
        if data.latitude is not None:
            loc.latitude = data.latitude
        if data.longitude is not None:
            loc.longitude = data.longitude
        if data.description is not None:
            loc.description = data.description

        loc.updated_at = datetime.now(timezone.utc)

        with self.session.begin_nested():
            updated = self.repository.update(loc)

            if status_changed:
                self.event_service.append_event(
                    event_type="LocationStateChanged",
                    entity_type="LOCATION",
                    entity_id=updated.id,
                    new_state=updated.status,
                    previous_state=previous_state,
                    source=actor.get("source", "API"),
                    actor_type=actor.get("actor_type", "SYSTEM"),
                    actor_id=actor.get("actor_id"),
                    location_id=updated.id,
                    evidence={"update_attributes": list(data.model_dump(exclude_unset=True).keys())},
                    correlation_id=cid
                )

            self.audit_service.record_audit(
                action="UPDATE_LOCATION",
                entity_type="LOCATION",
                entity_id=updated.id,
                before_snapshot=before_snapshot,
                after_snapshot={
                    "name": updated.name,
                    "type": updated.type,
                    "status": updated.status,
                    "parent_location_id": str(updated.parent_location_id) if updated.parent_location_id else None
                },
                correlation_id=cid
            )

        self.session.commit()
        return updated

    def get_hierarchy(self, location_id: uuid.UUID) -> LocationHierarchyRead:
        """Retrieves location along with ordered ancestors and immediate child locations."""
        loc = self.get_location(location_id)

        # Build ancestors list from parent upwards, then reverse for top-down order
        ancestors: List[LocationModel] = []
        curr_parent_id = loc.parent_location_id
        while curr_parent_id:
            parent = self.repository.get_by_id(curr_parent_id)
            if not parent or parent.id in [a.id for a in ancestors]:
                break
            ancestors.append(parent)
            curr_parent_id = parent.parent_location_id
        ancestors.reverse()

        children = self.repository.get_children(loc.id)

        return LocationHierarchyRead(
            location=LocationRead.model_validate(loc),
            ancestors=[LocationRead.model_validate(a) for a in ancestors],
            children=[LocationRead.model_validate(c) for c in children]
        )
