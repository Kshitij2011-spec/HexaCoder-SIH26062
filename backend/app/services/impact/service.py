"""Operational Impact Propagation Service."""

import uuid
from typing import Optional, List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.expeditions.models import ExpeditionModel
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.people.models import PersonModel
from backend.app.services.dependencies.service import DependencyService
from backend.app.services.constraints.service import ConstraintService
from backend.app.services.impact.schemas import (
    ImpactResult,
    AffectedEntity,
)
from backend.app.shared.types.reasoning import (
    TraversalDirection,
    ConstraintState,
)


class ImpactService:
    """
    Computes deterministic operational impact propagation across semantic dependency chains.
    Identifies downstream affected missions, consignments, assets, teams, and at-risk constraints.
    """

    def __init__(self, session: Session):
        self.session = session
        self.dependency_service = DependencyService(session)
        self.constraint_service = ConstraintService(session)

    def _resolve_entity_code(self, entity_type: str, entity_id: uuid.UUID) -> Optional[str]:
        """Queries the entity code for human-readable operational traceability."""
        e_type = entity_type.upper()
        if e_type == "MISSION":
            code = self.session.execute(select(MissionModel.code).where(MissionModel.id == entity_id)).scalar_one_or_none()
            if code:
                return code
        elif e_type == "EXPEDITION":
            code = self.session.execute(select(ExpeditionModel.code).where(ExpeditionModel.id == entity_id)).scalar_one_or_none()
            if code:
                return code
        elif e_type == "TEAM":
            code = self.session.execute(select(TeamModel.code).where(TeamModel.id == entity_id)).scalar_one_or_none()
            if code:
                return code
        elif e_type == "PERSON":
            code = self.session.execute(select(PersonModel.person_code).where(PersonModel.id == entity_id)).scalar_one_or_none()
            if code:
                return code

        table_map = {
            "ASSET": ("assets", "asset_code"),
            "CARGO_CONSIGNMENT": ("cargo_consignments", "code"),
            "CARGO_PACKAGE": ("cargo_packages", "code"),
            "TRANSPORT_LEG": ("transport_legs", "code"),
            "INVENTORY_ITEM": ("inventory_items", "item_code"),
            "LOCATION": ("locations", "code"),
            "DOCUMENT": ("documents", "document_code"),
        }

        cfg = table_map.get(e_type)
        if not cfg:
            return None

        tbl, col = cfg
        try:
            sql = text(f"SELECT {col} FROM {tbl} WHERE CAST(id AS TEXT) = :id_str")
            row = self.session.execute(sql, {"id_str": str(entity_id)}).mappings().first()
            if row:
                return row[col]
        except Exception:
            try:
                sql2 = text(f"SELECT {col} FROM {tbl} WHERE id = :id_str")
                row = self.session.execute(sql2, {"id_str": str(entity_id)}).mappings().first()
                if row:
                    return row[col]
            except Exception:
                return None
        return None

    def calculate_impact(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        change_summary: str,
        depth: int = 3,
        correlation_id: Optional[uuid.UUID] = None
    ) -> ImpactResult:
        """
        Calculates bounded impact propagation for a mutation on source entity.
        Traverses semantic graph both directions (incoming dependents and connected items).
        """
        bounded_depth = min(max(1, depth), DependencyService.MAX_TRAVERSAL_DEPTH)
        root_type = entity_type.upper()
        root_code = self._resolve_entity_code(root_type, entity_id)

        # Traverse graph for connected and dependent entities
        graph_result = self.dependency_service.traverse_graph(
            entity_type=root_type,
            entity_id=entity_id,
            direction=TraversalDirection.BOTH,
            max_depth=bounded_depth
        )

        affected_entities: List[AffectedEntity] = []
        seen_entities: Set[Tuple[str, uuid.UUID]] = set()
        reasons: List[str] = []

        for p in graph_result.paths:
            last_edge = p.edges[-1]
            # Determine target node in path
            target_key = (p.terminal_entity_type, p.terminal_entity_id)
            if target_key in seen_entities or target_key == (root_type, entity_id):
                continue
            seen_entities.add(target_key)

            target_code = self._resolve_entity_code(p.terminal_entity_type, p.terminal_entity_id)

            # Build deterministic explanation from actual relationship path
            path_str = " -> ".join([f"{e.source_entity_type} [{e.relationship.value}] {e.target_entity_type}" for e in p.edges])
            reason = (
                f"{p.terminal_entity_type} {target_code or str(p.terminal_entity_id)[:8]} "
                f"is reachable at depth {p.depth} via: {path_str}."
            )
            reasons.append(reason)

            affected_entities.append(
                AffectedEntity(
                    entity_type=p.terminal_entity_type,
                    entity_id=p.terminal_entity_id,
                    entity_code=target_code,
                    relationship=last_edge.relationship.value,
                    depth=p.depth,
                    direction=last_edge.direction,
                    reason=reason
                )
            )

        # Evaluate constraints for source and affected entities
        constraint_candidates = []
        eval_targets = [(root_type, entity_id)] + [(ae.entity_type, ae.entity_id) for ae in affected_entities]

        for etype, eid in eval_targets:
            summary = self.constraint_service.evaluate_for_entity(etype, eid)
            for cr in summary.results:
                constraint_candidates.append(cr)

        return ImpactResult(
            source_entity_type=root_type,
            source_entity_id=entity_id,
            source_entity_code=root_code,
            change_summary=change_summary,
            depth_limit=bounded_depth,
            total_affected_entities=len(affected_entities),
            affected_entities=affected_entities,
            dependency_paths=graph_result.paths,
            reasons=reasons,
            constraint_candidates=constraint_candidates,
            correlation_id=correlation_id or uuid.uuid4()
        )
