"""The concept graph: a DAG of concepts linked by prerequisite edges.

Vendored from the standalone knowledge-tracing engine (``ai_generated/graph.py``
plus the ``Concept`` dataclass from ``ai_generated/models.py``). Pure and
IO-free: the recommender builds one of these from the DB-backed concept graph
and feeds it to the ``KnowledgeTracer``.

Note: this ``Concept`` is the engine's lightweight value type, distinct from the
SQLAlchemy ``backend.db.models.Concept`` ORM entity.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    """A single node in the knowledge graph.

    prerequisites are the ids of concepts that must be understood first. The
    edges they define must form a DAG (validated by ConceptGraph).
    """

    id: str
    name: str
    prerequisites: tuple[str, ...] = ()
    difficulty: float = 0.5  # 0 (trivial) .. 1 (hard); reserved for question targeting

    def __post_init__(self) -> None:
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(f"difficulty for {self.id!r} must be in [0, 1]")


class ConceptGraph:
    """A directed acyclic graph of concepts.

    An edge prereq -> concept means `prereq` must be learned before `concept`.
    The constructor validates that every prerequisite exists and that the edges
    contain no cycle, so downstream code can rely on a valid topological order.
    """

    def __init__(self, concepts: Iterable[Concept]):
        self._concepts: dict[str, Concept] = {}
        for c in concepts:
            if c.id in self._concepts:
                raise ValueError(f"duplicate concept id: {c.id!r}")
            self._concepts[c.id] = c

        # Validate prerequisite references.
        for c in self._concepts.values():
            for p in c.prerequisites:
                if p not in self._concepts:
                    raise ValueError(f"concept {c.id!r} references unknown prerequisite {p!r}")

        # Build the dependents adjacency (prereq -> [concepts depending on it]).
        self._dependents: dict[str, list[str]] = {cid: [] for cid in self._concepts}
        for c in self._concepts.values():
            for p in c.prerequisites:
                self._dependents[p].append(c.id)

        self._topo = self._topological_order()  # raises on cycle

    # -- basic accessors -------------------------------------------------

    @property
    def concepts(self) -> list[str]:
        return list(self._concepts.keys())

    def get(self, concept_id: str) -> Concept:
        return self._concepts[concept_id]

    def prerequisites(self, concept_id: str) -> tuple[str, ...]:
        return self._concepts[concept_id].prerequisites

    def direct_dependents(self, concept_id: str) -> list[str]:
        return list(self._dependents[concept_id])

    def topological_order(self) -> list[str]:
        return list(self._topo)

    # -- transitive closure ---------------------------------------------

    def ancestors(self, concept_id: str) -> set[str]:
        """All transitive prerequisites of a concept."""
        seen: set[str] = set()
        stack = list(self.prerequisites(concept_id))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.prerequisites(cur))
        return seen

    def descendants(self, concept_id: str) -> set[str]:
        """All transitive dependents of a concept."""
        seen: set[str] = set()
        stack = list(self._dependents[concept_id])
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self._dependents[cur])
        return seen

    # -- internals -------------------------------------------------------

    def _topological_order(self) -> list[str]:
        """Kahn's algorithm. Raises ValueError if the graph has a cycle."""
        indeg = {cid: len(self._concepts[cid].prerequisites) for cid in self._concepts}
        # Deterministic ordering: process ready nodes in sorted id order.
        ready = deque(sorted(cid for cid, d in indeg.items() if d == 0))
        order: list[str] = []
        while ready:
            cur = ready.popleft()
            order.append(cur)
            for dep in sorted(self._dependents[cur]):
                indeg[dep] -= 1
                if indeg[dep] == 0:
                    ready.append(dep)
        if len(order) != len(self._concepts):
            remaining = set(self._concepts) - set(order)
            raise ValueError(f"prerequisite graph has a cycle involving: {sorted(remaining)}")
        return order
