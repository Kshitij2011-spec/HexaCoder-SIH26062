"""SQLAlchemy Data Access Repository for Incidents and Incident References."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from backend.app.domains.incidents.models import IncidentModel, IncidentReferenceModel


class IncidentRepository:
    """Encapsulates transactional database access operations for Incident entities."""

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # 1. INCIDENTS
    # ============================================================

    def get_by_id(self, incident_id: uuid.UUID) -> Optional[IncidentModel]:
        stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, incident_code: str) -> Optional[IncidentModel]:
        stmt = select(IncidentModel).where(IncidentModel.incident_code == incident_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[int] = None,
        location_id: Optional[uuid.UUID] = None,
        asset_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[IncidentModel], int]:
        query = select(IncidentModel)
        count_query = select(func.count(IncidentModel.id))

        if status:
            query = query.where(IncidentModel.status == status)
            count_query = count_query.where(IncidentModel.status == status)
        if severity:
            query = query.where(IncidentModel.severity == severity)
            count_query = count_query.where(IncidentModel.severity == severity)
        if priority is not None:
            query = query.where(IncidentModel.priority == priority)
            count_query = count_query.where(IncidentModel.priority == priority)
        if location_id is not None:
            query = query.where(IncidentModel.location_id == location_id)
            count_query = count_query.where(IncidentModel.location_id == location_id)
        if asset_id is not None:
            query = query.where(IncidentModel.asset_id == asset_id)
            count_query = count_query.where(IncidentModel.asset_id == asset_id)

        total = self.session.execute(count_query).scalar() or 0
        offset = (page - 1) * page_size
        stmt = query.order_by(desc(IncidentModel.detected_at), desc(IncidentModel.created_at)).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def create_incident(self, incident: IncidentModel) -> IncidentModel:
        self.session.add(incident)
        self.session.flush()
        return incident

    def update_incident(self, incident: IncidentModel) -> IncidentModel:
        self.session.add(incident)
        self.session.flush()
        return incident

    # ============================================================
    # 2. INCIDENT REFERENCES
    # ============================================================

    def get_reference_by_target(
        self,
        incident_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> Optional[IncidentReferenceModel]:
        stmt = select(IncidentReferenceModel).where(
            IncidentReferenceModel.incident_id == incident_id,
            IncidentReferenceModel.reference_type == reference_type,
            IncidentReferenceModel.reference_id == reference_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_references_by_incident(
        self,
        incident_id: uuid.UUID,
    ) -> List[IncidentReferenceModel]:
        stmt = (
            select(IncidentReferenceModel)
            .where(IncidentReferenceModel.incident_id == incident_id)
            .order_by(IncidentReferenceModel.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_reference(self, reference: IncidentReferenceModel) -> IncidentReferenceModel:
        self.session.add(reference)
        self.session.flush()
        return reference
