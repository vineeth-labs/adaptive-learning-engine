from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from uuid import UUID
from typing import Dict, Any, List, Literal

class DomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str

class ConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain_id: UUID
    name: str
    path: str
    difficulty: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("concept_metadata", "metadata"))

class GraphNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    path: str
    difficulty: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("concept_metadata", "metadata"))

class GraphEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: UUID
    target_id: UUID
    relation_type: Literal["prerequisite"]

class DomainGraphResponse(BaseModel):
    domain_id: UUID
    domain_name: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
