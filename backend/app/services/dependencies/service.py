"""Dependency Service for Semantic Relationship Navigation and Bounded Traversal."""

import uuid
from collections import deque
from typing import Optional, List, Set, Tuple, Dict, Any
from sqlalchemy.orm import Session
from backend.app.services.dependencies.models import DependencyModel
from backend.app.services.dependencies.repository import DependencyRepository
from backend.app.services.dependencies.schemas import (
    DependencyEdge,
    DependencyPath,
    DependencyGraphResult,
    DependencyRead,
)
from backend.app.shared.types.reasoning import (
    DependencyRelationship,
    TraversalDirection,
)
from backend.app.core.errors import DomainValidationError


class DependencyService:
    """
    Core service for querying semantic dependencies, traversing paths,
    and performing bounded, cycle-safe graph exploration.
    Authoritative store: public.dependencies.
    """

    MAX_TRAVERSAL_DEPTH = 5
    DEFAULT_TRAVERSAL_DEPTH = 3

    def __init__(self, session: Session):
        self.session = session
        self.repository = DependencyRepository(session)

    def _model_to_edge(self, model: DependencyModel, direction: str) -> DependencyEdge:
        """Converts an ORM DependencyModel to a normalized DependencyEdge."""
        try:
            rel = DependencyRelationship(model.relationship_type)
        except ValueError:
            # Fallback if invalid string in legacy data, though validation prevents it
            rel = DependencyRelationship[model.relationship_type]

        return DependencyEdge(
            source_entity_type=model.source_entity_type,
            source_entity_id=model.source_entity_id,
            relationship=rel,
            target_entity_type=model.target_entity_type,
            target_entity_id=model.target_entity_id,
            direction=direction,
            criticality=model.criticality or "CRITICAL",
            provenance=model.data_provenance or "SYNTHETIC_DEMO",
            metadata=model.metadata_ if hasattr(model, "metadata_") and isinstance(model.metadata_, dict) else {},
        )

    def get_outgoing_dependencies(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        relationship_type: Optional[str] = None
    ) -> List[DependencyEdge]:
        """Returns direct outgoing dependencies (entity -> target)."""
        models = self.repository.get_outgoing(entity_type, entity_id, relationship_type)
        return [self._model_to_edge(m, "OUTGOING") for m in models]

    def get_incoming_dependencies(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        relationship_type: Optional[str] = None
    ) -> List[DependencyEdge]:
        """Returns direct incoming dependencies/dependents (source -> entity)."""
        models = self.repository.get_incoming(entity_type, entity_id, relationship_type)
        return [self._model_to_edge(m, "INCOMING") for m in models]

    def get_dependencies(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        direction: TraversalDirection = TraversalDirection.OUTGOING,
        relationship_type: Optional[str] = None
    ) -> List[DependencyEdge]:
        """Retrieves direct dependencies based on direction."""
        if direction == TraversalDirection.OUTGOING:
            return self.get_outgoing_dependencies(entity_type, entity_id, relationship_type)
        elif direction == TraversalDirection.INCOMING:
            return self.get_incoming_dependencies(entity_type, entity_id, relationship_type)
        elif direction == TraversalDirection.BOTH:
            outgoing = self.get_outgoing_dependencies(entity_type, entity_id, relationship_type)
            incoming = self.get_incoming_dependencies(entity_type, entity_id, relationship_type)
            return outgoing + incoming
        else:
            raise DomainValidationError(f"Unsupported traversal direction: {direction}")

    def traverse_graph(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        direction: TraversalDirection = TraversalDirection.OUTGOING,
        max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
        relationship_type: Optional[str] = None
    ) -> DependencyGraphResult:
        """
        Executes bounded, cycle-safe Breadth-First Search (BFS) starting from the root entity.
        Enforces depth bounds [1, MAX_TRAVERSAL_DEPTH=5].
        Tracks visited (entity_type, entity_id) pairs to eliminate infinite loops.
        """
        bounded_depth = min(max(1, max_depth), self.MAX_TRAVERSAL_DEPTH)
        root_type = entity_type.upper()
        root_key = (root_type, entity_id)

        visited: Set[Tuple[str, uuid.UUID]] = {root_key}
        discovered_paths: List[DependencyPath] = []
        direct_edges: List[DependencyEdge] = []

        # Queue items: (current_type, current_id, current_depth, path_edges)
        queue: deque[Tuple[str, uuid.UUID, int, List[DependencyEdge]]] = deque()
        queue.append((root_type, entity_id, 0, []))

        while queue:
            curr_type, curr_id, curr_depth, curr_path = queue.popleft()

            if curr_depth >= bounded_depth:
                continue

            next_edges: List[Tuple[DependencyEdge, Tuple[str, uuid.UUID]]] = []

            # 1. Outgoing edges (curr -> target)
            if direction in (TraversalDirection.OUTGOING, TraversalDirection.BOTH):
                for m in self.repository.get_outgoing(curr_type, curr_id, relationship_type):
                    edge = self._model_to_edge(m, "OUTGOING")
                    next_node = (m.target_entity_type.upper(), m.target_entity_id)
                    next_edges.append((edge, next_node))

            # 2. Incoming edges (source -> curr)
            if direction in (TraversalDirection.INCOMING, TraversalDirection.BOTH):
                for m in self.repository.get_incoming(curr_type, curr_id, relationship_type):
                    edge = self._model_to_edge(m, "INCOMING")
                    next_node = (m.source_entity_type.upper(), m.source_entity_id)
                    next_edges.append((edge, next_node))

            for edge, next_node in next_edges:
                new_path_edges = curr_path + [edge]

                # Record direct edge from root
                if curr_depth == 0:
                    direct_edges.append(edge)

                if next_node not in visited:
                    visited.add(next_node)
                    discovered_paths.append(
                        DependencyPath(
                            depth=curr_depth + 1,
                            edges=new_path_edges,
                            terminal_entity_type=next_node[0],
                            terminal_entity_id=next_node[1]
                        )
                    )
                    queue.append((next_node[0], next_node[1], curr_depth + 1, new_path_edges))
                else:
                    # Cycle detected or already visited node: do NOT recurse into it
                    continue

        return DependencyGraphResult(
            entity_type=root_type,
            entity_id=entity_id,
            direction=direction,
            depth_limit=bounded_depth,
            total_nodes_visited=len(visited),
            direct_dependencies=direct_edges,
            paths=discovered_paths
        )
