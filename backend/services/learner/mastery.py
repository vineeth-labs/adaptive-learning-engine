"""Learner-state updates driven by Bayesian Knowledge Tracing.

``apply_diagnostic_result`` turns the diagnostic evaluator's per-question grades
into an updated mastery belief for a single concept, persisting it on the
``LearnerState`` row. The belief math lives in ``bkt.py`` (vendored from the
standalone knowledge-tracing engine); this module composes it with the
DB-backed learner state and the prerequisite graph.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.models import Concept, ConceptRelationship, LearnerState
from backend.schemas import DiagnosticResult

from . import bkt
from .bkt_models import BKTParams, Grade

# Global BKT parameters for the MVP, sourced from config. A production system
# would fit per-concept slip/guess from data (or vary them by difficulty).
_PARAMS = BKTParams(
    p_transit=settings.BKT_P_TRANSIT,
    p_slip=settings.BKT_P_SLIP,
    p_guess=settings.BKT_P_GUESS,
    base_prior=settings.BKT_BASE_PRIOR,
)


async def _prerequisite_gated_prior(
    user_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession,
) -> float:
    """Cold-start prior for a concept with no direct evidence.

    Mirrors ``KnowledgeTracer._recompute``: a root concept (no prerequisites)
    starts at ``base_prior``; otherwise the prior is ``base_prior * mean(prereq
    masteries)``, so advanced concepts start low until their prerequisites look
    solid. A prerequisite the learner has never been assessed on contributes its
    own ``base_prior``.
    """
    prereq_ids = (
        await db.execute(
            select(ConceptRelationship.source_id).where(
                ConceptRelationship.target_id == concept_id,
                ConceptRelationship.relation_type == "prerequisite",
            )
        )
    ).scalars().all()

    if not prereq_ids:
        return _PARAMS.base_prior

    prereq_masteries = dict(
        (
            await db.execute(
                select(LearnerState.concept_id, LearnerState.mastery).where(
                    LearnerState.user_id == user_id,
                    LearnerState.concept_id.in_(prereq_ids),
                )
            )
        ).all()
    )

    # Missing prereq state -> the learner hasn't been assessed on it yet, so it
    # contributes the base prior rather than 0.
    mean_prereq = sum(
        prereq_masteries.get(pid, _PARAMS.base_prior) for pid in prereq_ids
    ) / len(prereq_ids)
    return _PARAMS.base_prior * mean_prereq


async def apply_diagnostic_result(
    user_id: uuid.UUID,
    concept_id: uuid.UUID,
    result: DiagnosticResult,
    db: AsyncSession,
) -> float:
    """Apply the evaluator's per-question grades to the learner's mastery belief.

    Each grade is one BKT observation applied sequentially via
    ``bkt_update_graded``. The starting belief is the stored mastery when the
    learner already has evidence on this concept (continuing the trajectory), or
    the prerequisite-gated prior on a cold start. Returns the final belief.

    Does not commit — the caller commits once for the whole submission.
    """
    state = (
        await db.execute(
            select(LearnerState).where(
                LearnerState.user_id == user_id,
                LearnerState.concept_id == concept_id,
            )
        )
    ).scalar_one_or_none()

    if state is None:
        state = LearnerState(user_id=user_id, concept_id=concept_id, mastery=0.0, evidence_count=0)
        db.add(state)

    old_mastery = state.mastery or 0.0
    prior_count = state.evidence_count or 0

    # BKT belief (grade-based) is retained for a future version but no longer drives
    # the persisted mastery. Prior: continue the existing trajectory, or cold-start
    # from the prereq gate.
    if prior_count > 0:
        belief = old_mastery
    else:
        belief = await _prerequisite_gated_prior(user_id, concept_id, db)
    for qg in result.question_grades:
        belief = bkt.bkt_update_graded(belief, Grade[qg.grade], _PARAMS)

    # Simple running-average update from the evaluator's holistic answer_quality.
    # This submission counts as a single new piece of evidence.
    new_mastery = (old_mastery * prior_count + result.answer_quality) / (prior_count + 1)
    state.mastery = new_mastery
    state.evidence_count = prior_count + 1

    # Collect misconceptions from this submission (per-question + overall), dedup
    # against what's already recorded.
    new_misconceptions = [qg.misconception for qg in result.question_grades if qg.misconception]
    if result.misconception:
        new_misconceptions.append(result.misconception)
    if new_misconceptions:
        existing = list(state.misconceptions or [])
        for m in new_misconceptions:
            if m not in existing:
                existing.append(m)
        state.misconceptions = existing

    state.last_interaction_at = datetime.now(timezone.utc)
    return new_mastery
