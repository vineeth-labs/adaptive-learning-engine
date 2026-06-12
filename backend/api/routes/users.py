from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from backend.db.models import User, Concept, ConceptRelationship, LearnerState
from backend.schemas import UserMapResponse, ConceptNode, ConceptEdge
from backend.api.dependencies import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}/competency-map", response_model=UserMapResponse)
async def get_competency_map(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    concepts_result = await db.execute(select(Concept))
    concepts = concepts_result.scalars().all()
    concept_ids = {c.id for c in concepts}

    states_result = await db.execute(
        select(LearnerState).where(LearnerState.user_id == user_id)
    )
    state_by_concept = {s.concept_id: s for s in states_result.scalars().all()}

    edges_result = await db.execute(
        select(ConceptRelationship).where(
            ConceptRelationship.source_id.in_(concept_ids),
            ConceptRelationship.target_id.in_(concept_ids),
        )
    )
    edges = edges_result.scalars().all()

    nodes = []
    for concept in concepts:
        state = state_by_concept.get(concept.id)
        nodes.append(
            ConceptNode(
                id=concept.id,
                domain_id=concept.domain_id,
                name=concept.name,
                path=str(concept.path) if concept.path else "",
                difficulty=concept.difficulty,
                metadata=concept.concept_metadata or {},
                mastery=state.mastery if state else 0.0,
                evidence_count=state.evidence_count if state else 0,
                misconceptions=state.misconceptions if state else [],
                last_interaction_at=state.last_interaction_at if state else None,
            )
        )

    return UserMapResponse(
        user_id=user_id,
        nodes=nodes,
        edges=[ConceptEdge.model_validate(e) for e in edges],
    )
