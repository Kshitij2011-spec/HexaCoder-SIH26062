"""Operational Timeline Domain Service for Track B Logistics & Operations.

Aggregates immutable operational events, audit logs, offline sync operations,
and incident propagation records into a unified, deterministic, read-only timeline.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set, Literal
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_

from backend.app.platform.events.models import OperationalEventModel
from backend.app.platform.audit.models import AuditLogModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.cargo.models import CargoConsignmentModel, CargoPackageModel
from backend.app.domains.transport.models import TransportLegModel, TransportCargoAssignmentModel
from backend.app.domains.inventory.models import (
    InventoryItemModel,
    InventoryStockLotModel,
    InventoryTransactionModel,
)
from backend.app.domains.assets.models import AssetModel, MaintenanceRecordModel
from backend.app.domains.incidents.models import (
    IncidentModel,
    IncidentReferenceModel,
    IncidentPropagationModel,
)
from backend.app.domains.sync.models import OfflineOperationModel

from backend.app.domains.operations.schemas import (
    TimelineEntityType,
    TimelineEntryType,
    TimelineEntry,
    TimelineResponse,
    normalize_entity_type,
    ENTITY_TYPE_ALIASES,
)
from backend.app.core.errors import EntityNotFoundError, DomainValidationError


def ensure_utc(dt: Optional[datetime]) -> datetime:
    """Ensures datetime is timezone-aware in UTC."""
    if not dt:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class OperationalTimelineService:
    """
    Read-only domain service providing chronological operational history
    and cross-domain event reconstruction for Person B resources.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_timeline(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        include_related: bool = False,
        order: Literal["desc", "asc"] = "desc",
        page: int = 1,
        page_size: int = 50,
        entry_type: Optional[str] = None,
        occurred_from: Optional[datetime] = None,
        occurred_to: Optional[datetime] = None,
    ) -> TimelineResponse:
        """
        Retrieves a deterministic, aggregated operational timeline for a Person B entity.
        Strictly read-only; never mutates domain state.
        """
        canonical_type = normalize_entity_type(entity_type)
        if not canonical_type:
            raise DomainValidationError(
                f"Invalid or unsupported entity_type '{entity_type}'. Supported types: {sorted(set(ENTITY_TYPE_ALIASES.values()))}",
                field="entity_type",
            )

        # 1. Authoritative entity existence verification
        entity_name = self._verify_entity_exists(canonical_type, entity_id)

        # 2. Collect primary + direct 1-hop related Person B entities if requested
        targets: List[Tuple[str, uuid.UUID, Optional[str]]] = [(canonical_type, entity_id, None)]
        if include_related:
            related = self._discover_related_entities(canonical_type, entity_id)
            targets.extend(related)

        # Deduplicate targets by (type, id)
        unique_targets: List[Tuple[str, uuid.UUID, Optional[str]]] = []
        seen_targets: Set[Tuple[str, uuid.UUID]] = set()
        for t_type, t_id, rel_role in targets:
            key = (t_type, t_id)
            if key not in seen_targets:
                seen_targets.add(key)
                unique_targets.append((t_type, t_id, rel_role))

        # 3. Query immutable events, audits, propagations, and sync records
        raw_events = self._fetch_operational_events(unique_targets)
        raw_audits = self._fetch_audit_logs(unique_targets)
        raw_propagations = self._fetch_propagations(canonical_type, entity_id, include_related)
        raw_sync_ops = self._fetch_sync_operations(canonical_type, entity_id, include_related)

        # 4. Deduplication: Merge correlated operational events and audit logs
        deduplicated_entries = self._deduplicate_and_unify(
            raw_events=raw_events,
            raw_audits=raw_audits,
            raw_propagations=raw_propagations,
            raw_sync_ops=raw_sync_ops,
            primary_type=canonical_type,
            primary_id=entity_id,
        )

        # 5. Optional filtering
        filtered = deduplicated_entries
        if entry_type:
            cleaned_entry_type = entry_type.strip().upper()
            filtered = [e for e in filtered if e.entry_type.value == cleaned_entry_type]

        if occurred_from:
            utc_from = ensure_utc(occurred_from)
            filtered = [e for e in filtered if e.timestamp >= utc_from]

        if occurred_to:
            utc_to = ensure_utc(occurred_to)
            filtered = [e for e in filtered if e.timestamp <= utc_to]

        # 6. Deterministic Ordering: timestamp -> event_or_action -> id
        reverse_sort = order == "desc"
        filtered.sort(
            key=lambda x: (x.timestamp, x.event_or_action or "", str(x.id)),
            reverse=reverse_sort,
        )

        # 7. Pagination
        total_entries = len(filtered)
        total_pages = max(1, math.ceil(total_entries / page_size)) if total_entries > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_entries = filtered[start_idx:end_idx]

        return TimelineResponse(
            entity_type=canonical_type,
            entity_id=entity_id,
            entity_name=entity_name,
            total_entries=total_entries,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            entries=paged_entries,
            related_entities_included=include_related and len(unique_targets) > 1,
        )

    # ============================================================
    # ENTITY EXISTENCE VERIFICATION
    # ============================================================

    def _verify_entity_exists(self, canonical_type: str, entity_id: uuid.UUID) -> Optional[str]:
        """Checks authoritative table for entity existence; raises EntityNotFoundError if missing."""
        if canonical_type == TimelineEntityType.LOCATION.value:
            loc = self.session.get(LocationModel, entity_id)
            if not loc:
                raise EntityNotFoundError("Location", entity_id)
            return loc.code or loc.name

        elif canonical_type == TimelineEntityType.CARGO_CONSIGNMENT.value:
            consignment = self.session.get(CargoConsignmentModel, entity_id)
            if not consignment:
                raise EntityNotFoundError("CargoConsignment", entity_id)
            return consignment.code

        elif canonical_type == TimelineEntityType.CARGO_PACKAGE.value:
            pkg = self.session.get(CargoPackageModel, entity_id)
            if not pkg:
                raise EntityNotFoundError("CargoPackage", entity_id)
            return pkg.code

        elif canonical_type == TimelineEntityType.TRANSPORT_LEG.value:
            leg = self.session.get(TransportLegModel, entity_id)
            if not leg:
                raise EntityNotFoundError("TransportLeg", entity_id)
            return leg.code

        elif canonical_type == TimelineEntityType.INVENTORY_ITEM.value:
            item = self.session.get(InventoryItemModel, entity_id)
            if not item:
                raise EntityNotFoundError("InventoryItem", entity_id)
            return item.item_code

        elif canonical_type == TimelineEntityType.INVENTORY_STOCK_LOT.value:
            lot = self.session.get(InventoryStockLotModel, entity_id)
            if not lot:
                raise EntityNotFoundError("InventoryStockLot", entity_id)
            return lot.lot_code

        elif canonical_type == TimelineEntityType.ASSET.value:
            asset = self.session.get(AssetModel, entity_id)
            if not asset:
                raise EntityNotFoundError("Asset", entity_id)
            return asset.asset_code

        elif canonical_type == TimelineEntityType.MAINTENANCE_RECORD.value:
            maint = self.session.get(MaintenanceRecordModel, entity_id)
            if not maint:
                raise EntityNotFoundError("MaintenanceRecord", entity_id)
            return f"MAINT-{maint.maintenance_type}"

        elif canonical_type == TimelineEntityType.INCIDENT.value:
            inc = self.session.get(IncidentModel, entity_id)
            if not inc:
                raise EntityNotFoundError("Incident", entity_id)
            return inc.incident_code

        elif canonical_type == TimelineEntityType.INCIDENT_REFERENCE.value:
            ref = self.session.get(IncidentReferenceModel, entity_id)
            if not ref:
                raise EntityNotFoundError("IncidentReference", entity_id)
            return f"REF-{ref.reference_type}"

        elif canonical_type == TimelineEntityType.OFFLINE_OPERATION.value:
            # Check by primary ID or operation_id
            stmt = select(OfflineOperationModel).where(
                or_(OfflineOperationModel.id == entity_id, OfflineOperationModel.operation_id == entity_id)
            )
            op = self.session.execute(stmt).scalar_one_or_none()
            if not op:
                raise EntityNotFoundError("OfflineOperation", entity_id)
            return f"SYNC-{op.operation_type}"

        elif canonical_type == TimelineEntityType.INCIDENT_PROPAGATION.value:
            prop = self.session.get(IncidentPropagationModel, entity_id)
            if not prop:
                raise EntityNotFoundError("IncidentPropagation", entity_id)
            return f"PROPAGATION-{prop.action}"

        return None

    # ============================================================
    # 1-HOP CROSS-DOMAIN RELATIONSHIP DISCOVERY
    # ============================================================

    def _discover_related_entities(
        self, canonical_type: str, entity_id: uuid.UUID
    ) -> List[Tuple[str, uuid.UUID, str]]:
        """
        Discovers direct 1-hop related Person B entities without inventing new schemas.
        Returns list of (related_type, related_id, relationship_role).
        """
        related: List[Tuple[str, uuid.UUID, str]] = []

        # 1. Transport Leg <-> Cargo Assignments
        if canonical_type == TimelineEntityType.TRANSPORT_LEG.value:
            stmt = select(TransportCargoAssignmentModel.cargo_consignment_id).where(
                TransportCargoAssignmentModel.transport_leg_id == entity_id
            )
            consignment_ids = self.session.execute(stmt).scalars().all()
            for cid in consignment_ids:
                related.append((TimelineEntityType.CARGO_CONSIGNMENT.value, cid, "ASSIGNED_CARGO"))

        # 2. Cargo Consignment <-> Packages and Transport Assignments
        elif canonical_type == TimelineEntityType.CARGO_CONSIGNMENT.value:
            # Packages belonging to consignment
            pkg_stmt = select(CargoPackageModel.id).where(CargoPackageModel.consignment_id == entity_id)
            pkg_ids = self.session.execute(pkg_stmt).scalars().all()
            for pid in pkg_ids:
                related.append((TimelineEntityType.CARGO_PACKAGE.value, pid, "PACKAGE"))

            # Transport legs moving this consignment
            leg_stmt = select(TransportCargoAssignmentModel.transport_leg_id).where(
                TransportCargoAssignmentModel.cargo_consignment_id == entity_id
            )
            leg_ids = self.session.execute(leg_stmt).scalars().all()
            for lid in leg_ids:
                related.append((TimelineEntityType.TRANSPORT_LEG.value, lid, "TRANSPORT_LEG"))

        # 3. Asset <-> Maintenance Records and Incident Propagations
        elif canonical_type == TimelineEntityType.ASSET.value:
            maint_stmt = select(MaintenanceRecordModel.id).where(MaintenanceRecordModel.asset_id == entity_id)
            maint_ids = self.session.execute(maint_stmt).scalars().all()
            for mid in maint_ids:
                related.append((TimelineEntityType.MAINTENANCE_RECORD.value, mid, "MAINTENANCE_RECORD"))

            prop_stmt = select(IncidentPropagationModel.id).where(
                and_(
                    IncidentPropagationModel.reference_type == "ASSET",
                    IncidentPropagationModel.reference_id == entity_id,
                )
            )
            prop_ids = self.session.execute(prop_stmt).scalars().all()
            for pid in prop_ids:
                related.append((TimelineEntityType.INCIDENT_PROPAGATION.value, pid, "INCIDENT_PROPAGATION"))

        # 4. Incident <-> References and Propagation Records
        elif canonical_type == TimelineEntityType.INCIDENT.value:
            ref_stmt = select(IncidentReferenceModel.id).where(IncidentReferenceModel.incident_id == entity_id)
            ref_ids = self.session.execute(ref_stmt).scalars().all()
            for rid in ref_ids:
                related.append((TimelineEntityType.INCIDENT_REFERENCE.value, rid, "INCIDENT_REFERENCE"))

            prop_stmt = select(IncidentPropagationModel.id).where(IncidentPropagationModel.incident_id == entity_id)
            prop_ids = self.session.execute(prop_stmt).scalars().all()
            for pid in prop_ids:
                related.append((TimelineEntityType.INCIDENT_PROPAGATION.value, pid, "INCIDENT_PROPAGATION"))

        # 5. Inventory Item <-> Stock Lots
        elif canonical_type == TimelineEntityType.INVENTORY_ITEM.value:
            lot_stmt = select(InventoryStockLotModel.id).where(InventoryStockLotModel.inventory_item_id == entity_id)
            lot_ids = self.session.execute(lot_stmt).scalars().all()
            for lid in lot_ids:
                related.append((TimelineEntityType.INVENTORY_STOCK_LOT.value, lid, "STOCK_LOT"))

        # 6. Inventory Stock Lot <-> Transactions and Parent Item
        elif canonical_type == TimelineEntityType.INVENTORY_STOCK_LOT.value:
            lot = self.session.get(InventoryStockLotModel, entity_id)
            if lot and lot.inventory_item_id:
                related.append((TimelineEntityType.INVENTORY_ITEM.value, lot.inventory_item_id, "PARENT_ITEM"))

        # 7. Location <-> Existing Assets, Stock Lots, and Transport Legs
        elif canonical_type == TimelineEntityType.LOCATION.value:
            asset_stmt = select(AssetModel.id).where(AssetModel.location_id == entity_id).limit(50)
            asset_ids = self.session.execute(asset_stmt).scalars().all()
            for aid in asset_ids:
                related.append((TimelineEntityType.ASSET.value, aid, "STATION_ASSET"))

            lot_stmt = select(InventoryStockLotModel.id).where(InventoryStockLotModel.location_id == entity_id).limit(50)
            lot_ids = self.session.execute(lot_stmt).scalars().all()
            for lid in lot_ids:
                related.append((TimelineEntityType.INVENTORY_STOCK_LOT.value, lid, "STATION_STOCK_LOT"))

            leg_stmt = (
                select(TransportLegModel.id)
                .where(
                    or_(
                        TransportLegModel.origin_location_id == entity_id,
                        TransportLegModel.destination_location_id == entity_id,
                    )
                )
                .limit(50)
            )
            leg_ids = self.session.execute(leg_stmt).scalars().all()
            for lid in leg_ids:
                related.append((TimelineEntityType.TRANSPORT_LEG.value, lid, "TRANSIT_LEG"))

            prop_stmt = select(IncidentPropagationModel.id).where(
                and_(
                    IncidentPropagationModel.reference_type == "LOCATION",
                    IncidentPropagationModel.reference_id == entity_id,
                )
            )
            prop_ids = self.session.execute(prop_stmt).scalars().all()
            for pid in prop_ids:
                related.append((TimelineEntityType.INCIDENT_PROPAGATION.value, pid, "INCIDENT_PROPAGATION"))

        # 8. Offline Operation <-> Targeted Entity
        elif canonical_type == TimelineEntityType.OFFLINE_OPERATION.value:
            op = self.session.get(OfflineOperationModel, entity_id)
            if op and isinstance(op.payload, dict):
                target_raw_id = op.payload.get("id") or op.payload.get("entity_id")
                if target_raw_id:
                    try:
                        target_uuid = uuid.UUID(str(target_raw_id))
                        op_target_type = normalize_entity_type(op.entity_type)
                        if op_target_type:
                            related.append((op_target_type, target_uuid, "TARGET_ENTITY"))
                    except (ValueError, TypeError):
                        pass

        return related

    # ============================================================
    # DATA RETRIEVAL (EVENTS, AUDITS, PROPAGATIONS, SYNC)
    # ============================================================

    def _fetch_operational_events(
        self, targets: List[Tuple[str, uuid.UUID, Optional[str]]]
    ) -> List[Tuple[OperationalEventModel, Optional[str]]]:
        """Fetches operational events for the target entities."""
        if not targets:
            return []

        conditions = [
            and_(
                OperationalEventModel.entity_type == t_type,
                OperationalEventModel.entity_id == t_id,
            )
            for t_type, t_id, _ in targets
        ]

        stmt = (
            select(OperationalEventModel)
            .where(or_(*conditions))
            .order_by(OperationalEventModel.occurred_at.desc())
        )
        models = self.session.execute(stmt).scalars().all()

        # Map entity_id to relationship role
        role_map = {(t_type, t_id): rel_role for t_type, t_id, rel_role in targets}
        return [(m, role_map.get((m.entity_type, m.entity_id))) for m in models]

    def _fetch_audit_logs(
        self, targets: List[Tuple[str, uuid.UUID, Optional[str]]]
    ) -> List[Tuple[AuditLogModel, Optional[str]]]:
        """Fetches audit logs for the target entities."""
        if not targets:
            return []

        conditions = [
            and_(
                AuditLogModel.entity_type == t_type,
                AuditLogModel.entity_id == t_id,
            )
            for t_type, t_id, _ in targets
        ]

        stmt = select(AuditLogModel).where(or_(*conditions)).order_by(AuditLogModel.occurred_at.desc())
        models = self.session.execute(stmt).scalars().all()

        role_map = {(t_type, t_id): rel_role for t_type, t_id, rel_role in targets}
        return [(m, role_map.get((m.entity_type, m.entity_id))) for m in models]

    def _fetch_propagations(
        self, primary_type: str, primary_id: uuid.UUID, include_related: bool
    ) -> List[IncidentPropagationModel]:
        """Fetches incident propagation records matching incident or referenced target."""
        conditions = []
        if primary_type == TimelineEntityType.INCIDENT.value:
            conditions.append(IncidentPropagationModel.incident_id == primary_id)

        if include_related or primary_type in {
            TimelineEntityType.LOCATION.value,
            TimelineEntityType.ASSET.value,
            TimelineEntityType.INVENTORY_STOCK_LOT.value,
            TimelineEntityType.TRANSPORT_LEG.value,
            TimelineEntityType.CARGO_CONSIGNMENT.value,
        }:
            conditions.append(
                and_(
                    IncidentPropagationModel.reference_type == primary_type,
                    IncidentPropagationModel.reference_id == primary_id,
                )
            )

        if not conditions:
            return []

        stmt = (
            select(IncidentPropagationModel)
            .where(or_(*conditions))
            .order_by(IncidentPropagationModel.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def _fetch_sync_operations(
        self, primary_type: str, primary_id: uuid.UUID, include_related: bool
    ) -> List[OfflineOperationModel]:
        """Fetches offline operations matching target entity."""
        conditions = []
        if primary_type == TimelineEntityType.OFFLINE_OPERATION.value:
            conditions.append(
                or_(
                    OfflineOperationModel.id == primary_id,
                    OfflineOperationModel.operation_id == primary_id,
                )
            )
        elif include_related:
            # Check offline ops whose payload targets primary_id
            conditions.append(OfflineOperationModel.entity_type == primary_type)

        if not conditions:
            return []

        stmt = (
            select(OfflineOperationModel)
            .where(or_(*conditions))
            .order_by(OfflineOperationModel.created_at.desc())
        )
        ops = list(self.session.execute(stmt).scalars().all())

        if primary_type != TimelineEntityType.OFFLINE_OPERATION.value:
            # Filter in Python to ops matching primary_id in payload
            str_id = str(primary_id)
            ops = [
                op
                for op in ops
                if isinstance(op.payload, dict)
                and (str(op.payload.get("id")) == str_id or str(op.payload.get("entity_id")) == str_id)
            ]

        return ops

    # ============================================================
    # DEDUPLICATION AND ENTRY UNIFICATION
    # ============================================================

    def _deduplicate_and_unify(
        self,
        raw_events: List[Tuple[OperationalEventModel, Optional[str]]],
        raw_audits: List[Tuple[AuditLogModel, Optional[str]]],
        raw_propagations: List[IncidentPropagationModel],
        raw_sync_ops: List[OfflineOperationModel],
        primary_type: str,
        primary_id: uuid.UUID,
    ) -> List[TimelineEntry]:
        """
        Deduplicates and unifies operational events and audit logs.
        Merges correlated pairs with strong correlation_id + entity_id match,
        preserving event_id, audit_id, and snapshots in a single unified entry.
        """
        timeline_entries: List[TimelineEntry] = []
        matched_audit_ids: Set[uuid.UUID] = set()

        # Build lookup table for audits by (correlation_id, entity_id) when correlation_id is present
        audits_by_correlation: Dict[Tuple[uuid.UUID, uuid.UUID], List[Tuple[AuditLogModel, Optional[str]]]] = {}
        for audit, role in raw_audits:
            if audit.correlation_id:
                corr_key = (audit.correlation_id, audit.entity_id)
                audits_by_correlation.setdefault(corr_key, []).append((audit, role))

        # 1. Process Operational Events (merging corresponding audits)
        for ev, role in raw_events:
            matched_audit: Optional[AuditLogModel] = None

            # Primary Rule: Match on non-null correlation_id + entity_id
            if ev.correlation_id:
                corr_key = (ev.correlation_id, ev.entity_id)
                candidates = audits_by_correlation.get(corr_key, [])
                for candidate, _ in candidates:
                    if candidate.id not in matched_audit_ids:
                        matched_audit = candidate
                        matched_audit_ids.add(candidate.id)
                        break

            # Fallback Safe Correlation: Only if correlation_id was missing on either side
            if not matched_audit:
                ev_utc = ensure_utc(ev.occurred_at)
                for candidate, _ in raw_audits:
                    if candidate.id in matched_audit_ids:
                        continue
                    if candidate.entity_id != ev.entity_id or candidate.entity_type != ev.entity_type:
                        continue
                    # Delta <= 2.0s
                    cand_utc = ensure_utc(candidate.occurred_at)
                    delta_sec = abs((ev_utc - cand_utc).total_seconds())
                    if delta_sec > 2.0:
                        continue

                    # Strict state transition and semantic match requirement
                    cand_after_status = candidate.after_snapshot.get("status") if isinstance(candidate.after_snapshot, dict) else None
                    if ev.new_state and cand_after_status and ev.new_state == cand_after_status:
                        matched_audit = candidate
                        matched_audit_ids.add(candidate.id)
                        break

            # Construct unified TimelineEntry
            details: Dict[str, Any] = {}
            if ev.evidence and isinstance(ev.evidence, dict):
                details.update(ev.evidence)

            audit_action = None
            audit_id = None
            if matched_audit:
                audit_action = matched_audit.action
                audit_id = matched_audit.id
                if matched_audit.before_snapshot:
                    details["before_snapshot"] = matched_audit.before_snapshot
                if matched_audit.after_snapshot:
                    details["after_snapshot"] = matched_audit.after_snapshot
                if matched_audit.metadata_:
                    details["audit_metadata"] = matched_audit.metadata_

            entry_id = str(ev.id)
            description = (
                f"Status: {ev.previous_state} -> {ev.new_state}"
                if ev.previous_state and ev.new_state
                else f"State: {ev.new_state or ev.event_type}"
            )

            is_related = (ev.entity_type != primary_type or ev.entity_id != primary_id)
            timeline_entries.append(
                TimelineEntry(
                    id=entry_id,
                    entry_type=TimelineEntryType.OPERATIONAL_EVENT,
                    timestamp=ensure_utc(ev.occurred_at),
                    event_or_action=ev.event_type,
                    audit_action=audit_action,
                    entity_type=ev.entity_type,
                    entity_id=ev.entity_id,
                    entity_name=None,
                    source=f"EVENT_JOURNAL+{audit_action}" if audit_action else ev.source or "EVENT_JOURNAL",
                    previous_state=ev.previous_state,
                    new_state=ev.new_state,
                    status=ev.new_state,
                    actor_type=ev.actor_type or ("USER" if matched_audit and matched_audit.actor_person_id else "SYSTEM"),
                    actor_id=ev.actor_id or (matched_audit.actor_person_id if matched_audit else None),
                    correlation_id=ev.correlation_id or (matched_audit.correlation_id if matched_audit else None),
                    data_provenance=ev.data_provenance,
                    description=description,
                    details=details,
                    related_entity_type=ev.entity_type if is_related else None,
                    related_entity_id=ev.entity_id if is_related else None,
                    audit_id=audit_id,
                    event_id=ev.event_id,
                )
            )

        # 2. Process Unmatched Audit Logs (purely administrative or audit-only actions)
        for audit, role in raw_audits:
            if audit.id in matched_audit_ids:
                continue

            details = {}
            if audit.before_snapshot:
                details["before_snapshot"] = audit.before_snapshot
            if audit.after_snapshot:
                details["after_snapshot"] = audit.after_snapshot
            if audit.metadata_:
                details["audit_metadata"] = audit.metadata_

            before_status = audit.before_snapshot.get("status") if isinstance(audit.before_snapshot, dict) else None
            after_status = audit.after_snapshot.get("status") if isinstance(audit.after_snapshot, dict) else None

            description = (
                f"Action {audit.action}: {before_status} -> {after_status}"
                if before_status and after_status
                else f"Audit {audit.action}"
            )

            is_related = (audit.entity_type != primary_type or audit.entity_id != primary_id)
            timeline_entries.append(
                TimelineEntry(
                    id=str(audit.id),
                    entry_type=TimelineEntryType.AUDIT_RECORD,
                    timestamp=ensure_utc(audit.occurred_at),
                    event_or_action=audit.action,
                    audit_action=audit.action,
                    entity_type=audit.entity_type,
                    entity_id=audit.entity_id or primary_id,
                    entity_name=None,
                    source="AUDIT_LOG",
                    previous_state=before_status,
                    new_state=after_status,
                    status=after_status,
                    actor_type="USER" if (audit.actor_person_id or audit.actor_user_id) else "SYSTEM",
                    actor_id=audit.actor_person_id or audit.actor_user_id,
                    correlation_id=audit.correlation_id,
                    data_provenance="SYNTHETIC_DEMO",
                    description=description,
                    details=details,
                    related_entity_type=audit.entity_type if is_related else None,
                    related_entity_id=audit.entity_id if is_related else None,
                    audit_id=audit.id,
                    event_id=None,
                )
            )

        # 3. Process Incident Propagation Records (B8)
        for prop in raw_propagations:
            prop_details = {
                "reference_type": prop.reference_type,
                "reference_id": str(prop.reference_id),
                "action": prop.action,
                "status": prop.status,
                "reason": prop.reason,
            }
            if prop.operational_metadata:
                prop_details["operational_metadata"] = prop.operational_metadata

            desc = f"Propagation ({prop.action}): {prop.status} on {prop.reference_type}"
            if prop.reason:
                desc += f" — {prop.reason}"

            is_related = (prop.incident_id != primary_id)
            timeline_entries.append(
                TimelineEntry(
                    id=str(prop.id),
                    entry_type=TimelineEntryType.PROPAGATION_RECORD,
                    timestamp=ensure_utc(prop.created_at),
                    event_or_action=f"IncidentPropagation:{prop.action}",
                    audit_action=None,
                    entity_type=TimelineEntityType.INCIDENT_PROPAGATION.value,
                    entity_id=prop.id,
                    entity_name=f"PROP-{prop.action}",
                    source="INCIDENT_PROPAGATION_ENGINE",
                    previous_state=prop.previous_state,
                    new_state=prop.resulting_state,
                    status=prop.status,
                    actor_type="SYSTEM",
                    actor_id=getattr(prop, "actor_person_id", None),
                    correlation_id=getattr(prop, "correlation_id", None),
                    data_provenance="SYNTHETIC_DEMO",
                    description=desc,
                    details=prop_details,
                    related_entity_type=prop.reference_type if is_related else None,
                    related_entity_id=prop.reference_id if is_related else None,
                    audit_id=prop.audit_id,
                    event_id=prop.event_id,
                )
            )

        # 4. Process Offline Sync Operations (B5)
        for op in raw_sync_ops:
            sync_details = {
                "operation_id": str(op.operation_id),
                "operation_type": op.operation_type,
                "retry_count": op.retry_count,
                "failure_reason": op.failure_reason,
            }
            if isinstance(op.payload, dict):
                sync_details["payload_snapshot"] = op.payload

            desc = f"Offline Sync {op.operation_type} ({op.status})"
            if op.failure_reason:
                desc += f": {op.failure_reason}"

            is_related = (primary_type != TimelineEntityType.OFFLINE_OPERATION.value)
            timeline_entries.append(
                TimelineEntry(
                    id=str(op.id),
                    entry_type=TimelineEntryType.OFFLINE_SYNC,
                    timestamp=ensure_utc(op.applied_at or op.queued_at or op.created_at),
                    event_or_action=f"OfflineOperation:{op.operation_type}",
                    audit_action=None,
                    entity_type=TimelineEntityType.OFFLINE_OPERATION.value,
                    entity_id=op.id,
                    entity_name=f"SYNC-{op.operation_type}",
                    source="SYNC_QUEUE",
                    previous_state="PENDING" if op.status != "PENDING" else None,
                    new_state=op.status,
                    status=op.status,
                    actor_type="FIELD_CLIENT" if op.actor_id else "SYSTEM",
                    actor_id=op.actor_id,
                    correlation_id=op.correlation_id,
                    data_provenance=op.data_provenance,
                    description=desc,
                    details=sync_details,
                    related_entity_type=op.entity_type if is_related else None,
                    related_entity_id=None,
                    audit_id=None,
                    event_id=None,
                )
            )

        return timeline_entries
