from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID

class ActionType(str, Enum):
    ASSESS = "ASSESS"
    REVIEW = "REVIEW"
    TEACH = "TEACH"

class RecommendationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: UUID
    concept_name: str
    score: float
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict, 
        description="Weight breakdown: gap, review, centrality, fatigue"
    )

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_type: ActionType
    recommended_concepts: List[RecommendationDetail]
    rationale: str
    payload: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Context-specific details, e.g. scenario text or tutorial content"
    )
