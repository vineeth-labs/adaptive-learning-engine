"""Next-best-action recommendation.

Builds an in-memory ``ConceptGraph`` from the DB, rehydrates a ``KnowledgeTracer``
from the user's stored ``LearnerState`` (or leaves it cold-start empty), and uses
the tracer's leverage-based ``recommend_next_to_study`` to pick the highest-value
learnable concept. A light priority layer maps that concept's state to an
``action_type`` (TECH_SPEC §3.5); ``preview_path`` supplies a bounded roadmap.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.models import Recommendation, User
from backend.schemas import (
    ActionType,
    RecommendationDetail,
    RecommendationResponse,
)
from backend.services.learner.rehydrate import build_tracer


async def recommend_next(user_id: uuid.UUID, db: AsyncSession) -> RecommendationResponse:
    """Return the next-best-action recommendation for a user.

    Works for cold-start users (no LearnerState rows -> prerequisite-gated priors
    surface the foundations) and returning users (stored masteries rehydrated via
    ``KnowledgeTracer.from_state``) identically, since recommendation is a pure
    function of the belief vector.
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Rehydrate the learner's belief vector from stored state (shared with the frontier
    # endpoint, so both read the same beliefs). Only rows with real evidence seed the
    # tracer; everything else keeps its dynamic prereq-gated prior.
    rehydrated = await build_tracer(user_id, db)
    if rehydrated is None:
        raise HTTPException(status_code=404, detail="No concepts found")
    graph = rehydrated.graph
    tracer = rehydrated.tracer
    concept_by_id = rehydrated.concept_by_id
    state_by_id = rehydrated.state_by_id
    threshold = settings.RECOMMEND_MASTERY_THRESHOLD

    rec_id = tracer.recommend_next_to_study(mastery_threshold=threshold)
    if rec_id is None:
        # Everything reachable is already mastered (or nothing is learnable yet).
        return RecommendationResponse(
            action_type=ActionType.ASSESS,
            recommended_concepts=[],
            rationale="All reachable concepts are mastered — nothing to recommend right now.",
            payload={"roadmap": []},
        )

    rec_concept = concept_by_id[rec_id]
    rec_state = state_by_id.get(rec_id)
    rec_mastery = tracer.mastery(rec_id)

    # Leverage breakdown (the tracer's own scoring, surfaced for explainability).
    downstream_blocked = sum(
        1 for d in graph.descendants(rec_id) if tracer.mastery(d) < threshold
    )
    gap = 1.0 - rec_mastery
    centrality = float(1 + downstream_blocked)
    score = gap * centrality

    # Light priority routing -> action_type (presentation only; the pick is fixed).
    has_misconception = bool(rec_state and rec_state.misconceptions)
    encountered = bool(rec_state and (rec_state.evidence_count or 0) > 0)
    if has_misconception:
        action_type = ActionType.REVIEW
        reason = "you have a recorded misconception here — review it before moving on."
    elif not encountered:
        action_type = ActionType.ASSESS
        reason = "it's a new frontier concept ready to be assessed."
    else:
        action_type = ActionType.REVIEW
        reason = "you've encountered it but mastery is still low — reinforce it."

    rationale = (
        f"'{rec_concept.name}' is the highest-leverage concept you can learn now "
        f"(mastery {rec_mastery:.2f}, unblocks {downstream_blocked} downstream concept(s)): {reason}"
    )

    # Bounded study roadmap consistent with the leverage recommendation: the
    # order concepts would be recommended, starting with this one.
    roadmap_ids = tracer.recommend_path(
        max_steps=settings.ROADMAP_MAX_STEPS, mastery_threshold=threshold
    )
    roadmap = [
        {"concept_id": str(concept_by_id[cid].id), "concept_name": concept_by_id[cid].name}
        for cid in roadmap_ids
    ]

    detail = RecommendationDetail(
        concept_id=rec_concept.id,
        concept_name=rec_concept.name,
        score_calculated=score,
        score_breakdown={"gap": gap, "centrality": centrality, "score": score},
    )

    # Audit the engine decision (TECH_SPEC §5).
    db.add(
        Recommendation(
            user_id=user_id,
            concept_id=rec_concept.id,
            action_type=action_type.value,
            score_calculated=score,
        )
    )
    await db.commit()

    return RecommendationResponse(
        action_type=action_type,
        recommended_concepts=[detail],
        rationale=rationale,
        payload={"roadmap": roadmap},
    )
