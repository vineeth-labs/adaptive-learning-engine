from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any
from uuid import UUID

class ConceptNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    path: str  # String representation of Postgres ltree (e.g., "Java.Concurrency")
    difficulty_weight: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Overlayed learner state (default values if no state exists yet)
    mastery: float = 0.0
    confidence: float = 0.0
    fsrs_stability: float = 0.0
    evidence_count: int = 0
    misconceptions: List[str] = Field(default_factory=list)

class ConceptEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: UUID
    target_id: UUID
    relation_type: str  # e.g., "prerequisite_of", "part_of"

class UserMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nodes: List[ConceptNode]
    edges: List[ConceptEdge]
