"""Rehydrate a learner's belief state from the database.

Builds the in-memory ``ConceptGraph`` from the stored DAG and a ``KnowledgeTracer``
seeded from the user's ``LearnerState`` rows. Shared by the recommender and the
frontier-assessment endpoint so both read the same belief vector (the frontier
predicate and the recommendation predicate must agree).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Concept, ConceptRelationship, LearnerState
from backend.services.graph import Concept as GraphConcept, ConceptGraph
from backend.services.learner.mastery import _PARAMS
from backend.services.learner.tracer import KnowledgeTracer


@dataclass
class RehydratedLearner:
    graph: ConceptGraph
    tracer: KnowledgeTracer
    concept_by_id: dict[str, Concept]      # str(concept.id) -> ORM Concept
    state_by_id: dict[str, LearnerState]   # str(concept.id) -> LearnerState (only stored rows)


async def build_tracer(user_id: uuid.UUID, db: AsyncSession) -> RehydratedLearner | None:
    """Load the concept graph and rehydrate the user's tracer.

    Returns ``None`` if the domain has no concepts. Only concepts with real evidence
    (``evidence_count > 0``) seed the tracer; everything else keeps its dynamic
    prerequisite-gated prior so it still responds to new evidence.
    """
    concepts = (await db.execute(select(Concept))).scalars().all()
    if not concepts:
        return None
    concept_by_id = {str(c.id): c for c in concepts}

    prereq_rows = (
        await db.execute(
            select(ConceptRelationship.source_id, ConceptRelationship.target_id).where(
                ConceptRelationship.relation_type == "prerequisite"
            )
        )
    ).all()
    # An edge source -> target means source is a prerequisite of target.
    prereqs_of: dict[str, list[str]] = {cid: [] for cid in concept_by_id}
    for source_id, target_id in prereq_rows:
        s, t = str(source_id), str(target_id)
        if s in concept_by_id and t in concept_by_id:
            prereqs_of[t].append(s)

    graph = ConceptGraph(
        GraphConcept(
            id=str(c.id),
            name=c.name,
            prerequisites=tuple(prereqs_of[str(c.id)]),
            difficulty=c.difficulty,
        )
        for c in concepts
    )

    states = (
        await db.execute(select(LearnerState).where(LearnerState.user_id == user_id))
    ).scalars().all()
    state_by_id = {str(s.concept_id): s for s in states}
    mastery = {sid: s.mastery for sid, s in state_by_id.items() if (s.evidence_count or 0) > 0}
    counts = {sid: s.evidence_count for sid, s in state_by_id.items() if (s.evidence_count or 0) > 0}

    tracer = KnowledgeTracer.from_state(graph, mastery, counts=counts, params=_PARAMS)
    return RehydratedLearner(
        graph=graph,
        tracer=tracer,
        concept_by_id=concept_by_id,
        state_by_id=state_by_id,
    )
