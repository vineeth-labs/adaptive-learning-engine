from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.schemas import RecommendationResponse
from backend.services.recommender import recommend_next

router = APIRouter(prefix="/users", tags=["recommendations"])


@router.get("/{user_id}/recommendations/next", response_model=RecommendationResponse)
async def get_next_recommendation(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Return the next-best-action recommendation (highest-leverage learnable
    concept) for the user, with an explainable rationale and a bounded roadmap."""
    return await recommend_next(user_id, db)
