from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
from uuid import UUID
from datetime import datetime

class ConceptNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain_id: UUID
    name: str
    path: str  # String representation of Postgres ltree (e.g., "Java.Concurrency")
    difficulty: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Overlayed learner state (default values if no state exists yet)
    mastery: float = 0.0
    evidence_count: int = 0
    misconceptions: List[str] = Field(default_factory=list)
    last_interaction_at: Optional[datetime] = None

class ConceptEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: UUID
    target_id: UUID
    relation_type: Literal["prerequisite"]

class UserMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nodes: List[ConceptNode]
    edges: List[ConceptEdge]
