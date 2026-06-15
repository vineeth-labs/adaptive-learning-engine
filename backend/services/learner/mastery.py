"""Learner-state updates driven by a Beta-Bernoulli mastery model.

``apply_diagnostic_result`` turns the diagnostic evaluator's per-question scores
into an updated mastery belief for a single concept, persisting it on the
``LearnerState`` row. The belief math lives in ``beta_mastery.py`` (a per-concept
Beta(alpha, beta) posterior); this module composes it with the DB-backed learner
state and the prerequisite graph. See ``docs/mastery-update.md``.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.models import Concept, ConceptRelationship, LearnerState
from backend.schemas import DiagnosticResult

from . import beta_mastery
from .beta_mastery import BetaState
from .bkt_models import BKTParams

# BKT parameters for the MVP. The mastery *update* is now Beta-Bernoulli (below), but
# the recommender's ``KnowledgeTracer`` still uses these for diagnostic selection, so
# they stay centralized here and are imported by ``services/recommender``.
_PARAMS = BKTParams(
    p_transit=settings.BKT_P_TRANSIT,
    p_slip=settings.BKT_P_SLIP,
    p_guess=settings.BKT_P_GUESS,
    base_prior=settings.BKT_BASE_PRIOR,
)

# Cold-start prior mean for a root concept, reused from the BKT prior so the two
# models agree on where an unseen concept starts before evidence arrives.
_BASE_PRIOR = settings.BKT_BASE_PRIOR
# Total concentration of the cold-start Beta prior (how much the prior resists the
# first few answers).
_PRIOR_CONCENTRATION = settings.BETA_PRIOR_ALPHA + settings.BETA_PRIOR_BETA


async def _prerequisite_gated_prior(
    user_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession,
) -> float:
    """Cold-start prior *mean* for a concept with no direct evidence.

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
        return _BASE_PRIOR

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
        prereq_masteries.get(pid, _BASE_PRIOR) for pid in prereq_ids
    ) / len(prereq_ids)
    return _BASE_PRIOR * mean_prereq


async def apply_diagnostic_result(
    user_id: uuid.UUID,
    concept_id: uuid.UUID,
    result: DiagnosticResult,
    db: AsyncSession,
) -> float:
    """Apply the evaluator's per-question scores to the learner's mastery belief.

    The belief is a Beta(alpha, beta) posterior. Each question's ``answer_score``
    is one fractional observation folded in via ``beta_mastery.apply_score``. Before
    applying new evidence the belief is decayed toward the prior by the time elapsed
    since the last interaction (forgetting). The starting state is the stored
    ``(alpha, beta)`` when the learner already has evidence, or a prior whose mean is
    the prerequisite-gated cold start. Returns the new posterior mean (= mastery).

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

    prior_count = state.evidence_count or 0
    now = datetime.now(timezone.utc)

    # Cold-start prior: prerequisite-gated mean at the configured concentration, so
    # advanced concepts start low until their prerequisites look solid. This prior is
    # also the target the belief decays back toward (forgetting).
    prior_mean = await _prerequisite_gated_prior(user_id, concept_id, db)
    prior = beta_mastery.prior_from_mean(prior_mean, _PRIOR_CONCENTRATION)

    # Starting belief: continue the stored trajectory, or cold-start from the prior.
    if state.alpha is not None and state.beta is not None:
        belief = BetaState(alpha=state.alpha, beta=state.beta)
    else:
        belief = prior

    # Forgetting: decay toward the prior by the days since the last interaction.
    if state.last_interaction_at is not None:
        last = state.last_interaction_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed_days = max(0.0, (now - last).total_seconds() / 86_400.0)
        belief = beta_mastery.decay_toward_prior(
            belief, prior, elapsed_days, settings.BETA_HALF_LIFE_DAYS
        )

    # One fractional observation per question.
    for qg in result.question_grades:
        belief = beta_mastery.apply_score(belief, qg.answer_score, settings.BETA_BASE_WEIGHT)

    state.alpha = belief.alpha
    state.beta = belief.beta
    new_mastery = belief.mastery()
    state.mastery = new_mastery
    # Each question is one observation, so evidence accrues per question answered.
    state.evidence_count = prior_count + len(result.question_grades)

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

    state.last_interaction_at = now
    return new_mastery
